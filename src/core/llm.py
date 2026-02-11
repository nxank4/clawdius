from anthropic import AsyncAnthropic
from loguru import logger

from src.core.config import settings
from src.tools.registry import TOOLS, run_tool

MAX_TOOL_ROUNDS = 15


class Brain:
    def __init__(self) -> None:
        self.client = AsyncAnthropic(
            base_url=settings.LLM_BASE_URL,
            api_key=settings.LLM_API_KEY,
        )
        self.model = settings.LLM_MODEL
        logger.info(f"Brain initialized → model={self.model} base_url={settings.LLM_BASE_URL}")

    async def think(self, prompt: str, on_tool_call=None) -> str:
        """ReAct loop: reason, act with tools, repeat until final answer.

        on_tool_call: optional async callback(tool_name, tool_args) for status updates.
        """
        messages = [{"role": "user", "content": prompt}]

        for round_num in range(MAX_TOOL_ROUNDS):
            logger.debug(f"Round {round_num + 1}")
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                tools=TOOLS,
                messages=messages,
            )

            logger.debug(f"stop_reason={response.stop_reason} blocks={[b.type for b in response.content]}")

            # Collect any tool_use blocks
            tool_blocks = [b for b in response.content if b.type == "tool_use"]

            if not tool_blocks:
                # No tools requested — extract final text answer
                text_parts = [b.text for b in response.content if b.type == "text"]
                return "\n".join(text_parts) or "(no response)"

            # Append the assistant's full response (text + tool_use blocks)
            messages.append({"role": "assistant", "content": response.content})

            # Execute each tool and collect results
            tool_results = []
            for block in tool_blocks:
                logger.info(f"Tool call: {block.name}({block.input})")
                if on_tool_call:
                    await on_tool_call(block.name, block.input)

                result = await run_tool(block.name, block.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result,
                })

            messages.append({"role": "user", "content": tool_results})

        return "(max tool rounds reached)"

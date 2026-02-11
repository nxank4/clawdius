from anthropic import AsyncAnthropic
from loguru import logger

from src.core.config import settings


class Brain:
    def __init__(self) -> None:
        self.client = AsyncAnthropic(
            base_url=settings.LLM_BASE_URL,
            api_key=settings.LLM_API_KEY,
        )
        self.model = settings.LLM_MODEL
        logger.info(f"Brain initialized → model={self.model} base_url={settings.LLM_BASE_URL}")

    async def think(self, prompt: str) -> str:
        logger.debug(f"Thinking: {prompt[:80]}...")
        response = await self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
        content = response.content[0].text if response.content else ""
        logger.debug(f"Response: {content[:80]}...")
        return content

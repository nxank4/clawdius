import discord
from loguru import logger

from src.core.config import settings
from src.core.llm import Brain

PREFIX = "!c"
DISCORD_MAX_LEN = 2000


class ClawdiusBot(discord.Client):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        kwargs = {}
        if settings.DISCORD_PROXY:
            kwargs["proxy"] = settings.DISCORD_PROXY
        super().__init__(intents=intents, **kwargs)
        self.brain = Brain()

    async def on_ready(self) -> None:
        logger.info(f"Clawdius is listening as {self.user}")

    async def on_message(self, message: discord.Message) -> None:
        if message.author == self.user:
            return

        if settings.ALLOWED_CHANNEL_ID and message.channel.id != settings.ALLOWED_CHANNEL_ID:
            return

        if settings.ALLOWED_USER_ID and message.author.id != settings.ALLOWED_USER_ID:
            return

        if not message.content.startswith(PREFIX):
            return

        prompt = message.content[len(PREFIX):].strip()
        if not prompt:
            await message.reply("Usage: `!c <your prompt>`")
            return

        logger.info(f"Request from {message.author}: {prompt[:80]}")

        tool_log = []

        async def on_tool_call(name: str, args: dict) -> None:
            tool_log.append(name)

        async with message.channel.typing():
            try:
                response = await self.brain.think(prompt, on_tool_call=on_tool_call)
            except Exception as e:
                logger.error(f"Brain error: {e}")
                await message.reply(f"Something went wrong: `{e}`")
                return

        if tool_log:
            tools_used = ", ".join(f"`{t}`" for t in tool_log)
            response = f"{response}\n\n_Tools used: {tools_used}_"

        for i in range(0, len(response), DISCORD_MAX_LEN):
            await message.reply(response[i : i + DISCORD_MAX_LEN])

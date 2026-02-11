import logging

from loguru import logger

from src.core.config import settings
from src.interfaces.discord_bot import ClawdiusBot


def main() -> None:
    if not settings.DISCORD_TOKEN:
        logger.error("DISCORD_TOKEN is not set. Check your .env file.")
        raise SystemExit(1)

    logging.basicConfig(level=logging.DEBUG)

    bot = ClawdiusBot()
    logger.info("Starting Clawdius...")
    bot.run(settings.DISCORD_TOKEN)


if __name__ == "__main__":
    main()

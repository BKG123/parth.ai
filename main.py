"""Parth.ai - Main entry point."""

import os

from dotenv import load_dotenv

load_dotenv()


def main():
    """Launch the Telegram bot. Set TELEGRAM_BOT_TOKEN in .env."""
    if not os.getenv("TELEGRAM_BOT_TOKEN"):
        raise ValueError("TELEGRAM_BOT_TOKEN must be set in .env")
    from app_telegram import main as telegram_main
    telegram_main()


if __name__ == "__main__":
    main()

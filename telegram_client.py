"""Telegram API client for sending messages (used by worker, proactive agent)."""

import html
import logging
import os
import re

import httpx

logger = logging.getLogger(__name__)


def md_to_html(text: str) -> str:
    """Convert AI markdown to Telegram HTML. Shared by app_telegram and send_telegram_message."""
    if not text:
        return ""
    escaped = html.escape(text)
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", escaped)
    escaped = re.sub(r"\*([^*]+)\*", r"<i>\1</i>", escaped)
    escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
    return escaped


async def send_telegram_message(
    chat_id: int,
    text: str,
    parse_mode: str = "HTML",
) -> dict | None:
    """Send a message via Telegram Bot API.

    Args:
        chat_id: Telegram chat ID (user's telegram_id)
        text: Message content (will be HTML-formatted if parse_mode=HTML)
        parse_mode: 'HTML' or None for plain text

    Returns:
        API response dict or None on failure
    """
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN not set - cannot send message")
        return None

    formatted = md_to_html(text) if parse_mode == "HTML" else text
    if len(formatted) > 4096:
        formatted = formatted[:4090] + "..."

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": formatted,
        "parse_mode": parse_mode,
    }

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload, timeout=10.0)
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPError as e:
        logger.error(f"Telegram send failed: {e}")
        return None

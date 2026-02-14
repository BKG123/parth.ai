"""Telegram bot interface for Parth AI Assistant."""

import html
import logging
import os
import time

from telegram_client import md_to_html
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from dotenv import load_dotenv

from ai.agent_manager import AgentManager
from services.services import MessageService, UserCRUD
from models.models import User

load_dotenv()

logger = logging.getLogger(__name__)

# Database
_POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
_POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
_POSTGRES_USER = os.getenv("POSTGRES_USER", "admin")
_POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "admin123")
_POSTGRES_DB = os.getenv("POSTGRES_DB", "parth_db")
DATABASE_URL = f"postgresql+asyncpg://{_POSTGRES_USER}:{_POSTGRES_PASSWORD}@{_POSTGRES_HOST}:{_POSTGRES_PORT}/{_POSTGRES_DB}"


def _make_session():
    engine = create_async_engine(
        DATABASE_URL,
        echo=False,
        pool_pre_ping=False,
        poolclass=NullPool,
    )
    return async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )


async def get_user_and_history(telegram_id: int) -> tuple[User, list[dict]]:
    """Get or create user and fetch recent message history."""
    SessionLocal = _make_session()
    async with SessionLocal() as db:
        user_crud = UserCRUD(model=User)
        user = await user_crud.get_or_create_by_telegram_id(db, telegram_id=telegram_id)
        msg_service = MessageService(db)
        messages = await msg_service.get_recent_messages(user.id, limit=20)
        history = [
            {"role": msg.role.name, "content": msg.content}
            for msg in reversed(messages)
        ]
        return user, history


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    await update.message.reply_text(
        "🪶 **Parth AI Assistant**\n\n"
        "Your personal AI guide for goals and growth. "
        "Ask me anything about creating goals, tracking progress, or getting guidance.\n\n"
        "Try: *Create a goal to run 5K* or *What are my active goals?*",
        parse_mode="Markdown",
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming text messages."""
    if not update.message or not update.message.text:
        return

    telegram_id = update.effective_user.id
    prompt = update.message.text.strip()

    await update.effective_chat.send_action("typing")

    try:
        user, history = await get_user_and_history(telegram_id)
    except Exception as e:
        logger.exception("DB error getting user/history: %s", e)
        await update.message.reply_text(
            "Sorry, I couldn't load your data. Please try again."
        )
        return

    # Save user message
    SessionLocal = _make_session()
    async with SessionLocal() as db:
        msg_service = MessageService(db)
        await msg_service.create_message(
            user_id=user.id,
            role="user",
            content=prompt,
            telegram_message_id=update.message.message_id,
        )

    # Create agent and stream response
    agent = AgentManager(
        user_id=str(user.id),
        name="Parth AI",
        model=os.getenv("OPENAI_MODEL", "gpt-5.2"),
    )

    sent_msg = await update.message.reply_text("🪶 Thinking...")
    full_response = ""
    tool_calls = []
    active_tools = []
    last_edit = -999  # Force first edit immediately
    EDIT_INTERVAL = 1.5  # seconds, to respect Telegram rate limits

    try:
        async for event in agent.stream_response(prompt, history=history):
            if event["type"] == "text":
                full_response += event["content"]
            elif event["type"] == "tool_call":
                tool_calls.append(event["content"])
                active_tools.append(event["content"])
            elif event["type"] == "tool_output":
                if active_tools:
                    active_tools.pop(0)

            # Throttled edit for streaming UX
            now = time.monotonic()
            if now - last_edit >= EDIT_INTERVAL or event["type"] == "tool_call":
                display = _build_display(full_response, tool_calls, active_tools)
                try:
                    await sent_msg.edit_text(
                        display or "🪶 Thinking...",
                        parse_mode="HTML",
                    )
                    last_edit = now
                except Exception:
                    pass  # Same content or rate limit

        # Final message
        display = _build_display(full_response, tool_calls, [])
        await sent_msg.edit_text(
            display or "No response generated.",
            parse_mode="HTML",
        )

        # Save assistant message
        SessionLocal2 = _make_session()
        async with SessionLocal2() as db:
            msg_service = MessageService(db)
            await msg_service.create_message(
                user_id=user.id,
                role="assistant",
                content=full_response,
                telegram_message_id=sent_msg.message_id,
            )

    except Exception as e:
        logger.exception("Agent error: %s", e)
        await sent_msg.edit_text(
            f"Error: {html.escape(str(e))}",
            parse_mode="HTML",
        )


def _build_display(response: str, tool_calls: list, active_tools: list) -> str:
    """Build display text for Telegram (HTML formatted, max 4096 chars)."""
    parts = []
    if tool_calls:
        parts.append("🔧 Tools: " + ", ".join(tool_calls) + "\n")
    if active_tools:
        parts.append("⚙️ Running: " + ", ".join(active_tools) + "\n")
    parts.append(md_to_html(response or ""))
    text = "\n".join(parts)
    return text[:4090] + "..." if len(text) > 4096 else text


def main() -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN must be set in environment")

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
    )

    logger.info("Starting Parth AI Telegram bot...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

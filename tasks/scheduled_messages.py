"""Task to execute scheduled messages when their time comes."""

import logging
from datetime import datetime

from sqlalchemy import select

from database import AsyncSessionLocal
from models.models import User
from services.services import ScheduledMessageService
from ai.reactive_agent import ReactiveAgent

logger = logging.getLogger(__name__)


async def execute_scheduled_messages(ctx):
    """
    Execute scheduled messages that are due.

    This runs more frequently (every 5-15 minutes) to send messages
    that were scheduled by the ProactiveAgent.

    Args:
        ctx: Worker context
    """
    logger.info("🕐 Checking for scheduled messages to send")

    async with AsyncSessionLocal() as db:
        try:
            # Get scheduled messages that are due
            scheduled_service = ScheduledMessageService(db)
            due_messages = await scheduled_service.get_pending_messages(
                before_time=datetime.utcnow()
            )

            if not due_messages:
                logger.info("No scheduled messages due")
                return {
                    "status": "completed",
                    "messages_sent": 0,
                }

            logger.info(f"Found {len(due_messages)} scheduled messages to send")

            sent_count = 0
            failed_count = 0

            for scheduled_msg in due_messages:
                try:
                    # Get user for telegram_id
                    result = await db.execute(
                        select(User).where(User.id == scheduled_msg.user_id)
                    )
                    user = result.scalar_one_or_none()

                    if not user:
                        logger.warning(
                            f"User {scheduled_msg.user_id} not found for scheduled message {scheduled_msg.id}"
                        )
                        await scheduled_service.mark_as_cancelled(scheduled_msg.id)
                        failed_count += 1
                        continue

                    # Use ReactiveAgent with db user_id (messages FK uses users.id)
                    reactive_agent = ReactiveAgent(user_id=str(user.id))
                    result = await reactive_agent.send_proactive_message(
                        content=scheduled_msg.message_content,
                        goal_id=scheduled_msg.goal_id,
                        telegram_chat_id=user.telegram_id,
                    )

                    if result["status"] == "sent":
                        await scheduled_service.mark_as_sent(scheduled_msg.id)
                        sent_count += 1
                        logger.info(
                            f"Sent scheduled message {scheduled_msg.id} to user {scheduled_msg.user_id}"
                        )
                    else:
                        logger.error(
                            f"Failed to send scheduled message {scheduled_msg.id}: {result.get('error')}"
                        )
                        failed_count += 1

                except Exception as e:
                    logger.error(
                        f"Error sending scheduled message {scheduled_msg.id}: {e}",
                        exc_info=True,
                    )
                    failed_count += 1

            logger.info(
                f"✅ Scheduled messages execution completed: "
                f"{sent_count} sent, {failed_count} failed"
            )

            return {
                "status": "completed",
                "messages_sent": sent_count,
                "messages_failed": failed_count,
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error executing scheduled messages: {e}", exc_info=True)
            return {
                "status": "failed",
                "error": str(e),
            }

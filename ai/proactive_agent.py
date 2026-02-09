"""Proactive Agent - Evaluates whether to reach out proactively."""

import json
import logging
from datetime import datetime
from typing import Dict, Any

from openai import AsyncOpenAI
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from database import AsyncSessionLocal
from models.models import User, Goal, GoalStatus, Message
from prompts.proactive_agent_prompt import PROACTIVE_EVALUATION_PROMPT
from ai.reactive_agent import ReactiveAgent

logger = logging.getLogger(__name__)


class ProactiveAgent:
    """Evaluates whether Parth should proactively reach out to the user."""

    def __init__(self, model: str = "gpt-5.2"):
        self.model = model
        self.client = AsyncOpenAI()

    async def build_context(self, user_id: int) -> Dict[str, Any]:
        """Build analytical context for decision-making.

        Args:
            user_id: User's database ID

        Returns:
            Dict with user context including goals, messages, preferences
        """
        async with AsyncSessionLocal() as db:
            # Get user with relationships
            result = await db.execute(
                select(User)
                .options(
                    selectinload(User.goals).selectinload(Goal.goal_data),
                    selectinload(User.preferences),
                    selectinload(User.messages),
                    selectinload(User.scheduled_messages),
                )
                .where(User.id == user_id)
            )
            user = result.scalar_one_or_none()

            if not user:
                return {"error": "user_not_found"}

            # Get active goals with their data
            active_goals = []
            for goal in user.goals:
                if goal.status == GoalStatus.active:
                    goal_info = {
                        "id": goal.id,
                        "title": goal.title,
                        "created_at": goal.created_at.isoformat(),
                        "updated_at": goal.updated_at.isoformat(),
                    }
                    if goal.goal_data:
                        goal_info["data"] = goal.goal_data.agent_data
                    active_goals.append(goal_info)

            # Get recent messages (last 20)
            result = await db.execute(
                select(Message)
                .where(Message.user_id == user_id)
                .order_by(Message.created_at.desc())
                .limit(20)
            )
            messages = result.scalars().all()
            recent_messages = [
                {
                    "role": msg.role.value,
                    "content": msg.content,
                    "created_at": msg.created_at.isoformat(),
                    "goal_id": msg.goal_id,
                }
                for msg in reversed(messages)  # Reverse to chronological order
            ]

            # Calculate time since last contact
            last_message_time = None
            last_assistant_message = None
            if messages:
                last_message_time = messages[0].created_at
                # Find last assistant message
                for msg in messages:
                    if msg.role.value == "assistant":
                        last_assistant_message = msg.created_at
                        break

            # User preferences
            preferences = {}
            if user.preferences and user.preferences.agent_data:
                preferences = user.preferences.agent_data

            # Pending scheduled messages
            pending_scheduled = []
            for scheduled_msg in user.scheduled_messages:
                if scheduled_msg.status.value == "pending":
                    pending_scheduled.append(
                        {
                            "goal_id": scheduled_msg.goal_id,
                            "scheduled_for": scheduled_msg.scheduled_for.isoformat(),
                            "message_content": scheduled_msg.message_content,
                        }
                    )

            context = {
                "user_id": user_id,
                "telegram_id": user.telegram_id,
                "timezone": user.timezone,
                "is_active": user.is_active,
                "current_datetime": datetime.utcnow().isoformat(),
                "active_goals": active_goals,
                "active_goals_count": len(active_goals),
                "recent_messages": recent_messages,
                "last_message_at": last_message_time.isoformat()
                if last_message_time
                else None,
                "last_assistant_message_at": (
                    last_assistant_message.isoformat()
                    if last_assistant_message
                    else None
                ),
                "hours_since_last_message": (
                    (datetime.utcnow() - last_message_time).total_seconds() / 3600
                    if last_message_time
                    else None
                ),
                "hours_since_last_assistant_message": (
                    (datetime.utcnow() - last_assistant_message).total_seconds() / 3600
                    if last_assistant_message
                    else None
                ),
                "user_preferences": preferences,
                "pending_scheduled_messages": pending_scheduled,
            }

            return context

    async def evaluate(self, user_id: int) -> Dict[str, Any]:
        """Evaluate whether to reach out proactively.

        Args:
            user_id: User's database ID

        Returns:
            Decision dict with action, message, goal_id, send_at, reasoning
        """
        logger.info(f"Evaluating proactive outreach for user {user_id}")

        try:
            # Build context
            context = await self.build_context(user_id)

            if "error" in context:
                return {
                    "action": "skip",
                    "message": None,
                    "goal_id": None,
                    "send_at": None,
                    "reasoning": f"Error building context: {context['error']}",
                }

            # If no active goals, skip
            if context["active_goals_count"] == 0:
                return {
                    "action": "skip",
                    "message": None,
                    "goal_id": None,
                    "send_at": None,
                    "reasoning": "User has no active goals",
                }

            # Build prompt with context
            prompt = f"{PROACTIVE_EVALUATION_PROMPT}\n\n## CONTEXT\n\n```json\n{json.dumps(context, indent=2)}\n```\n\nProvide your decision as valid JSON:"

            # Call LLM for decision
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                response_format={"type": "json_object"},
            )

            decision_text = response.choices[0].message.content
            decision = json.loads(decision_text)

            # Validate decision structure
            required_keys = ["action", "message", "goal_id", "send_at", "reasoning"]
            if not all(key in decision for key in required_keys):
                logger.error(f"Invalid decision structure: {decision}")
                return {
                    "action": "skip",
                    "message": None,
                    "goal_id": None,
                    "send_at": None,
                    "reasoning": "Invalid decision structure from LLM",
                }

            logger.info(
                f"Decision for user {user_id}: {decision['action']} - {decision['reasoning']}"
            )

            return decision

        except Exception as e:
            logger.error(
                f"Error evaluating proactive outreach for user {user_id}: {e}",
                exc_info=True,
            )
            return {
                "action": "skip",
                "message": None,
                "goal_id": None,
                "send_at": None,
                "reasoning": f"Error during evaluation: {str(e)}",
            }

    async def execute_decision(
        self, user_id: int, decision: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute the decided action.

        Args:
            user_id: User's database ID
            decision: Decision dict from evaluate()

        Returns:
            Result dict with status and details
        """
        action = decision["action"]

        try:
            if action == "send_now":
                # Get user's telegram_id for sending message
                async with AsyncSessionLocal() as db:
                    result = await db.execute(select(User).where(User.id == user_id))
                    user = result.scalar_one_or_none()

                    if not user:
                        return {"status": "failed", "reason": "user_not_found"}

                    # Use ReactiveAgent to send the message
                    reactive_agent = ReactiveAgent(user_id=str(user.telegram_id))
                    result = await reactive_agent.send_proactive_message(
                        content=decision["message"],
                        goal_id=decision.get("goal_id"),
                        telegram_chat_id=user.telegram_id,
                    )

                    return {
                        "status": "completed",
                        "action": "sent",
                        "message_id": result.get("message_id"),
                        "timestamp": datetime.utcnow().isoformat(),
                    }

            elif action == "schedule":
                # Store in scheduled_messages table
                from services.services import ScheduledMessageService

                async with AsyncSessionLocal() as db:
                    scheduled_service = ScheduledMessageService(db)
                    scheduled_msg = await scheduled_service.create_scheduled_message(
                        user_id=user_id,
                        goal_id=decision.get("goal_id"),
                        scheduled_for=datetime.fromisoformat(decision["send_at"]),
                        message_content=decision["message"],
                    )

                    return {
                        "status": "completed",
                        "action": "scheduled",
                        "scheduled_message_id": scheduled_msg.id,
                        "scheduled_for": decision["send_at"],
                    }

            elif action == "skip":
                return {
                    "status": "completed",
                    "action": "skipped",
                    "reasoning": decision["reasoning"],
                }

            else:
                return {"status": "failed", "reason": f"unknown_action: {action}"}

        except Exception as e:
            logger.error(
                f"Error executing decision for user {user_id}: {e}", exc_info=True
            )
            return {"status": "failed", "error": str(e)}

    async def run(self, user_id: int) -> Dict[str, Any]:
        """Run the full proactive evaluation and execution.

        Args:
            user_id: User's database ID

        Returns:
            Result dict with decision and execution details
        """
        # Evaluate
        decision = await self.evaluate(user_id)

        # Execute
        result = await self.execute_decision(user_id, decision)

        # Combine decision and result
        return {
            "user_id": user_id,
            "decision": decision,
            "execution": result,
            "timestamp": datetime.utcnow().isoformat(),
        }

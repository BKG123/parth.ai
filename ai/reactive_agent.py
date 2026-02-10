"""Reactive Agent - Handles user messages in real-time."""

import logging
from typing import AsyncIterator
from agents import Agent, Runner, RunItemStreamEvent
from openai.types.responses import ResponseTextDeltaEvent

from ai.llm_tools import (
    AgentContext,
    list_goals,
    get_goal,
    get_goal_data,
    update_goal_data,
    append_goal_event,
    send_message,
    get_recent_messages,
    update_user_preferences,
    create_goal,
    update_goal_status,
    create_skill,
    update_skill,
    link_goal_to_skill,
    get_goal_skill,
    search_skills,
    get_skill,
    read_reference_doc,
    search_web,
)
from prompts.agents import PARTH_AGENT_PROMPT
from database import AsyncSessionLocal
from services.services import MessageService

logger = logging.getLogger(__name__)

TOOLS_ALLOWED_LIST = [
    update_user_preferences,
    list_goals,
    get_goal,
    get_goal_data,
    update_goal_data,
    append_goal_event,
    send_message,
    get_recent_messages,
    create_goal,
    update_goal_status,
    create_skill,
    update_skill,
    link_goal_to_skill,
    get_goal_skill,
    search_skills,
    get_skill,
    read_reference_doc,
    search_web,
]


class ReactiveAgent:
    """Handles user messages in real-time with full conversational capability."""

    def __init__(
        self,
        user_id: str,
        name: str = "Parth AI",
        instructions: str = None,
        model: str = "gpt-5.2",
    ) -> None:
        self.user_id = user_id
        self.agent = Agent(
            name=name,
            instructions=instructions or PARTH_AGENT_PROMPT,
            model=model,
            tools=TOOLS_ALLOWED_LIST,
        )

    async def stream_response(
        self, prompt: str, history: list[dict] = None
    ) -> AsyncIterator[dict]:
        """Stream agent response with events including tool calls.

        Args:
            prompt: User input prompt
            history: List of previous messages [{"role": "user", "content": "..."}, ...]

        Yields:
            Dict with 'type' and 'content' keys for text deltas and tool calls
        """
        # Build messages list with history
        messages = []
        if history:
            for msg in history:
                messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": prompt})

        # Create context with user_id
        context = AgentContext(user_id=self.user_id)
        result = Runner.run_streamed(self.agent, messages, context=context)
        async for event in result.stream_events():
            # Handle text deltas
            if event.type == "raw_response_event" and isinstance(
                event.data, ResponseTextDeltaEvent
            ):
                yield {"type": "text", "content": event.data.delta}

            # Handle tool calls
            elif isinstance(event, RunItemStreamEvent) and event.name == "tool_called":
                tool_name = (
                    event.item.raw_item.name
                    if hasattr(event.item, "raw_item")
                    else "Unknown"
                )
                yield {"type": "tool_call", "content": tool_name}

            # Handle tool outputs
            elif isinstance(event, RunItemStreamEvent) and event.name == "tool_output":
                yield {"type": "tool_output", "content": "completed"}

    async def get_response(self, prompt: str, history: list[dict] = None) -> str:
        """Get complete agent response (non-streaming).

        Args:
            prompt: User input prompt
            history: List of previous messages [{"role": "user", "content": "..."}, ...]

        Returns:
            Complete response text
        """
        # Build messages list with history
        messages = []
        if history:
            for msg in history:
                messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": prompt})

        # Create context with user_id
        context = AgentContext(user_id=self.user_id)
        result = await Runner.run(self.agent, messages, context=context)
        return result.final_output

    async def send_proactive_message(
        self,
        content: str,
        goal_id: int | None = None,
        telegram_chat_id: int | None = None,
    ) -> dict:
        """Send a proactive message to the user.

        This is called by ProactiveAgent when it decides to send a message.
        Routes through ReactiveAgent for consistency.

        Args:
            content: Message content
            goal_id: Optional goal ID to associate message with
            telegram_chat_id: Telegram chat ID to send to

        Returns:
            Dict with status and message_id
        """
        logger.info(f"Sending proactive message to user {self.user_id}")

        async with AsyncSessionLocal() as db:
            try:
                # Store message in database
                message_service = MessageService(db)
                message = await message_service.create_message(
                    user_id=int(self.user_id),
                    goal_id=goal_id,
                    role="assistant",
                    content=content,
                )

                # Send via Telegram if chat_id provided
                if telegram_chat_id:
                    # TODO: Import and use telegram bot to send message
                    # await telegram_bot.send_message(chat_id=telegram_chat_id, text=content)
                    logger.info(
                        f"Would send Telegram message to {telegram_chat_id}: {content[:50]}..."
                    )
                    pass

                return {
                    "status": "sent",
                    "message_id": message.id,
                    "timestamp": message.created_at.isoformat(),
                }

            except Exception as e:
                logger.error(f"Error sending proactive message: {e}", exc_info=True)
                return {"status": "failed", "error": str(e)}

    @property
    def model_name(self) -> str:
        """Get the model name."""
        return self.agent.model

    @property
    def agent_name(self) -> str:
        """Get the agent name."""
        return self.agent.name

from dataclasses import dataclass
from datetime import datetime
from agents import function_tool, RunContextWrapper
from database import AsyncSessionLocal
from services import (
    user_crud,
    user_preference_crud,
    goal_crud,
    goal_data_crud,
    message_crud,
    scheduled_message_crud,
)
from models.models import MessageRole, MessageStatus


@dataclass
class AgentContext:
    """Context passed to all agent tools containing user-specific data."""

    user_id: str


@function_tool
# User context (read/write)
async def update_user_preferences(
    wrapper: RunContextWrapper[AgentContext], data: dict
) -> None:
    """Update user preferences with the provided data."""
    user_id = int(wrapper.context.user_id)
    
    async with AsyncSessionLocal() as db:
        # Get user to verify they exist
        user = await user_crud.get(db, user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        # Get or create user preferences
        prefs = await user_preference_crud.get_by(db, user_id=user_id)
        if prefs:
            # Update existing preferences
            current_data = prefs.agent_data or {}
            current_data.update(data)
            await user_preference_crud.update(db, prefs.id, agent_data=current_data)
        else:
            # Create new preferences
            await user_preference_crud.create(db, user_id=user_id, agent_data=data)


@function_tool
# Goals metadata (read-only)
async def list_goals(wrapper: RunContextWrapper[AgentContext]) -> list[dict]:
    """List all goals for the current user."""
    user_id = int(wrapper.context.user_id)
    
    async with AsyncSessionLocal() as db:
        goals = await goal_crud.get_all(db, user_id=user_id)
        return [
            {
                "id": goal.id,
                "title": goal.title,
                "status": goal.status.value,
                "created_at": goal.created_at.isoformat(),
                "updated_at": goal.updated_at.isoformat(),
            }
            for goal in goals
        ]


@function_tool
async def get_goal(wrapper: RunContextWrapper[AgentContext], goal_id: int) -> dict:
    """Get a specific goal by ID."""
    user_id = int(wrapper.context.user_id)
    
    async with AsyncSessionLocal() as db:
        goal = await goal_crud.get(db, goal_id)
        if not goal:
            raise ValueError(f"Goal {goal_id} not found")
        
        # Verify goal belongs to user
        if goal.user_id != user_id:
            raise ValueError(f"Goal {goal_id} does not belong to user {user_id}")
        
        return {
            "id": goal.id,
            "title": goal.title,
            "status": goal.status.value,
            "created_at": goal.created_at.isoformat(),
            "updated_at": goal.updated_at.isoformat(),
            "meta_data": goal.meta_data,
        }


@function_tool
# Goal data (read/write, full autonomy)
async def get_goal_data(wrapper: RunContextWrapper[AgentContext], goal_id: int) -> dict:
    """Get the agent data for a specific goal."""
    user_id = int(wrapper.context.user_id)
    
    async with AsyncSessionLocal() as db:
        # Verify goal belongs to user
        goal = await goal_crud.get(db, goal_id)
        if not goal:
            raise ValueError(f"Goal {goal_id} not found")
        if goal.user_id != user_id:
            raise ValueError(f"Goal {goal_id} does not belong to user {user_id}")
        
        # Get goal data
        goal_data = await goal_data_crud.get_by(db, goal_id=goal_id)
        if not goal_data:
            return {}
        
        return goal_data.agent_data or {}


@function_tool
async def update_goal_data(
    wrapper: RunContextWrapper[AgentContext], goal_id: int, data: dict
) -> None:
    """Update the agent data for a specific goal."""
    user_id = int(wrapper.context.user_id)
    
    async with AsyncSessionLocal() as db:
        # Verify goal belongs to user
        goal = await goal_crud.get(db, goal_id)
        if not goal:
            raise ValueError(f"Goal {goal_id} not found")
        if goal.user_id != user_id:
            raise ValueError(f"Goal {goal_id} does not belong to user {user_id}")
        
        # Get or create goal data
        goal_data = await goal_data_crud.get_by(db, goal_id=goal_id)
        if goal_data:
            # Update existing data
            current_data = goal_data.agent_data or {}
            current_data.update(data)
            await goal_data_crud.update(db, goal_data.id, agent_data=current_data)
        else:
            # Create new goal data
            await goal_data_crud.create(db, goal_id=goal_id, agent_data=data)


@function_tool
async def append_goal_event(
    wrapper: RunContextWrapper[AgentContext], goal_id: int, event: dict
) -> None:
    """Append an event to the goal's event log in agent_data."""
    user_id = int(wrapper.context.user_id)
    
    async with AsyncSessionLocal() as db:
        # Verify goal belongs to user
        goal = await goal_crud.get(db, goal_id)
        if not goal:
            raise ValueError(f"Goal {goal_id} not found")
        if goal.user_id != user_id:
            raise ValueError(f"Goal {goal_id} does not belong to user {user_id}")
        
        # Get or create goal data
        goal_data = await goal_data_crud.get_by(db, goal_id=goal_id)
        
        # Add timestamp to event
        event["timestamp"] = datetime.utcnow().isoformat()
        
        if goal_data:
            # Append to existing events
            current_data = goal_data.agent_data or {}
            events = current_data.get("events", [])
            events.append(event)
            current_data["events"] = events
            await goal_data_crud.update(db, goal_data.id, agent_data=current_data)
        else:
            # Create new goal data with event
            await goal_data_crud.create(
                db, goal_id=goal_id, agent_data={"events": [event]}
            )


# Communication
@function_tool
async def send_message(
    wrapper: RunContextWrapper[AgentContext],
    content: str,
    goal_id: int = None,
    is_scheduled: bool = False,
) -> None:
    """Send a message to the user or schedule it for later."""
    user_id = int(wrapper.context.user_id)
    
    async with AsyncSessionLocal() as db:
        if is_scheduled:
            # Create scheduled message (will be sent by scheduler)
            await scheduled_message_crud.create(
                db,
                user_id=user_id,
                goal_id=goal_id,
                scheduled_for=datetime.utcnow(),  # Immediate scheduling
                message_content=content,
                status=MessageStatus.pending,
            )
        else:
            # Create message record
            await message_crud.create(
                db,
                user_id=user_id,
                goal_id=goal_id,
                role=MessageRole.assistant,
                content=content,
            )
            # TODO: Actually send via Telegram API


@function_tool
async def get_recent_messages(
    wrapper: RunContextWrapper[AgentContext], limit: int = 20, goal_id: int = None
) -> list[dict]:
    """Get recent messages for the user, optionally filtered by goal."""
    user_id = int(wrapper.context.user_id)
    
    async with AsyncSessionLocal() as db:
        filters = {"user_id": user_id}
        if goal_id is not None:
            filters["goal_id"] = goal_id
        
        messages = await message_crud.get_all(db, limit=limit, **filters)
        
        return [
            {
                "role": msg.role.value,
                "content": msg.content,
                "goal_id": msg.goal_id,
                "created_at": msg.created_at.isoformat(),
            }
            for msg in reversed(messages)  # Most recent first
        ]

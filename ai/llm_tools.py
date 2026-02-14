import os
import json
import httpx
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from pydantic import BaseModel, Field
from agents import function_tool, RunContextWrapper
from database import AsyncSessionLocal
from services import (
    user_crud,
    user_preference_crud,
    goal_crud,
    goal_data_crud,
    message_crud,
    scheduled_message_crud,
    skill_crud,
    goal_skill_crud,
)
from models.models import MessageRole, MessageStatus


class JsonData(BaseModel):
    """Flexible JSON data container."""

    class Config:
        extra = "forbid"  # This prevents additionalProperties

    data: str = Field(description="JSON string containing the data")


@dataclass
class AgentContext:
    """Context passed to all agent tools containing user-specific data."""

    user_id: str


@function_tool
# User context (read/write)
async def update_user_preferences(
    wrapper: RunContextWrapper[AgentContext], data_json: str
) -> None:
    """Update user preferences with the provided data as a JSON string."""
    import json

    user_id = int(wrapper.context.user_id)
    data = json.loads(data_json)

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
async def list_goals(wrapper: RunContextWrapper[AgentContext]) -> str:
    """List all goals for the current user with their progress data. Returns JSON string."""
    import json

    user_id = int(wrapper.context.user_id)

    async with AsyncSessionLocal() as db:
        goals = await goal_crud.get_all(db, user_id=user_id)
        result = []
        for goal in goals:
            goal_data = await goal_data_crud.get_by(db, goal_id=goal.id)
            result.append({
                "id": goal.id,
                "title": goal.title,
                "status": goal.status.value,
                "created_at": goal.created_at.isoformat(),
                "updated_at": goal.updated_at.isoformat(),
                "data": goal_data.agent_data if goal_data and goal_data.agent_data else {},
            })
        return json.dumps(result)


@function_tool
async def get_goal(wrapper: RunContextWrapper[AgentContext], goal_id: int) -> str:
    """Get a specific goal by ID. Returns JSON string."""
    import json

    user_id = int(wrapper.context.user_id)

    async with AsyncSessionLocal() as db:
        goal = await goal_crud.get(db, goal_id)
        if not goal:
            raise ValueError(f"Goal {goal_id} not found")

        # Verify goal belongs to user
        if goal.user_id != user_id:
            raise ValueError(f"Goal {goal_id} does not belong to user {user_id}")

        result = {
            "id": goal.id,
            "title": goal.title,
            "status": goal.status.value,
            "created_at": goal.created_at.isoformat(),
            "updated_at": goal.updated_at.isoformat(),
            "meta_data": goal.meta_data,
        }
        return json.dumps(result)


@function_tool
# Goal data (read/write, full autonomy)
async def get_goal_data(wrapper: RunContextWrapper[AgentContext], goal_id: int) -> str:
    """Get the agent data for a specific goal. Returns JSON string."""
    import json

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
            return json.dumps({})

        return json.dumps(goal_data.agent_data or {})


@function_tool
async def update_goal_data(
    wrapper: RunContextWrapper[AgentContext], goal_id: int, data_json: str
) -> None:
    """Update the agent data for a specific goal. Provide data as JSON string."""
    import json

    user_id = int(wrapper.context.user_id)
    data = json.loads(data_json)

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
    wrapper: RunContextWrapper[AgentContext], goal_id: int, event_json: str
) -> None:
    """Append an event to the goal's event log in agent_data. Provide event as JSON string."""
    import json

    user_id = int(wrapper.context.user_id)
    event = json.loads(event_json)

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
    goal_id: int | None = None,
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
    wrapper: RunContextWrapper[AgentContext],
    limit: int = 20,
    goal_id: int | None = None,
) -> str:
    """Get recent messages for the user, optionally filtered by goal. Returns JSON string."""
    import json

    user_id = int(wrapper.context.user_id)

    async with AsyncSessionLocal() as db:
        filters = {"user_id": user_id}
        if goal_id is not None:
            filters["goal_id"] = goal_id

        messages = await message_crud.get_all(db, limit=limit, **filters)

        result = [
            {
                "role": msg.role.value,
                "content": msg.content,
                "goal_id": msg.goal_id,
                "created_at": msg.created_at.isoformat(),
            }
            for msg in reversed(messages)  # Most recent first
        ]
        return json.dumps(result)


# Add these to your tools.py file

# ==================== SKILL MANAGEMENT TOOLS ====================


@function_tool
async def search_skills(
    wrapper: RunContextWrapper[AgentContext], query: str, top_k: int = 3
) -> str:
    """Search for existing skills using semantic/text matching. Returns JSON string with matching skills."""
    import json

    async with AsyncSessionLocal() as db:
        # Get active skills
        skills = await skill_crud.search(db, query=query, limit=top_k)

        result = [
            {
                "id": skill.id,
                "name": skill.name,
                "title": skill.title,
                "description": skill.description,
                "usage_count": skill.usage_count,
                "created_by_type": skill.created_by_type.value,
                "metadata": skill.skill_metadata,
            }
            for skill in skills
        ]
        return json.dumps(result)


@function_tool
async def get_skill(wrapper: RunContextWrapper[AgentContext], skill_id: int) -> str:
    """Get detailed information about a specific skill including its prompt. Returns JSON string."""
    import json

    async with AsyncSessionLocal() as db:
        skill = await skill_crud.get(db, skill_id)
        if not skill:
            raise ValueError(f"Skill {skill_id} not found")

        result = {
            "id": skill.id,
            "name": skill.name,
            "title": skill.title,
            "description": skill.description,
            "skill_prompt": skill.skill_prompt,
            "metadata": skill.skill_metadata,
            "usage_count": skill.usage_count,
            "created_by_type": skill.created_by_type.value,
            "created_at": skill.created_at.isoformat(),
        }
        return json.dumps(result)


@function_tool
async def create_skill(
    wrapper: RunContextWrapper[AgentContext],
    name: str,
    title: str,
    description: str,
    skill_prompt: str,
    metadata_json: str | None = None,
) -> int:
    """Create a new skill. Returns the skill ID."""
    import json
    from models.models import SkillCreatedBy

    user_id = int(wrapper.context.user_id)

    metadata = json.loads(metadata_json) if metadata_json else {}

    async with AsyncSessionLocal() as db:
        skill = await skill_crud.create(
            db,
            name=name,
            title=title,
            description=description,
            skill_prompt=skill_prompt,
            skill_metadata=metadata,
            created_by_type=SkillCreatedBy.agent,
            created_by_user_id=user_id,
            usage_count=1,
        )
        return skill.id


@function_tool
async def update_skill(
    wrapper: RunContextWrapper[AgentContext],
    skill_id: int,
    skill_prompt: str | None = None,
    description: str | None = None,
    metadata_json: str | None = None,
) -> None:
    """Update an existing skill's prompt, description, or metadata."""
    import json
    from models.models import SkillCreatedBy

    async with AsyncSessionLocal() as db:
        skill = await skill_crud.get(db, skill_id)
        if not skill:
            raise ValueError(f"Skill {skill_id} not found")

        # Only allow updating agent-created skills
        if skill.created_by_type == SkillCreatedBy.system:
            raise ValueError("Cannot update system skills")

        updates = {}
        if skill_prompt is not None:
            updates["skill_prompt"] = skill_prompt
            # Increment version in metadata
            metadata = skill.skill_metadata or {}
            metadata["version"] = metadata.get("version", 1) + 1
            metadata["last_improved"] = datetime.utcnow().isoformat()
            updates["skill_metadata"] = metadata

        if description is not None:
            updates["description"] = description

        if metadata_json is not None:
            metadata = json.loads(metadata_json)
            current_metadata = skill.skill_metadata or {}
            current_metadata.update(metadata)
            updates["skill_metadata"] = current_metadata

        if updates:
            await skill_crud.update(db, skill_id, **updates)


@function_tool
async def link_goal_to_skill(
    wrapper: RunContextWrapper[AgentContext],
    goal_id: int,
    skill_id: int,
    customizations_json: str | None = None,
) -> None:
    """Link a goal to a skill with optional customizations. Provide customizations as JSON string."""
    import json

    user_id = int(wrapper.context.user_id)

    customizations = json.loads(customizations_json) if customizations_json else {}

    async with AsyncSessionLocal() as db:
        # Verify goal belongs to user
        goal = await goal_crud.get(db, goal_id)
        if not goal:
            raise ValueError(f"Goal {goal_id} not found")
        if goal.user_id != user_id:
            raise ValueError(f"Goal {goal_id} does not belong to user {user_id}")

        # Verify skill exists
        skill = await skill_crud.get(db, skill_id)
        if not skill:
            raise ValueError(f"Skill {skill_id} not found")

        # Create link
        await goal_skill_crud.create(
            db, goal_id=goal_id, skill_id=skill_id, customizations=customizations
        )

        # Increment skill usage count
        await skill_crud.update(db, skill_id, usage_count=skill.usage_count + 1)


@function_tool
async def get_goal_skill(wrapper: RunContextWrapper[AgentContext], goal_id: int) -> str:
    """Get the skill(s) associated with a goal. Returns JSON string."""
    import json

    user_id = int(wrapper.context.user_id)

    async with AsyncSessionLocal() as db:
        # Verify goal belongs to user
        goal = await goal_crud.get(db, goal_id)
        if not goal:
            raise ValueError(f"Goal {goal_id} not found")
        if goal.user_id != user_id:
            raise ValueError(f"Goal {goal_id} does not belong to user {user_id}")

        # Get goal-skill links
        goal_skills = await goal_skill_crud.get_all(db, goal_id=goal_id)

        result = []
        for gs in goal_skills:
            skill = await skill_crud.get(db, gs.skill_id)
            result.append(
                {
                    "skill_id": skill.id,
                    "name": skill.name,
                    "title": skill.title,
                    "skill_prompt": skill.skill_prompt,
                    "customizations": gs.customizations,
                    "linked_at": gs.created_at.isoformat(),
                }
            )

        return json.dumps(result)


@function_tool
async def create_goal(
    wrapper: RunContextWrapper[AgentContext], title: str, status: str = "active"
) -> int:
    """Create a new goal for the user. Returns the goal ID."""
    user_id = int(wrapper.context.user_id)

    async with AsyncSessionLocal() as db:
        from models.models import GoalStatus

        goal = await goal_crud.create(
            db, user_id=user_id, title=title, status=GoalStatus(status)
        )
        return goal.id


@function_tool
async def update_goal_status(
    wrapper: RunContextWrapper[AgentContext], goal_id: int, status: str
) -> None:
    """Update a goal's status (active, paused, completed, abandoned)."""
    user_id = int(wrapper.context.user_id)

    async with AsyncSessionLocal() as db:
        from models.models import GoalStatus

        # Verify goal belongs to user
        goal = await goal_crud.get(db, goal_id)
        if not goal:
            raise ValueError(f"Goal {goal_id} not found")
        if goal.user_id != user_id:
            raise ValueError(f"Goal {goal_id} does not belong to user {user_id}")

        await goal_crud.update(db, goal_id, status=GoalStatus(status))


# ==================== REFERENCE DOCUMENTATION TOOLS ====================


@function_tool
async def read_reference_doc(
    wrapper: RunContextWrapper[AgentContext], doc_name: str
) -> str:
    """Read reference documentation to guide your behavior.

    Available documents:
    - 'skills.md' or 'skills': Complete specification for creating and managing skills

    Use this tool when you need to:
    - Create a new skill (MUST read skills.md first)
    - Understand skill structure and templates
    - Follow standardized patterns for goal types

    Returns the full content of the requested document.
    """
    # Normalize doc_name
    doc_map = {
        "skills": "skills.md",
        "skills.md": "skills.md",
    }

    normalized_name = doc_map.get(doc_name.lower())
    if not normalized_name:
        available = ", ".join(doc_map.keys())
        raise ValueError(f"Unknown document '{doc_name}'. Available: {available}")

    # Get the project root (assuming this file is in ai/ directory)
    project_root = Path(__file__).parent.parent
    doc_path = project_root / "prompts" / normalized_name

    if not doc_path.exists():
        raise FileNotFoundError(f"Document not found: {doc_path}")

    return doc_path.read_text(encoding="utf-8")


@function_tool
async def search_web(
    query: str,
    num_results: int = 10,
    search_type: str = "auto",
    max_characters: int = 20000,
) -> str:
    """Search the web using Exa API for latest information.

    Args:
        query: Search query string
        num_results: Number of results to return (default: 10)
        search_type: Type of search - "auto", "keyword", or "neural" (default: "auto")
        max_characters: Maximum characters to return per result (default: 20000)

    Returns:
        JSON string containing search results with text content
    """

    api_key = os.getenv("EXA_API_KEY")
    if not api_key:
        raise ValueError("EXA_API_KEY not found in environment variables")

    url = "https://api.exa.ai/search"
    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json",
    }

    payload = {
        "query": query,
        "type": search_type,
        "num_results": num_results,
        "contents": {"text": {"max_characters": max_characters}},
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=payload, timeout=30.0)
        response.raise_for_status()
        return json.dumps(response.json(), indent=2)

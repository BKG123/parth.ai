from dataclasses import dataclass
from agents import function_tool, RunContextWrapper


@dataclass
class AgentContext:
    """Context passed to all agent tools containing user-specific data."""

    user_id: str


@function_tool
# User context (read/write)
async def update_user_preferences(
    wrapper: RunContextWrapper[AgentContext], data: dict
) -> None:
    user_id = wrapper.context.user_id
    # TODO: Implement with user_id
    pass


@function_tool
# Goals metadata (read-only)
async def list_goals(wrapper: RunContextWrapper[AgentContext]) -> list[dict]:
    user_id = wrapper.context.user_id
    # TODO: Implement with user_id
    pass


@function_tool
async def get_goal(wrapper: RunContextWrapper[AgentContext], goal_id) -> dict:
    user_id = wrapper.context.user_id
    # TODO: Implement with user_id
    pass


@function_tool
# Goal data (read/write, full autonomy)
async def get_goal_data(wrapper: RunContextWrapper[AgentContext], goal_id) -> dict:
    user_id = wrapper.context.user_id
    # TODO: Implement with user_id
    pass


@function_tool
async def update_goal_data(
    wrapper: RunContextWrapper[AgentContext], goal_id, data: dict
) -> None:
    user_id = wrapper.context.user_id
    # TODO: Implement with user_id
    pass


@function_tool
async def append_goal_event(
    wrapper: RunContextWrapper[AgentContext], goal_id, event: dict
) -> None:
    user_id = wrapper.context.user_id
    # TODO: Implement with user_id
    pass


# Communication
@function_tool
async def send_message(
    wrapper: RunContextWrapper[AgentContext],
    content: str,
    goal_id: int = None,
    is_scheduled: bool = False,
) -> None:
    user_id = wrapper.context.user_id
    # TODO: Implement with user_id
    pass


@function_tool
async def get_recent_messages(
    wrapper: RunContextWrapper[AgentContext], limit: int = 20
) -> list[str]:
    user_id = wrapper.context.user_id
    # TODO: Implement with user_id
    pass

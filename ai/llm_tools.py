from agents import function_tool


@function_tool
# User context (read/write)
async def update_user_preferences(data: dict) -> None:
    pass


@function_tool
# Goals metadata (read-only)
async def list_goals() -> list[dict]:
    pass


@function_tool
async def get_goal(goal_id) -> dict:
    pass


@function_tool
# Goal data (read/write, full autonomy)
async def get_goal_data(goal_id) -> dict:
    pass


@function_tool
async def update_goal_data(goal_id, data: dict) -> None:
    pass


@function_tool
async def append_goal_event(goal_id, event: dict) -> None:
    pass


# Communication
@function_tool
async def send_message(
    content: str, goal_id: int = None, is_scheduled: bool = False
) -> None:
    pass


@function_tool
async def get_recent_messages(limit: int = 20) -> list[str]:
    pass

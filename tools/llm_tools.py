# User context (read/write)
async def get_user_preferences() -> dict:
    pass


async def update_user_preferences(data: dict) -> None:
    pass


# Goals metadata (read-only)
async def list_goals() -> list[dict]:
    pass


async def get_goal(goal_id) -> dict:
    pass


# Goal data (read/write, full autonomy)
async def get_goal_data(goal_id) -> dict:
    pass


async def update_goal_data(goal_id, data: dict) -> None:
    pass


async def append_goal_event(goal_id, event: dict) -> None:
    pass


# Communication
async def send_message(
    content: str, goal_id: int = None, is_scheduled: bool = False
) -> None:
    pass


async def get_recent_messages(limit: int = 20) -> list[str]:
    pass

"""
Parth.ai Worker
Background job processing for proactive agent check-ins
"""

import logging
import os

from arq import cron, create_pool
from arq.connections import RedisSettings
from sqlalchemy import select

from ai.proactive_agent import ProactiveAgent
from database import AsyncSessionLocal
from models.models import User, Goal, GoalStatus

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_SETTINGS = RedisSettings(host=REDIS_HOST, port=6379, database=0)


async def run_proactive_checkin(ctx: dict, user_id: int) -> dict:
    """Run proactive evaluation for a single user. Enqueued per-user or by cron."""
    logger.info(f"Running proactive check-in for user {user_id}")
    agent = ProactiveAgent()
    return await agent.run(user_id)


async def run_all_proactive_checkins(ctx: dict) -> None:
    """Cron: enqueue proactive check for all users with active goals (fallback)."""
    redis = ctx.get("redis")
    if not redis:
        logger.error("Redis not in ctx - cannot enqueue jobs")
        return

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User.id)
            .join(Goal, Goal.user_id == User.id)
            .where(Goal.status == GoalStatus.active, User.is_active)
            .distinct()
        )
        user_ids = [r[0] for r in result.fetchall()]
        logger.info(f"Found {len(user_ids)} users with active goals")

    for uid in user_ids:
        await redis.enqueue_job("run_proactive_checkin", uid)
    logger.info(f"Enqueued proactive check-ins for {len(user_ids)} users")


async def startup(ctx: dict) -> None:
    """Add redis pool to ctx for enqueueing from within jobs."""
    ctx["redis"] = await create_pool(REDIS_SETTINGS)


async def shutdown(ctx: dict) -> None:
    """Close redis connection."""
    redis = ctx.get("redis")
    if redis:
        await redis.close()


class WorkerSettings:
    functions = [run_proactive_checkin]
    cron_jobs = [
        # Every 2 min for testing (prod: hour=set(range(0, 24, 2)), minute=0)
        cron(run_all_proactive_checkins, minute=set(range(0, 60, 2))),
    ]
    redis_settings = REDIS_SETTINGS
    on_startup = startup
    on_shutdown = shutdown

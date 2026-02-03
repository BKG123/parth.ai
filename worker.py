"""
Parth.ai Worker
Background job processing for proactive agent check-ins
"""

import logging
from datetime import datetime
from arq import cron
from arq.connections import RedisSettings
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from database import AsyncSessionLocal
from models.models import User, Goal, GoalStatus
from ai.agent_manager import AgentManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Redis connection settings - using docker-compose redis
REDIS_SETTINGS = RedisSettings(host="localhost", port=6379, database=0)


async def run_agent_checkin_for_user(ctx, user_id: int):
    """
    Run proactive agent check-in for a specific user.
    
    This function:
    1. Gets the user's active goals
    2. Runs the agent to check on progress
    3. Sends appropriate nudges/encouragement
    4. Stores the interaction
    
    Args:
        ctx: Worker context
        user_id: The user's database ID
    """
    logger.info(f"Starting agent check-in for user {user_id}")
    
    async with AsyncSessionLocal() as session:
        try:
            # Get user with their active goals
            result = await session.execute(
                select(User)
                .options(selectinload(User.goals))
                .where(User.id == user_id, User.is_active == True)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                logger.warning(f"User {user_id} not found or inactive")
                return {"status": "skipped", "reason": "user_not_found_or_inactive"}
            
            # Get active goals
            active_goals = [g for g in user.goals if g.status == GoalStatus.active]
            
            if not active_goals:
                logger.info(f"User {user_id} has no active goals, skipping check-in")
                return {"status": "skipped", "reason": "no_active_goals"}
            
            # Create agent manager for this user
            agent_manager = AgentManager(user_id=str(user.telegram_id))
            
            # Craft proactive check-in prompt
            prompt = (
                "It's time for a proactive check-in. Review the user's active goals, "
                "their recent progress, and decide if you should send them an encouraging "
                "message, a gentle reminder, or ask how things are going. Be natural and "
                "context-aware - only reach out if it feels helpful, not just because it's "
                "scheduled. If there's nothing meaningful to say right now, you can skip."
            )
            
            # Run the agent
            response = await agent_manager.get_response(prompt=prompt)
            
            logger.info(f"Agent check-in completed for user {user_id}")
            logger.debug(f"Agent response: {response[:200]}...")  # Log first 200 chars
            
            return {
                "status": "completed",
                "user_id": user_id,
                "active_goals_count": len(active_goals),
                "timestamp": datetime.utcnow().isoformat(),
            }
            
        except Exception as e:
            logger.error(f"Error during agent check-in for user {user_id}: {e}", exc_info=True)
            return {
                "status": "failed",
                "user_id": user_id,
                "error": str(e),
            }


async def run_agent_checkins_all_users(ctx):
    """
    Cron job that runs proactive check-ins for all active users.
    
    This is the main scheduled task that runs every 2 hours and:
    1. Fetches all active users
    2. Enqueues individual check-in jobs for each user
    3. Logs the batch operation
    """
    logger.info("🪶 Starting scheduled agent check-ins for all users")
    
    async with AsyncSessionLocal() as session:
        try:
            # Get all active users
            result = await session.execute(
                select(User).where(User.is_active == True)
            )
            users = result.scalars().all()
            
            if not users:
                logger.info("No active users found")
                return {"status": "completed", "users_processed": 0}
            
            logger.info(f"Found {len(users)} active users")
            
            # Enqueue individual check-in jobs for each user
            from arq import create_pool
            redis = await create_pool(REDIS_SETTINGS)
            
            enqueued_count = 0
            for user in users:
                try:
                    job = await redis.enqueue_job(
                        'run_agent_checkin_for_user',
                        user.id,
                        _job_id=f"checkin_user_{user.id}_{datetime.utcnow().strftime('%Y%m%d_%H')}",
                    )
                    if job:
                        enqueued_count += 1
                        logger.debug(f"Enqueued check-in for user {user.id}")
                    else:
                        logger.debug(f"Check-in already enqueued for user {user.id}")
                except Exception as e:
                    logger.error(f"Failed to enqueue check-in for user {user.id}: {e}")
            
            await redis.close()
            
            logger.info(f"✅ Batch check-in completed: {enqueued_count}/{len(users)} jobs enqueued")
            
            return {
                "status": "completed",
                "total_users": len(users),
                "enqueued_count": enqueued_count,
                "timestamp": datetime.utcnow().isoformat(),
            }
            
        except Exception as e:
            logger.error(f"Error during batch agent check-ins: {e}", exc_info=True)
            return {
                "status": "failed",
                "error": str(e),
            }


async def startup(ctx):
    """Initialize resources on worker startup"""
    logger.info("🚀 Parth.ai worker starting up...")
    ctx["startup_time"] = datetime.utcnow()
    logger.info(f"✅ Worker ready at {ctx['startup_time']}")


async def shutdown(ctx):
    """Cleanup resources on worker shutdown"""
    logger.info("🛑 Parth.ai worker shutting down...")
    uptime = datetime.utcnow() - ctx["startup_time"]
    logger.info(f"Worker was up for {uptime}")


# WorkerSettings defines the configuration for the arq worker
class WorkerSettings:
    """
    Configuration for the Parth.ai arq worker.
    
    Run with: arq worker.WorkerSettings
    Run with watch: arq worker.WorkerSettings --watch .
    """

    # List of functions to register as jobs
    functions = [
        run_agent_checkin_for_user,
    ]

    # Cron jobs - scheduled tasks
    cron_jobs = [
        # Run agent check-ins every 2 hours
        # This runs at: 00:00, 02:00, 04:00, 06:00, 08:00, 10:00, 12:00, 14:00, 16:00, 18:00, 20:00, 22:00
        cron(
            run_agent_checkins_all_users,
            hour={0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22},
            minute=0,
            second=0,
        ),
    ]

    # Startup and shutdown hooks
    on_startup = startup
    on_shutdown = shutdown

    # Redis connection settings
    redis_settings = REDIS_SETTINGS

    # Worker configuration
    max_jobs = 10  # Maximum concurrent jobs
    job_timeout = 600  # Job timeout in seconds (10 minutes for agent runs)
    keep_result = 7200  # Keep results for 2 hours
    poll_delay = 0.5  # Poll for new jobs every 0.5 seconds
    queue_read_limit = 50  # Max jobs to pull from queue at once
    max_tries = 3  # Maximum retry attempts for failed jobs
    health_check_interval = 300  # Health check every 5 minutes
    log_results = True  # Log job results


if __name__ == "__main__":
    """
    Run the worker to process jobs:
    arq worker.WorkerSettings
    
    Run worker with auto-reload on code changes:
    arq worker.WorkerSettings --watch .
    """
    logger.info("Use 'arq worker.WorkerSettings' to start the worker")

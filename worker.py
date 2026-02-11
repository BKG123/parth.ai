"""
Parth.ai Worker
Background job processing for proactive agent check-ins
"""

import logging
from arq import cron
from arq.connections import RedisSettings

from tasks.scheduled_messages import execute_scheduled_messages

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Redis connection settings - using docker-compose redis
REDIS_SETTINGS = RedisSettings(host="localhost", port=6379, database=0)

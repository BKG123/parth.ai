import asyncio
from datetime import datetime
from httpx import AsyncClient
from arq import cron
from arq.connections import RedisSettings

# Redis connection settings - using docker-compose redis
REDIS_SETTINGS = RedisSettings(host="localhost", port=6379, database=0)


# Example async job
async def download_content(ctx, url: str):
    """Example job that downloads content from a URL"""
    session: AsyncClient = ctx["session"]
    response = await session.get(url)
    print(f"{url}: {response.status_code} - {len(response.text)} bytes")
    return {"url": url, "status": response.status_code, "length": len(response.text)}


# Example simple job
async def test_job(ctx, name: str = "World"):
    """Simple test job"""
    print(f"Hello, {name}! Job executed at {datetime.now()}")
    await asyncio.sleep(2)  # Simulate some work
    return f"Completed greeting for {name}"


# Example cron job - runs every minute
async def scheduled_task(ctx):
    """Cron job that runs on a schedule"""
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"⏰ Cron job executed at {current_time}")
    print(f"Enqueue time: {ctx.get('enqueue_time')}")
    return {"executed_at": current_time}


# Example periodic health check
async def health_check(ctx):
    """Regular health check task"""
    print("🏥 Health check running...")
    # Simulate health check logic
    await asyncio.sleep(1)
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


# Example data processing job
async def process_data(ctx, data_id: int, batch_size: int = 100):
    """Example job for data processing"""
    print(f"Processing data ID: {data_id} with batch size: {batch_size}")
    await asyncio.sleep(3)  # Simulate processing
    return {"data_id": data_id, "processed": True, "batch_size": batch_size}


# Startup function - runs when worker starts
async def startup(ctx):
    """Initialize resources on worker startup"""
    print("🚀 Worker starting up...")
    ctx["session"] = AsyncClient()
    ctx["startup_time"] = datetime.now()
    print(f"✅ Worker ready at {ctx['startup_time']}")


# Shutdown function - runs when worker stops
async def shutdown(ctx):
    """Cleanup resources on worker shutdown"""
    print("🛑 Worker shutting down...")
    await ctx["session"].aclose()
    uptime = datetime.now() - ctx["startup_time"]
    print(f"Worker was up for {uptime}")


# WorkerSettings defines the configuration for the arq worker
class WorkerSettings:
    """
    Configuration for the arq worker.
    Run with: arq worker.WorkerSettings
    """

    # List of functions to register as jobs
    functions = [
        download_content,
        test_job,
        process_data,
    ]

    # Cron jobs - scheduled tasks
    cron_jobs = [
        # Run every minute
        cron(scheduled_task, minute={0, 15, 30, 45}, second=0),
        # Run health check every 5 minutes
        cron(
            health_check,
            minute={0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55},
            second=0,
        ),
        # Run at specific time - every day at 9 AM
        # cron(daily_report, hour=9, minute=0, second=0),
    ]

    # Startup and shutdown hooks
    on_startup = startup
    on_shutdown = shutdown

    # Redis connection settings
    redis_settings = REDIS_SETTINGS

    # Worker configuration
    max_jobs = 10  # Maximum concurrent jobs
    job_timeout = 300  # Job timeout in seconds (5 minutes)
    keep_result = 3600  # Keep results for 1 hour
    poll_delay = 0.5  # Poll for new jobs every 0.5 seconds
    queue_read_limit = 50  # Max jobs to pull from queue at once
    max_tries = 5  # Maximum retry attempts for failed jobs
    health_check_interval = 60  # Health check every 60 seconds
    log_results = True  # Log job results


# Example script to enqueue jobs manually
async def enqueue_example_jobs():
    """Example function to enqueue jobs for testing"""
    from arq import create_pool

    redis = await create_pool(REDIS_SETTINGS)

    # Enqueue a simple test job
    job1 = await redis.enqueue_job("test_job", "Alice")
    print(f"Enqueued test_job: {job1.job_id if job1 else 'Already exists'}")

    # Enqueue a job with custom ID (prevents duplicates)
    job2 = await redis.enqueue_job("test_job", "Bob", _job_id="bob-greeting")
    print(
        f"Enqueued test_job with custom ID: {job2.job_id if job2 else 'Already exists'}"
    )

    # Enqueue a data processing job
    job3 = await redis.enqueue_job("process_data", 12345, batch_size=50)
    print(f"Enqueued process_data: {job3.job_id if job3 else 'Already exists'}")

    # Enqueue a job to run in 10 seconds
    job4 = await redis.enqueue_job("test_job", "Charlie", _defer_by=10)
    print(
        f"Enqueued deferred test_job (10s delay): {job4.job_id if job4 else 'Already exists'}"
    )

    # Enqueue download job
    for url in ["https://httpbin.org/get", "https://httpbin.org/json"]:
        job = await redis.enqueue_job("download_content", url)
        print(
            f"Enqueued download_content for {url}: {job.job_id if job else 'Already exists'}"
        )

    await redis.close()


if __name__ == "__main__":
    """
    Run this script to enqueue example jobs:
    python worker.py
    
    Run the worker to process jobs:
    arq worker.WorkerSettings
    
    Run worker in burst mode (stop after all jobs complete):
    arq worker.WorkerSettings --burst
    
    Run worker with auto-reload on code changes:
    arq worker.WorkerSettings --watch .
    """
    print("📋 Enqueueing example jobs...")
    asyncio.run(enqueue_example_jobs())
    print("✅ Jobs enqueued! Start the worker with: arq worker.WorkerSettings")

"""Main entry point for the worker service."""
import asyncio
import logging
import os
import signal

from core.manager import JobManager
from core.implementations import InMemoryResultProcessor, RedisRequestSource

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    """Main entry point for the job manager."""
    # Get configuration from environment
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    batch_window_ms = int(os.getenv("BATCH_WINDOW_MS", "250"))
    max_concurrent_jobs = int(os.getenv("MAX_CONCURRENT_JOBS", "5"))
    max_requests_per_job = int(os.getenv("MAX_REQUESTS_PER_JOB", "100"))
    
    # Create components
    request_source = RedisRequestSource(redis_url=redis_url)
    result_processor = InMemoryResultProcessor()
    
    # Create and configure job manager
    manager = JobManager(
        request_source=request_source,
        result_processor=result_processor,
        batch_window_ms=batch_window_ms,
        max_concurrent_jobs=max_concurrent_jobs,
        max_requests_per_job=max_requests_per_job,
    )
    
    # Set up signal handlers
    loop = asyncio.get_running_loop()
    stop = loop.create_future()
    
    def handle_signal(sig: signal.Signals) -> None:
        """Handle shutdown signals."""
        logger.info(f"Received signal {sig.name}")
        if not stop.done():
            stop.set_result(None)
    
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda s=sig: handle_signal(s))
    
    try:
        # Start the manager
        manager_task = asyncio.create_task(manager.run())
        
        # Wait for shutdown signal
        await stop
        
        # Shutdown gracefully
        await manager.shutdown()
        await manager_task
        
    except Exception as e:
        logger.error(f"Error in main: {e}", exc_info=True)
        raise
    finally:
        # Clean up signal handlers
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.remove_signal_handler(sig)


if __name__ == "__main__":
    asyncio.run(main())

"""Main entrypoint for running the API server and job management."""

import asyncio
import logging
import signal
from typing import Optional

from aiohttp import web

from api.app import create_app
from config import settings
from data.redis import RedisInteractor
from job.manager import JobManager

logger = logging.getLogger(__name__)


class Application:
    """Main application that manages both API and job management."""

    def __init__(self):
        """Initialize the application."""
        self.api: Optional[web.Application] = None
        self.job_manager: Optional[JobManager] = None
        self.data_interactor: Optional[RedisInteractor] = None
        self.shutdown_event = asyncio.Event()
        self._tasks = []

    async def start(self):
        """Start the application."""
        logger.info("Starting application...")

        # Create data interactor
        self.data_interactor = RedisInteractor(settings.REDIS_URL)

        # Create job manager with data interactor
        self.job_manager = JobManager(
            redis_url=settings.REDIS_URL,
            queue_name=settings.REDIS_QUEUE_NAME,
            batch_window_ms=settings.BATCH_WINDOW_MS,
            max_requests_per_job=settings.MAX_REQUESTS_PER_JOB,
        )

        # Create and configure the application with job manager and data interactor
        self.api = create_app(self.job_manager, self.data_interactor)

        # Start background tasks
        await self._start_background_tasks()

        # Start the web server
        runner = web.AppRunner(self.api)
        await runner.setup()
        site = web.TCPSite(runner, settings.API_HOST, settings.API_PORT)
        await site.start()
        logger.info(f"Web server started on {settings.API_HOST}:{settings.API_PORT}")

    async def _start_background_tasks(self):
        """Start background tasks."""
        logger.info("Starting background tasks...")

        # Start periodic purge task
        purge_task = asyncio.create_task(self._periodic_purge())
        self._tasks.append(purge_task)

    async def _stop_background_tasks(self):
        """Stop all background tasks."""
        logger.info("Stopping background tasks...")

        # Cancel all tasks
        for task in self._tasks:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        self._tasks.clear()

    async def _periodic_purge(self):
        """Periodically purge completed batches."""
        while not self.shutdown_event.is_set():
            try:
                await self.job_manager.purge()
            except Exception as e:
                logger.error(f"Error in purge task: {e}")
            await asyncio.sleep(0.1)

    async def _shutdown(self):
        """Handle shutdown signal."""
        logger.info("Shutdown signal received...")
        self.shutdown_event.set()

        # Stop background tasks
        await self._stop_background_tasks()

        # Cleanup job manager
        if self.job_manager:
            await self.job_manager.close()

        # Cleanup data interactor
        if self.data_interactor:
            await self.data_interactor.close()

        # Stop the web server
        if self.api:
            await self.api.shutdown()
            await self.api.cleanup()

        logger.info("Application shutdown complete")


def main():
    """Main entry point."""
    # Configure logging
    logging.basicConfig(level=settings.LOG_LEVEL, format="%(asctime)s %(levelname)s %(message)s")

    # Create and run the application
    app = Application()

    # Set up signal handlers
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda s=sig: asyncio.create_task(app._shutdown()))

    try:
        loop.run_until_complete(app.start())
        loop.run_until_complete(app.shutdown_event.wait())
    except Exception as e:
        logger.error(f"Error in main: {e}")
    finally:
        loop.close()


if __name__ == "__main__":
    main()

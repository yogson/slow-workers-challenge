"""Job manager for handling request batching and job creation."""

from datetime import datetime, timedelta
from typing import List
from uuid import UUID

import structlog
from redis import Redis
from rq import Queue
from rq.job import Job

from job.models import JobRequest, Batch
from job.task import process_batch


logger = structlog.getLogger(__name__)


class JobManager:
    """Manages job creation and processing with request batching."""

    def __init__(
        self,
        redis_url: str,
        queue_name: str,
        batch_window_ms: int = 250,
        max_requests_per_job: int = 4,
    ) -> None:
        """Initialize the job manager.

        Args:
            redis_url: Redis connection URL
            batch_window_ms: Time window in milliseconds for batching requests
            max_requests_per_job: Maximum number of requests to process in a single job
        """
        self.batch_window = timedelta(milliseconds=batch_window_ms)
        self.max_requests_per_job = max_requests_per_job
        self._redis_url = redis_url
        self._redis = Redis.from_url(redis_url)
        self._queue = Queue(queue_name, connection=self._redis)
        self.__batch = None

        self._is_running = False
        self._is_shutting_down = False
        logger.info(
            f"JobManager initialized with batch_window={batch_window_ms}ms, max_requests={max_requests_per_job}"
        )

    @property
    def _new_batch(self) -> Batch:
        return Batch(created_at=datetime.now(), requests=list())

    @property
    def _has_batch(self) -> bool:
        return self.__batch is not None

    @property
    def _batch_size(self) -> int | None:
        return None if not self._has_batch else len(self.__batch.requests)

    @property
    def _batch_requests(self) -> list[JobRequest]:
        if not self._has_batch:
            return []
        return self.__batch.requests

    @property
    def _batch_is_full(self) -> bool:
        return self._batch_size >= self.max_requests_per_job

    @property
    def _batch_age(self) -> timedelta:
        if self._has_batch:
            now = datetime.now()
            return now - self.__batch.created_at
        return timedelta()

    def _clear_batch(self) -> None:
        self.__batch = None

    def _add_to_batch(self, request: JobRequest) -> None:
        if not self._has_batch:
            self.__batch = self._new_batch
        self.__batch.requests.append(request)

    async def purge(self):
        """Create a new job if the batch is full or the time window has elapsed."""
        if not self._has_batch:
            return

        batch_age = self._batch_age
        if batch_age >= self.batch_window or self._batch_is_full:
            logger.info(
                "Creating new batch",
                batch_size=self._batch_size,
                time_elapsed_ms=batch_age.total_seconds() * 1000,
                reason="time_window" if batch_age >= self.batch_window else "batch_full",
                request_ids=[str(req.id) for req in self._batch_requests],
            )
            await self._create_job(self._batch_requests)
            self._clear_batch()

    async def _create_job(self, requests: List[JobRequest]) -> Job:
        """Create a new job to process the batch of requests.

        Args:
            requests: List of job requests to process
        Returns:
            Created RQ job
        """
        # Convert requests to dict for serialization
        requests_data = [{"id": str(req.id), "prompt": req.prompt} for req in requests]

        logger.info(
            "Enqueueing batch job",
            request_ids=[str(req.id) for req in requests],
            batch_size=len(requests),
        )

        return self._queue.enqueue(process_batch, requests_data, self._redis_url, job_timeout="1h")

    def _add_request(self, rid: UUID, prompt: str):
        """Add a new request to the current batch.

        Args:
            rid: Request ID
            prompt: Prompt text
        """
        logger.info(
            "Adding request to batch",
            request_id=str(rid),
            current_batch_size=self._batch_size,
            batch_age_ms=self._batch_age.total_seconds() * 1000,
        )

        self._add_to_batch(JobRequest(id=rid, prompt=prompt))

    async def process_request(self, rid: UUID, prompt: str):
        """Process a new request by adding it to the current batch.

        Args:
            rid: Request ID
            prompt: Prompt text
        """
        logger.info(f"Received new request {rid}")

        # First, check if we need to process any existing batch
        await self.purge()

        # Add the new request
        self._add_request(rid=rid, prompt=prompt)

        # Process the batch if it's full or time window has elapsed
        await self.purge()

    async def close(self):
        """Close the job manager and cleanup resources."""
        # Ensure any remaining requests are processed
        if self._batch_requests:
            await self._create_job(self._batch_requests)

        self._redis.close()

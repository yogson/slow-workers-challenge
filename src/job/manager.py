"""Job manager for handling request batching and job creation."""
from datetime import datetime, timedelta
from typing import List
from uuid import UUID

import structlog
from redis import Redis
from rq import Queue
from rq.job import Job

from job.models import JobRequest, Batch
from job.processor import process_batch


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
        self._batch = self._empty_batch
        
        self._is_running = False
        self._is_shutting_down = False
        logger.info(f"JobManager initialized with batch_window={batch_window_ms}ms, max_requests={max_requests_per_job}")

    @property
    def _empty_batch(self):
        return Batch(created_at=datetime.now(), requests=list())

    async def purge(self):
        """Create a new job if the batch is full or the time window has elapsed."""
        if not self._batch.requests:
            return
            
        now = datetime.now()
        time_elapsed = now - self._batch.created_at
        
        if time_elapsed >= self.batch_window or len(self._batch.requests) >= self.max_requests_per_job:
            logger.info(
                "Creating new batch",
                batch_size=len(self._batch.requests),
                time_elapsed_ms=time_elapsed.total_seconds() * 1000,
                reason="time_window" if time_elapsed >= self.batch_window else "batch_full",
                request_ids=[str(req.id) for req in self._batch.requests]
            )
            await self._create_job(self._batch.requests)
            self._batch = self._empty_batch
    
    async def _create_job(self, requests: List[JobRequest]) -> Job:
        """Create a new job to process the batch of requests.
        
        Args:
            requests: List of job requests to process
        Returns:
            Created RQ job
        """
        # Convert requests to dict for serialization
        requests_data = [
            {"id": str(req.id), "prompt": req.prompt}
            for req in requests
        ]

        logger.info(
            "Enqueueing batch job",
            request_ids=[str(req.id) for req in requests],
            batch_size=len(requests)
        )
        
        return self._queue.enqueue(
            process_batch,
            requests_data,
            self._redis_url,
            job_timeout="1h"
        )

    def _add_request(self, rid: UUID, prompt: str):
        """Add a new request to the current batch.
        
        Args:
            rid: Request ID
            prompt: Prompt text
        """
        logger.info(
            "Adding request to batch",
            request_id=str(rid),
            current_batch_size=len(self._batch.requests),
            batch_age_ms=(datetime.now() - self._batch.created_at).total_seconds() * 1000
        )
        
        self._batch.requests.append(
            JobRequest(id=rid, prompt=prompt)
        )

    async def process_request(self, rid: UUID, prompt: str):
        """Process a new request by adding it to the current batch.
        
        Args:
            rid: Request ID
            prompt: Prompt text
        """
        logger.info(f"Received new request {rid}")
        await self.purge()
        self._add_request(rid=rid, prompt=prompt)
        await self.purge()

    async def close(self):
        """Close the job manager and cleanup resources."""
        # Ensure any remaining requests are processed
        if self._batch.requests:
            await self._create_job(self._batch.requests)
        
        self._redis.close()



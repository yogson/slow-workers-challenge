"""Job manager for handling request batching and job creation."""
import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Set

from job.models import JobRequest, JobResult, JobStatus
from job.processor import Job
from core.interfaces import ResultProcessor, RequestSource

logger = logging.getLogger(__name__)


class JobManager:
    """Manages job creation and processing with request batching."""
    
    def __init__(
        self,
        request_source: RequestSource,
        result_processor: ResultProcessor,
        batch_window_ms: int = 250,
        max_concurrent_jobs: int = 5,
        max_requests_per_job: int = 100,
    ) -> None:
        """Initialize the job manager.
        
        Args:
            request_source: Source for getting requests
            result_processor: Processor for handling job results
            batch_window_ms: Time window in milliseconds for batching requests
            max_concurrent_jobs: Maximum number of concurrent jobs
            max_requests_per_job: Maximum number of requests per job
        """
        self.request_source = request_source
        self.result_processor = result_processor
        self.batch_window = timedelta(milliseconds=batch_window_ms)
        self.max_concurrent_jobs = max_concurrent_jobs
        self.max_requests_per_job = max_requests_per_job
        
        self._active_jobs: Set[Job] = set()
        self._job_semaphore = asyncio.Semaphore(max_concurrent_jobs)
        self._is_running = False
        self._is_shutting_down = False
    
    async def _create_job(self, requests: List[JobRequest]) -> Job:
        """Create a new job from a list of requests.
        
        Args:
            requests: List of requests to process in the job
            
        Returns:
            The created job
        """
        job_id = uuid.uuid4()
        job = Job(
            job_id=job_id,
            requests=requests,
            result_processor=self.result_processor,
        )
        return job
    
    async def _process_job(self, job: Job) -> JobResult:
        """Process a job and handle its completion.
        
        Args:
            job: The job to process
            
        Returns:
            The job result
        """
        try:
            result = await job.run()
            
            # Mark requests as processed
            await self.request_source.mark_processed([req.id for req in job.requests])
            
            return result
        except Exception as e:
            logger.error(f"Error processing job {job.job_id}: {e}", exc_info=True)
            return JobResult(
                job_id=job.job_id,
                status=JobStatus.FAILED,
                start_time=job.start_time or datetime.now(),
                end_time=datetime.now(),
                metrics=job.metrics,
                error=str(e),
            )
        finally:
            self._active_jobs.discard(job)
            self._job_semaphore.release()
    
    async def _batch_requests(self, requests: List[JobRequest]) -> List[List[JobRequest]]:
        """Batch requests based on creation time.
        
        Args:
            requests: List of requests to batch
            
        Returns:
            List of request batches
        """
        if not requests:
            return []
        
        # Sort requests by creation time
        sorted_requests = sorted(requests, key=lambda r: r.created_at)
        
        batches: List[List[JobRequest]] = []
        current_batch: List[JobRequest] = []
        current_window_start = sorted_requests[0].created_at
        
        for request in sorted_requests:
            # Check if request is within current window
            if request.created_at - current_window_start <= self.batch_window:
                current_batch.append(request)
                
                # Check if batch is full
                if len(current_batch) >= self.max_requests_per_job:
                    batches.append(current_batch)
                    current_batch = []
                    current_window_start = request.created_at
            else:
                # Start new batch
                if current_batch:
                    batches.append(current_batch)
                current_batch = [request]
                current_window_start = request.created_at
        
        # Add final batch if not empty
        if current_batch:
            batches.append(current_batch)
        
        return batches
    
    async def _process_batch(self, requests: List[JobRequest]) -> None:
        """Process a batch of requests by creating and running a job.
        
        Args:
            requests: List of requests to process
        """
        # Wait for a job slot
        await self._job_semaphore.acquire()
        
        # Create and run job
        job = await self._create_job(requests)
        self._active_jobs.add(job)
        
        # Start job processing
        asyncio.create_task(self._process_job(job))
    
    async def run(self) -> None:
        """Run the job manager, continuously processing requests."""
        if self._is_running:
            raise RuntimeError("Job manager is already running")
        
        self._is_running = True
        logger.info("Starting job manager")
        
        try:
            while not self._is_shutting_down:
                # Get requests from source
                requests = await self.request_source.get_requests()
                if not requests:
                    # No requests available, wait before checking again
                    await asyncio.sleep(0.1)
                    continue
                
                # Batch requests
                batches = await self._batch_requests(requests)
                
                # Process each batch
                for batch in batches:
                    if self._is_shutting_down:
                        break
                    await self._process_batch(batch)
                
                # Small delay to prevent tight loop
                await asyncio.sleep(0.01)
        
        except Exception as e:
            logger.error(f"Error in job manager: {e}", exc_info=True)
        finally:
            self._is_running = False
            logger.info("Job manager stopped")
    
    async def shutdown(self) -> None:
        """Shutdown the job manager gracefully."""
        logger.info("Shutting down job manager")
        self._is_shutting_down = True
        
        # Wait for active jobs to complete
        if self._active_jobs:
            await asyncio.gather(
                *(job.cancel() for job in self._active_jobs),
                return_exceptions=True,
            )
        
        # Close request source
        await self.request_source.close()
        
        logger.info("Job manager shutdown complete") 
"""Job processor for handling concurrent text generation requests."""
import asyncio
import logging
import time
import uuid
from datetime import datetime
from typing import List, Optional, Set

from generators.text import generate_text_response
from job.models import JobRequest, JobResult, JobMetrics, JobStatus
from job.result_processor import ResultProcessor

logger = logging.getLogger(__name__)


class Job:
    """A job consists of multiple text generation requests that are processed concurrently."""

    def __init__(
        self,
        job_id: uuid.UUID,
        requests: List[JobRequest],
        result_processor: ResultProcessor,
        max_concurrent_requests: int = 4,
    ) -> None:
        """Initialize a new job.
        
        Args:
            job_id: Unique identifier for the job
            requests: List of text generation requests to process
            result_processor: Interface for processing results
            max_concurrent_requests: Maximum number of requests to process concurrently
        """
        self.job_id = job_id
        self.requests = requests
        self.result_processor = result_processor
        self.max_concurrent_requests = max_concurrent_requests
        
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.metrics = JobMetrics(total_requests=len(requests))
        
        self._active_tasks: Set[asyncio.Task] = set()
        self._request_semaphore = asyncio.Semaphore(max_concurrent_requests)
        self._is_running = False
        self._is_cancelled = False

    async def process_request(self, request: JobRequest) -> None:
        """Process a single text generation request.
        
        Args:
            request: The text generation request to process
        """
        request_start_time = time.time()
        char_count = 0
        
        try:
            # Initialize the result in the processor
            await self.result_processor.initialize_result(request.id)
            
            # Process the prompt and stream results
            async for char in generate_text_response(request.prompt):
                if self._is_cancelled:
                    logger.warning(f"Cancelling request {request.id} due to job cancellation")
                    break
                
                # Send the character to the result processor
                await self.result_processor.append_result(request.id, char)
                char_count += 1
            
            request_time = time.time() - request_start_time
            self.metrics.successful_requests += 1
            self.metrics.total_chars_generated += char_count
            self.metrics.total_processing_time += request_time
            
            # Finalize the result with metadata
            await self.result_processor.finalize_result(
                request.id,
                metadata={
                    "processing_time": request_time,
                    "chars_generated": char_count,
                    "chars_per_second": char_count / request_time if request_time > 0 else 0,
                },
            )
            
            logger.info(
                f"Request {request.id} completed: {char_count} chars in {request_time:.2f}s "
                f"({char_count / request_time:.2f} chars/s)"
            )
            
        except Exception as e:
            error_msg = f"Error processing request {request.id}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.metrics.failed_requests += 1
            await self.result_processor.mark_error(request.id, str(e))
        finally:
            # Release the semaphore to allow another request to be processed
            self._request_semaphore.release()

    async def run(self) -> JobResult:
        """Run the job, processing all requests concurrently.
        
        Returns:
            The result of the job including metrics
        """
        if self._is_running:
            raise RuntimeError("Job is already running")
        
        self._is_running = True
        self.start_time = datetime.now()
        
        logger.info(f"Starting job {self.job_id} with {len(self.requests)} requests")
        
        try:
            # Create a task for each request, limited by the semaphore
            for request in self.requests:
                await self._request_semaphore.acquire()
                
                if self._is_cancelled:
                    self._request_semaphore.release()
                    break
                
                task = asyncio.create_task(self.process_request(request))
                self._active_tasks.add(task)
                task.add_done_callback(self._active_tasks.discard)
            
            # Wait for all tasks to complete
            if self._active_tasks:
                await asyncio.gather(*self._active_tasks, return_exceptions=True)
        
        except Exception as e:
            logger.error(f"Error running job {self.job_id}: {str(e)}", exc_info=True)
            await self.cancel()
            
            # Create an error result
            self.end_time = datetime.now()
            return JobResult(
                job_id=self.job_id,
                status=JobStatus.FAILED,
                start_time=self.start_time,
                end_time=self.end_time,
                metrics=self.metrics,
                error=str(e),
            )
        finally:
            self._is_running = False
            self.end_time = datetime.now()
        
        # Determine the final status
        status = JobStatus.COMPLETED
        if self._is_cancelled:
            status = JobStatus.CANCELLED
        elif self.metrics.failed_requests > 0:
            if self.metrics.failed_requests == self.metrics.total_requests:
                status = JobStatus.FAILED
            else:
                status = JobStatus.PARTIALLY_COMPLETED
        
        logger.info(
            f"Job {self.job_id} {status.value}: {self.metrics.successful_requests}/{self.metrics.total_requests} "
            f"requests completed successfully in {(self.end_time - self.start_time).total_seconds():.2f}s"
        )
        
        # Return the final result
        return JobResult(
            job_id=self.job_id,
            status=status,
            start_time=self.start_time,
            end_time=self.end_time,
            metrics=self.metrics,
        )

    async def cancel(self) -> None:
        """Cancel the job, stopping any active requests."""
        if not self._is_running:
            return
        
        logger.info(f"Cancelling job {self.job_id}")
        self._is_cancelled = True
        
        for task in self._active_tasks:
            if not task.done():
                task.cancel()
        
        if self._active_tasks:
            await asyncio.gather(*self._active_tasks, return_exceptions=True)

from uuid import UUID

import structlog

from data import RedisInteractor
from generators.text import generate_text_response
from job.models import JobRequest
from processor.prompt_processor import PromptProcessor

logger = structlog.getLogger(__name__)


def process_batch(requests_data: list[dict], redis_url: str) -> None:
    """Process a batch of requests using PromptProcessor.

    This function is meant to be executed by RQ workers.

    Args:
        requests_data: List of request data dictionaries
        redis_url: Redis connection URL
    """
    import asyncio

    async def process_requests():
        # Convert request data back to JobRequest objects
        requests = [
            JobRequest(id=UUID(req["id"]), prompt=req["prompt"])
            for req in requests_data
        ]

        logger.info(
            "Starting batch processing",
            request_ids=[str(req.id) for req in requests],
            batch_size=len(requests)
        )

        processor = PromptProcessor(
            data_interactor=RedisInteractor(redis_url=redis_url),
            generate_text_fn=generate_text_response
        )

        try:
            async def process_with_logging(request: JobRequest):
                """Process a single request with logging."""
                logger.info(f"Processing request {request.id} in batch")
                try:
                    await processor.process_prompt(request.id, request.prompt)
                    logger.info(f"Completed request {request.id} in batch")
                except Exception as e:
                    logger.error(f"Error processing request {request.id}: {e}")
                    raise

            # Process all requests in the batch in parallel
            await asyncio.gather(
                *[process_with_logging(request) for request in requests]
            )
            logger.info(
                "Completed batch processing",
                request_ids=[str(req.id) for req in requests]
            )
        finally:
            await processor.close()

    # Run the async processing in the RQ worker
    asyncio.run(process_requests())

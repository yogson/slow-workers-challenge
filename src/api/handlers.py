import asyncio
import uuid
from typing import AsyncGenerator

import structlog
from aiohttp import web

from api.models import GenerateRequest, GenerateResponse
from job.models import JobStatus

logger = structlog.get_logger()


async def process_request(request: web.Request) -> AsyncGenerator[str, None]:
    """Stream SSE responses from Redis."""

    try:
        body = await request.json()
        generate_request = GenerateRequest(**body)
        
        request_id = uuid.uuid4()
        
        # Get job manager and data interactor from application
        job_manager = request.app["job_manager"]
        data_interactor = request.app["data_interactor"]
        
        # Submit request to JobManager
        await job_manager.process_request(request_id, generate_request.prompt)
        
        try:
            # Stream results
            while True:
                # Check if client is still connected
                if request.transport.is_closing():
                    logger.info(f"Client disconnected for request {request_id}")
                    break
                
                # Get current response and proceed if not empty
                response_text = await data_interactor.get_response(request_id)
                if not response_text:
                    await asyncio.sleep(0.05)
                    continue

                status = await data_interactor.get_status(request_id)
                
                # Create response object
                response = GenerateResponse(
                    request_id=request_id,
                    text=response_text,
                    status=status.value
                )
                
                # Send response
                yield f"data: {response.model_dump_json()}\n\n"
                
                # Break if request is completed or failed
                if status in (JobStatus.COMPLETED, JobStatus.FAILED):
                    break
                
                await asyncio.sleep(0.05)
                
        except Exception as e:
            logger.error(f"Error in streaming loop: {e}")
            raise
            
    except Exception as e:
        # Send error response
        yield f"data: {GenerateResponse(
            request_id=request_id, text='', status=JobStatus.FAILED.value, error=str(e)
        ).model_dump_json()}\n\n"


async def generate_handler(request: web.Request) -> web.StreamResponse:
    """Handle /generate endpoint with SSE."""
    response = web.StreamResponse()
    response.headers["Content-Type"] = "text/event-stream"
    response.headers["Cache-Control"] = "no-cache"
    response.headers["Connection"] = "keep-alive"

    await response.prepare(request)

    try:
        async for data in process_request(request):
            try:
                await response.write(data.encode())
            except ConnectionResetError:
                # Client disconnected, stop streaming
                logger.info("Client disconnected, stopping stream")
                break
            except Exception as e:
                logger.error(f"Error writing to stream: {e}")
                break
    except Exception as e:
        logger.error(f"Error in generate handler: {e}")
        if not response.prepared:
            await response.prepare(request)
        await response.write(
            f"data: {GenerateResponse(
                request_id=uuid.uuid4(), text='', status=JobStatus.FAILED.value, error=str(e)
            ).model_dump_json()}\n\n".encode()
        )

    return response


async def health_handler(request: web.Request) -> web.Response:
    """Handle health check requests."""
    return web.json_response(data={"status": "ok"})

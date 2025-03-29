import asyncio
import uuid
from typing import AsyncGenerator

import structlog
from aiohttp import web
from redis.asyncio import Redis

from api.models import GenerateRequest, GenerateResponse
from config import settings

logger = structlog.get_logger()


async def process_request(request: web.Request) -> AsyncGenerator[str, None]:
    """Stream SSE responses from Redis."""

    try:
        # Parse request body
        body = await request.json()
        generate_request = GenerateRequest(**body)
        
        # Generate request ID
        request_id = uuid.uuid4()
        
        # Get job manager from application
        job_manager = request.app["job_manager"]
        
        # Submit request to JobManager
        await job_manager.process_request(request_id, generate_request.prompt)
        
        # Initialize Redis connection for streaming
        redis = Redis.from_url(settings.REDIS_URL)
        
        try:
            # Stream results
            while True:
                # Check if client is still connected
                if request.transport.is_closing():
                    logger.info(f"Client disconnected for request {request_id}")
                    break
                
                # Get current response and status from Redis
                response_text = await redis.get(f"response:{request_id}")
                status = await redis.get(f"status:{request_id}")
                
                if status:
                    status = status.decode()
                else:
                    status = "in_progress"
                
                # Create response object
                response = GenerateResponse(
                    request_id=request_id,
                    text=response_text.decode() if response_text else "",
                    status=status
                )
                
                # Send response
                yield f"data: {response.model_dump_json()}\n\n"
                
                # Break if request is completed or failed
                if status in ("completed", "error"):
                    break
                
                await asyncio.sleep(0.05)
                
        finally:
            await redis.close()
            
    except Exception as e:
        # Send error response
        yield f"data: {GenerateResponse(request_id=request_id, text='', status='error', error=str(e)).model_dump_json()}\n\n"


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
            f"data: {GenerateResponse(request_id=uuid.uuid4(), text='', status='error', error=str(e)).model_dump_json()}\n\n".encode()
        )

    return response


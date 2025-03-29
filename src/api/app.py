import structlog
from aiohttp import web

from api.handlers import generate_handler
from job.manager import JobManager

logger = structlog.get_logger()


async def logging_middleware(app: web.Application, handler):
    """Middleware for logging requests."""

    async def middleware_handler(request: web.Request) -> web.StreamResponse:
        logger.info("request_started", method=request.method, path=request.path)
        try:
            response = await handler(request)
            logger.info("request_completed", status=response.status)
            return response
        except Exception as e:
            logger.error("request_failed", error=str(e))
            raise

    return middleware_handler


async def health_handler(request: web.Request) -> web.Response:
    """Handle health check requests."""
    return web.Response(text="OK")


def create_app(job_manager: JobManager) -> web.Application:
    """Create and configure the aiohttp application.
    
    Args:
        job_manager: JobManager instance to use for request processing
    """
    app = web.Application()
    
    # Store job manager in application state
    app["job_manager"] = job_manager

    # Add routes
    app.router.add_get("/health", health_handler)
    app.router.add_post("/generate", generate_handler)

    # Add middleware for logging
    app.middlewares.append(logging_middleware)

    return app

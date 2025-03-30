import structlog
from aiohttp import web

from api.handlers import generate_handler, health_handler
from data.interfaces import DataInteractor
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


def create_app(job_manager: JobManager, data_interactor: DataInteractor) -> web.Application:
    """Create and configure the web application.
    
    Args:
        job_manager: Job manager instance for processing requests
        data_interactor: Data interactor instance for storing and retrieving responses
        
    Returns:
        Configured web application
    """
    app = web.Application()
    
    # Store dependencies in application state
    app["job_manager"] = job_manager
    app["data_interactor"] = data_interactor
    
    # Configure routes
    app.router.add_get("/health", health_handler)
    app.router.add_post("/generate", generate_handler)
    
    # Add middleware for logging
    app.middlewares.append(logging_middleware)

    return app

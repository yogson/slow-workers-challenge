"""Redis implementation of the data interactor interface."""

from typing import Optional
from uuid import UUID

from redis.asyncio import Redis as AsyncRedis

from data.interfaces import DataInteractor
from job.models import JobStatus


class RedisInteractor(DataInteractor):
    """Redis implementation of the data interactor interface."""

    def __init__(self, redis_url: str) -> None:
        """Initialize the Redis interactor.
        
        Args:
            redis_url: Redis connection URL
        """
        self._redis: AsyncRedis | None = None
        self._redis_url = redis_url

    @property
    async def redis(self) -> AsyncRedis:
        """Get Redis connection, creating it if necessary.
        
        Returns:
            Redis connection instance
        """
        if self._redis is None:
            self._redis = await AsyncRedis.from_url(self._redis_url)
        return self._redis

    async def write_response(self, request_id: UUID, text: str) -> None:
        """Write a complete response text.
        
        Args:
            request_id: Unique identifier for the request
            text: Response text to write
        """
        redis = await self.redis
        redis_key = f"response:{request_id}"
        await redis.set(redis_key, text)
        await self.set_status(request_id, JobStatus.IN_PROGRESS)

    async def append_response(self, request_id: UUID, char: str) -> None:
        """Append a character to the response text.
        
        Args:
            request_id: Unique identifier for the request
            char: Character to append
        """
        redis = await self.redis
        redis_key = f"response:{request_id}"
        await redis.append(redis_key, char)
        await self.set_status(request_id, JobStatus.IN_PROGRESS)

    async def write_error(self, request_id: UUID, error_message: str) -> None:
        """Write an error message to Redis.
        
        Args:
            request_id: Unique identifier for the request
            error_message: Error message to write
        """
        redis = await self.redis
        redis_key = f"response:{request_id}"
        await redis.set(redis_key, f"Error: {error_message}")
        await self.set_status(request_id, JobStatus.FAILED)

    async def set_status(self, request_id: UUID, status: JobStatus) -> None:
        """Set the status of a request.
        
        Args:
            request_id: Unique identifier for the request
            status: Status to set
        """
        redis = await self.redis
        await redis.set(f"status:{request_id}", status.value)

    async def get_status(self, request_id: UUID) -> JobStatus:
        """Get the current status of a request.
        
        Args:
            request_id: Unique identifier for the request
        Returns:
            Current status of the request
        """
        redis = await self.redis
        status = await redis.get(f"status:{request_id}")
        try:
            return JobStatus(status.decode()) if status else JobStatus.IN_PROGRESS
        except ValueError:
            return JobStatus.IN_PROGRESS

    async def get_response(self, request_id: UUID) -> Optional[str]:
        """Get the current response text for a request.
        
        Args:
            request_id: Unique identifier for the request
        Returns:
            Current response text if available, None otherwise
        """
        redis = await self.redis
        response = await redis.get(f"response:{request_id}")
        return response.decode() if response else None

    async def close(self) -> None:
        """Close Redis connection."""
        if self._redis is not None:
            await self._redis.close()
            self._redis = None

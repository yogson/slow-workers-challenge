"""Output writer interface and implementations."""

from typing import Protocol
from uuid import UUID

from redis.asyncio import Redis as AsyncRedis


class OutputWriter(Protocol):
    """Protocol defining the interface for output writers."""

    async def write_char(self, request_id: UUID, char: str) -> None:
        """Write a single character to the output.
        
        Args:
            request_id: Unique identifier for the request
            char: Character to write
        """
        ...

    async def write_error(self, request_id: UUID, error_message: str) -> None:
        """Write an error message to the output.
        
        Args:
            request_id: Unique identifier for the request
            error_message: Error message to write
        """
        ...

    async def mark_completed(self, request_id: UUID) -> None:
        """Mark a request as completed.
        
        Args:
            request_id: Unique identifier for the request
        """
        ...

    async def get_status(self, request_id: UUID) -> str:
        """Get the current status of a request.
        
        Args:
            request_id: Unique identifier for the request
        Returns:
            Current status of the request ("in_progress", "completed", "error")
        """
        ...

    async def close(self) -> None:
        """Close the output writer and cleanup resources."""
        ...


class RedisOutputWriter:
    """Redis implementation of the output writer."""

    def __init__(self, redis_url: str) -> None:
        """Initialize the Redis output writer.
        
        Args:
            redis_url: Redis connection URL
        """
        self._redis: AsyncRedis | None = None
        self._redis_url = redis_url

    async def _ensure_connection(self) -> None:
        """Ensure Redis connection is established."""
        if self._redis is None:
            self._redis = await AsyncRedis.from_url(self._redis_url)

    async def write_char(self, request_id: UUID, char: str) -> None:
        """Write a character to Redis.
        
        Args:
            request_id: Unique identifier for the request
            char: Character to write
        """
        await self._ensure_connection()
        redis_key = f"response:{request_id}"
        await self._redis.append(redis_key, char)
        await self._redis.set(f"status:{request_id}", "in_progress")

    async def write_error(self, request_id: UUID, error_message: str) -> None:
        """Write an error message to Redis.
        
        Args:
            request_id: Unique identifier for the request
            error_message: Error message to write
        """
        await self._ensure_connection()
        redis_key = f"response:{request_id}"
        await self._redis.set(redis_key, f"Error: {error_message}")
        await self._redis.set(f"status:{request_id}", "error")

    async def mark_completed(self, request_id: UUID) -> None:
        """Mark a request as completed.
        
        Args:
            request_id: Unique identifier for the request
        """
        await self._ensure_connection()
        await self._redis.set(f"status:{request_id}", "completed")

    async def get_status(self, request_id: UUID) -> str:
        """Get the current status of a request.
        
        Args:
            request_id: Unique identifier for the request
        Returns:
            Current status of the request ("in_progress", "completed", "error")
        """
        await self._ensure_connection()
        status = await self._redis.get(f"status:{request_id}")
        return status.decode() if status else "in_progress"

    async def close(self) -> None:
        """Close Redis connection."""
        if self._redis is not None:
            await self._redis.close()
            self._redis = None

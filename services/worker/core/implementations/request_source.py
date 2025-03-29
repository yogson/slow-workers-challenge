"""Redis-based implementation of the request source."""
import logging
from typing import List
import uuid
from datetime import datetime

from job.models import JobRequest
from core.interfaces import RequestSource

logger = logging.getLogger(__name__)


class RedisRequestSource(RequestSource):
    """Redis-based implementation of the request source."""
    
    def __init__(
        self,
        redis_url: str,
        queue_key: str = "text_generation_queue",
        processed_key: str = "processed_requests",
    ) -> None:
        """Initialize the Redis request source.
        
        Args:
            redis_url: URL for Redis connection
            queue_key: Key for the request queue in Redis
            processed_key: Key for tracking processed requests
        """
        self.redis_url = redis_url
        self.queue_key = queue_key
        self.processed_key = processed_key
        self._redis = None
    
    async def _get_redis(self):
        """Get Redis connection."""
        if self._redis is None:
            import redis.asyncio as redis
            self._redis = await redis.from_url(self.redis_url)
        return self._redis
    
    async def get_requests(self, batch_size: int = 100) -> List[JobRequest]:
        """Get a batch of requests from Redis queue.
        
        Args:
            batch_size: Maximum number of requests to retrieve
            
        Returns:
            List of job requests
        """
        redis = await self._get_redis()
        
        # Get requests from queue
        requests_data = await redis.lrange(self.queue_key, 0, batch_size - 1)
        if not requests_data:
            return []
        
        # Parse requests
        requests = []
        for data in requests_data:
            try:
                request_dict = eval(data.decode())  # TODO: Use proper serialization
                request = JobRequest(
                    id=uuid.UUID(request_dict["id"]),
                    prompt=request_dict["prompt"],
                    params=request_dict.get("params", {}),
                    created_at=datetime.fromisoformat(request_dict["created_at"]),
                )
                requests.append(request)
            except Exception as e:
                logger.error(f"Error parsing request data: {e}")
                continue
        
        return requests
    
    async def mark_processed(self, request_ids: List[uuid.UUID]) -> None:
        """Mark requests as processed in Redis.
        
        Args:
            request_ids: List of request IDs to mark as processed
        """
        if not request_ids:
            return
            
        redis = await self._get_redis()
        
        # Remove processed requests from queue
        for request_id in request_ids:
            await redis.lrem(self.queue_key, 0, str(request_id))
        
        # Add to processed set
        await redis.sadd(self.processed_key, *[str(rid) for rid in request_ids])
    
    async def close(self) -> None:
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()
            self._redis = None 
"""Interface for request sources."""
from abc import ABC, abstractmethod
from typing import List
import uuid

from job.models import JobRequest


class RequestSource(ABC):
    """Interface for request sources."""
    
    @abstractmethod
    async def get_requests(self, batch_size: int = 100) -> List[JobRequest]:
        """Get a batch of requests from the source.
        
        Args:
            batch_size: Maximum number of requests to retrieve
            
        Returns:
            List of job requests
        """
        pass
    
    @abstractmethod
    async def mark_processed(self, request_ids: List[uuid.UUID]) -> None:
        """Mark requests as processed in the source.
        
        Args:
            request_ids: List of request IDs to mark as processed
        """
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """Close the request source and clean up resources."""
        pass 
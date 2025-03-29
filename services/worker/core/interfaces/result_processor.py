"""Interface for processing job results."""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import uuid


class ResultProcessor(ABC):
    """Interface for processing job results."""
    
    @abstractmethod
    async def initialize_result(self, request_id: uuid.UUID) -> None:
        """Initialize a new result for a request.
        
        Args:
            request_id: ID of the request to initialize result for
        """
        pass
    
    @abstractmethod
    async def append_result(self, request_id: uuid.UUID, chunk: str) -> None:
        """Append a chunk to the result for a request.
        
        Args:
            request_id: ID of the request to append result for
            chunk: Chunk of text to append
        """
        pass
    
    @abstractmethod
    async def finalize_result(
        self,
        request_id: uuid.UUID,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Finalize the result for a request.
        
        Args:
            request_id: ID of the request to finalize result for
            metadata: Optional metadata to attach to the result
        """
        pass
    
    @abstractmethod
    async def mark_error(self, request_id: uuid.UUID, error: str) -> None:
        """Mark a request as failed with an error.
        
        Args:
            request_id: ID of the request to mark as failed
            error: Error message to attach
        """
        pass 
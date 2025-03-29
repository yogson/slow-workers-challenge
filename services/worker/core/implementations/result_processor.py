"""In-memory implementation of the result processor."""
from typing import Any, Dict, Optional
import uuid

from core.interfaces import ResultProcessor

class InMemoryResultProcessor(ResultProcessor):
    """In-memory implementation of the result processor."""
    
    def __init__(self) -> None:
        """Initialize the in-memory result processor."""
        self._results: Dict[uuid.UUID, str] = {}
        self._metadata: Dict[uuid.UUID, Dict[str, Any]] = {}
        self._errors: Dict[uuid.UUID, str] = {}
    
    async def initialize_result(self, request_id: uuid.UUID) -> None:
        """Initialize a new result for a request.
        
        Args:
            request_id: ID of the request to initialize result for
        """
        self._results[request_id] = ""
        self._metadata[request_id] = {}
        self._errors.pop(request_id, None)
    
    async def append_result(self, request_id: uuid.UUID, chunk: str) -> None:
        """Append a chunk to the result for a request.
        
        Args:
            request_id: ID of the request to append result for
            chunk: Chunk of text to append
        """
        if request_id not in self._results:
            await self.initialize_result(request_id)
        self._results[request_id] += chunk
    
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
        if metadata:
            self._metadata[request_id].update(metadata)
    
    async def mark_error(self, request_id: uuid.UUID, error: str) -> None:
        """Mark a request as failed with an error.
        
        Args:
            request_id: ID of the request to mark as failed
            error: Error message to attach
        """
        self._errors[request_id] = error
    
    def get_result(self, request_id: uuid.UUID) -> Optional[str]:
        """Get the result for a request.
        
        Args:
            request_id: ID of the request to get result for
            
        Returns:
            The result text if available, None otherwise
        """
        return self._results.get(request_id)
    
    def get_metadata(self, request_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        """Get the metadata for a request.
        
        Args:
            request_id: ID of the request to get metadata for
            
        Returns:
            The metadata if available, None otherwise
        """
        return self._metadata.get(request_id)
    
    def get_error(self, request_id: uuid.UUID) -> Optional[str]:
        """Get the error for a request.
        
        Args:
            request_id: ID of the request to get error for
            
        Returns:
            The error message if available, None otherwise
        """
        return self._errors.get(request_id) 
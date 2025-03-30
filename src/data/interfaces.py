"""Data interaction interfaces."""

from typing import Protocol, Optional
from uuid import UUID


class DataInteractor(Protocol):
    """Interface for data interaction operations."""

    async def write_response(self, request_id: UUID, text: str) -> None:
        """Write a response text.
        
        Args:
            request_id: Unique identifier for the request
            text: Response text to write
        """
        ...

    async def append_response(self, request_id: UUID, char: str) -> None:
        """Append a character to the response text.
        
        Args:
            request_id: Unique identifier for the request
            char: Character to append
        """
        ...

    async def write_error(self, request_id: UUID, error_message: str) -> None:
        """Write an error message.
        
        Args:
            request_id: Unique identifier for the request
            error_message: Error message to write
        """
        ...

    async def get_response(self, request_id: UUID) -> Optional[str]:
        """Get the response text.
        
        Args:
            request_id: Unique identifier for the request
        Returns:
            Response text if exists, None otherwise
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

    async def set_status(self, request_id: UUID, status: str) -> None:
        """Set the status of a request.
        
        Args:
            request_id: Unique identifier for the request
            status: Status to set ("in_progress", "completed", "error")
        """
        ...

    async def close(self) -> None:
        """Close the data interactor and cleanup resources."""
        ... 
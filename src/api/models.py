import uuid
from typing import Optional

from pydantic import BaseModel, Field


class GenerateRequest(BaseModel):
    """Request model for text generation."""

    prompt: str = Field(..., min_length=1)


class GenerateResponse(BaseModel):
    """Response model for text generation."""

    request_id: uuid.UUID
    text: str
    status: str = "in_progress"
    error: Optional[str] = None

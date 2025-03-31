import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class JobStatus(str, Enum):
    """Status of a job."""

    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"
    PARTIALLY_COMPLETED = "partially_completed"
    IN_PROGRESS = "in_progress"


@dataclass
class JobRequest:
    """Represents a single text generation request within a job."""

    id: uuid.UUID
    prompt: str

    def __post_init__(self) -> None:
        """Validate the job request after initialization."""
        if not isinstance(self.id, uuid.UUID):
            self.id = uuid.UUID(self.id) if isinstance(self.id, str) else uuid.uuid4()

        if not self.prompt:
            raise ValueError("Prompt cannot be empty")


@dataclass
class JobMetrics:
    """Metrics for a completed job."""

    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_processing_time: float = 0.0

    @property
    def success_rate(self) -> float:
        """Calculate the success rate of the job."""
        if self.total_requests == 0:
            return 0.0
        return self.successful_requests / self.total_requests

    @property
    def avg_processing_time(self) -> float:
        """Calculate the average processing time per request."""
        if self.total_requests == 0:
            return 0.0
        return self.total_processing_time / self.total_requests


@dataclass
class JobResult:
    """Overall results of a job."""

    job_id: uuid.UUID
    status: JobStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    metrics: JobMetrics = field(default_factory=JobMetrics)
    error: Optional[str] = None


@dataclass
class Batch:
    requests: list[JobRequest]
    created_at: datetime = field(default_factory=datetime.now)

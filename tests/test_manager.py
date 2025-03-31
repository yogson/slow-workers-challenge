"""Unit tests for JobManager class."""
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from rq import Queue
from rq.job import Job

from job.manager import JobManager
from job.models import JobRequest
from job.task import process_batch


@pytest.fixture
def mock_redis():
    """Create a mock Redis instance."""
    with patch('job.manager.Redis') as mock:
        redis_instance = MagicMock()
        mock.from_url.return_value = redis_instance
        yield redis_instance


@pytest.fixture
def mock_queue():
    """Create a mock RQ Queue instance."""
    with patch('job.manager.Queue') as mock:
        queue_instance = MagicMock()
        mock.return_value = queue_instance
        yield queue_instance


@pytest.fixture
def job_manager(mock_redis, mock_queue):
    """Create a JobManager instance with mocked dependencies."""
    manager = JobManager(
        redis_url="redis://localhost:6379",
        queue_name="test_queue",
        batch_window_ms=100,  # Small window for faster tests
        max_requests_per_job=2
    )
    return manager


@pytest.mark.asyncio
async def test_process_request_creates_job_when_batch_full(job_manager, mock_queue):
    """Test that a job is created when the batch is full."""
    # Create two requests to fill the batch
    request1 = JobRequest(id=uuid4(), prompt="test1")
    request2 = JobRequest(id=uuid4(), prompt="test2")
    
    # Process requests
    await job_manager.process_request(request1.id, request1.prompt)
    await job_manager.process_request(request2.id, request2.prompt)
    
    # Verify job was created with correct data
    mock_queue.enqueue.assert_called_once()
    args = mock_queue.enqueue.call_args[0]
    assert args[0] == process_batch  # Function to execute
    assert len(args[1]) == 2  # Batch size
    assert args[1][0]["id"] == str(request1.id)
    assert args[1][1]["id"] == str(request2.id)


@pytest.mark.asyncio
async def test_process_request_creates_job_when_time_window_elapsed(job_manager, mock_queue):
    """Test that a job is created when the time window has elapsed."""
    # Process one request
    request = JobRequest(id=uuid4(), prompt="test")
    await job_manager.process_request(request.id, request.prompt)
    
    # Simulate time passing
    with patch('job.manager.datetime') as mock_datetime:
        mock_datetime.now.return_value = datetime.now() + timedelta(milliseconds=150)
        await job_manager.purge()
    
    # Verify job was created
    mock_queue.enqueue.assert_called_once()
    args = mock_queue.enqueue.call_args[0]
    assert len(args[1]) == 1  # Batch size
    assert args[1][0]["id"] == str(request.id)


@pytest.mark.asyncio
async def test_process_request_combines_requests_in_batch(job_manager, mock_queue):
    """Test that requests are combined in the same batch until full."""
    # Process three requests
    request1 = JobRequest(id=uuid4(), prompt="test1")
    request2 = JobRequest(id=uuid4(), prompt="test2")
    request3 = JobRequest(id=uuid4(), prompt="test3")
    
    await job_manager.process_request(request1.id, request1.prompt)
    await job_manager.process_request(request2.id, request2.prompt)
    await job_manager.process_request(request3.id, request3.prompt)
    
    # Simulate time passing to trigger processing of the third request
    with patch('job.manager.datetime') as mock_datetime:
        mock_datetime.now.return_value = datetime.now() + timedelta(milliseconds=150)
        await job_manager.purge()
    
    # Verify two jobs were created (batch size of 2)
    assert mock_queue.enqueue.call_count == 2
    
    # Verify first batch
    first_batch = mock_queue.enqueue.call_args_list[0][0][1]
    assert len(first_batch) == 2
    assert first_batch[0]["id"] == str(request1.id)
    assert first_batch[1]["id"] == str(request2.id)
    
    # Verify second batch
    second_batch = mock_queue.enqueue.call_args_list[1][0][1]
    assert len(second_batch) == 1
    assert second_batch[0]["id"] == str(request3.id)


@pytest.mark.asyncio
async def test_close_creates_job_with_remaining_requests(job_manager, mock_queue):
    """Test that close() creates a job with any remaining requests."""
    # Process one request
    request = JobRequest(id=uuid4(), prompt="test")
    await job_manager.process_request(request.id, request.prompt)
    
    # Close the manager
    await job_manager.close()
    
    # Verify job was created with remaining request
    mock_queue.enqueue.assert_called_once()
    args = mock_queue.enqueue.call_args[0]
    assert len(args[1]) == 1
    assert args[1][0]["id"] == str(request.id)


@pytest.mark.asyncio
async def test_purge_does_nothing_with_empty_batch(job_manager, mock_queue):
    """Test that purge() does nothing when there are no requests in the batch."""
    await job_manager.purge()
    mock_queue.enqueue.assert_not_called() 
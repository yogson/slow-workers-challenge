"""Core implementations for the worker service."""
from .result_processor import InMemoryResultProcessor
from .request_source import RedisRequestSource

__all__ = ["InMemoryResultProcessor", "RedisRequestSource"] 
"""Core interfaces for the worker service."""
from .result_processor import ResultProcessor
from .request_source import RequestSource

__all__ = ["ResultProcessor", "RequestSource"] 
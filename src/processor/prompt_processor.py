"""Prompt processor for handling text generation and output storage."""

import logging
import time
from typing import AsyncGenerator, Callable
from uuid import UUID

from .output import OutputWriter

logger = logging.getLogger(__name__)


class PromptProcessor:
    """Processes prompts and stores generated responses using the configured output writer."""

    def __init__(
        self,
        output_writer: OutputWriter,
        generate_text_fn: Callable[[str], AsyncGenerator[str, None]],
    ) -> None:
        """Initialize the prompt processor.
        
        Args:
            output_writer: Writer implementation for storing generated responses
            generate_text_fn: Async generator function that yields text response characters
        """
        self._output_writer = output_writer
        self._generate_text = generate_text_fn

    async def process_prompt(self, request_id: UUID, prompt: str) -> None:
        """Process a prompt and store the generated response using the output writer.
        
        Args:
            request_id: Unique identifier for the request
            prompt: The input prompt to generate a response for
        """
        start_time = time.time()
        logger.info(
            "Starting prompt processing",
            request_id=str(request_id),
            prompt_length=len(prompt)
        )
        
        try:
            char_count = 0
            # Generate and store response character by character
            async for char in self._generate_text(prompt):
                await self._output_writer.write_char(request_id, char)
                char_count += 1
                
            # Mark the request as completed
            await self._output_writer.mark_completed(request_id)
            processing_time = time.time() - start_time
            
            logger.info(
                "Completed prompt processing",
                request_id=str(request_id),
                char_count=char_count,
                processing_time_ms=processing_time * 1000,
                chars_per_second=char_count / processing_time if processing_time > 0 else 0
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(
                "Error processing prompt",
                request_id=str(request_id),
                error=str(e),
                processing_time_ms=processing_time * 1000
            )
            await self._output_writer.write_error(request_id, str(e))
            raise

    async def close(self) -> None:
        """Close the prompt processor and cleanup resources."""
        await self._output_writer.close()

"""Text generation module for creating responses to prompts.

This module provides functionality for generating text responses to user prompts
in a streaming fashion, yielding one character at a time to simulate a real-time
text generation process.
"""

import asyncio
import logging
import random
import time
from typing import AsyncGenerator, Dict, Any

logger = logging.getLogger(__name__)

DELAY_PER_CHAR = 0.01
MAX_DELAY_BETWEEN_WORDS = 0.2
RESPONSE_LENGTH_FACTOR = 3

WORDS = [
    "the", "a", "an", "in", "on", "with", "for", "to", "from",
    "text", "response", "generation", "process", "system", "model",
    "input", "output", "data", "information", "content",
    "analysis", "research", "development", "implementation", "solution",
    "approach", "methodology", "framework", "architecture", "design",
    "optimization", "performance", "efficiency", "reliability", "scalability",
    "integration", "deployment", "monitoring", "maintenance", "support"
]


def _get_response(words: list[str]) -> str:
    """
    Generate a simple response based on the prompt
    This is a mock implementation that creates a response with similar length to the prompt
    """

    response_parts = []

    # Use the prompt words but shuffle and modify them slightly
    response_word_count = max(5, int(len(words) * RESPONSE_LENGTH_FACTOR))

    # Create response by assembling words
    for _ in range(response_word_count):
        if random.random() < 0.5 and words:  # 50% chance to use a word from the prompt
            word: str = random.choice(words)
            # Sometimes modify the word
            if random.random() < 0.3:
                word = word.upper()
        else:
            # Use some generic words
            word = random.choice(WORDS)

        response_parts.append(word)

    response_parts[0] = response_parts[0].capitalize()
    return " ".join(response_parts)


async def generate_text_response(prompt: str) -> AsyncGenerator[str, None]:
    """Generate a text response to the given prompt and stream it character by character.
    
    Args:
        prompt: The input prompt to generate a response for
    Yields:
        Characters of the generated response, one at a time
    """

    words = prompt.split()
    response = _get_response(words)
    
    # Add a conclusion
    conclusion = random.choice([
        f"\n\nBased on your prompt \"{prompt[:20]}{'...' if len(prompt) > 20 else ''}\", this is my response.",
        f"\n\nI hope this helps with your request about {words[0] if words else 'this topic'}.",
        f"\n\nThank you for your prompt. This was my generated response.",
    ])
    
    response += conclusion
    
    # Stream the response character by character
    for i, char in enumerate(response):
        # Add an extra delay between words
        if i > 0 and response[i-1] == ' ' and random.random() < 0.3:
            await asyncio.sleep(random.uniform(0, MAX_DELAY_BETWEEN_WORDS))
        
        # Basic delay for each character
        await asyncio.sleep(DELAY_PER_CHAR)
        
        yield char

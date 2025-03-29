"""Tests for the text generator module."""
import asyncio
import pytest
import time
from unittest import mock

from generators.text import generate_text_response, DELAY_PER_CHAR, MAX_DELAY_BETWEEN_WORDS


@pytest.mark.asyncio
async def test_generate_text_response():
    """Test that the text generator produces a character stream."""
    # Test prompt
    prompt = "This is a test prompt."
    
    # Patch the sleep function to make tests run faster
    with mock.patch('asyncio.sleep', new=lambda _: asyncio.sleep(0)):
        # Collect all characters from the generator
        result = ""
        async for char in generate_text_response(prompt):
            result += char
    
    # Verify the result
    assert result, "Response should not be empty"
    assert len(result) > len(prompt), "Response should be longer than the prompt"
    
    # Check that the response contains at least some of the words from the prompt
    prompt_words = prompt.strip(".").lower().split()
    response_words = set(word.lower() for word in result.split())
    
    # At least one word from the prompt should appear in the response
    assert any(word in response_words for word in prompt_words), \
        "Response should contain at least one word from the prompt"


@pytest.mark.asyncio
async def test_generate_text_response_timing():
    """Test the timing behavior of the generator."""
    prompt = "Short test."
    
    # Set a faster delay for testing purposes
    original_delay = DELAY_PER_CHAR
    
    # Patch the module constants for faster testing
    with mock.patch('worker.generators.text.DELAY_PER_CHAR', 0.01):
        with mock.patch('worker.generators.text.MAX_DELAY_BETWEEN_WORDS', 0):  # Disable word delays for consistent timing
            # Measure time taken
            start_time = time.time()
            
            char_count = 0
            async for _ in generate_text_response(prompt):
                char_count += 1
            
            elapsed = time.time() - start_time
    
    # With the given delay, generation should take at least:
    # (character count * mocked_delay_per_char) seconds
    expected_min_time = char_count * 0.01 * 0.8  # 80% of expected time to account for timing variations
    
    # Verify the timing (with some tolerance)
    assert elapsed >= expected_min_time, \
        f"Generation was too fast: {elapsed:.2f}s vs expected min {expected_min_time:.2f}s"


@pytest.mark.asyncio
async def test_generate_text_response_content_structure():
    """Test that the generator produces a well-formed response with a conclusion."""
    prompt = "Test the response structure."
    
    # Patch the sleep function to make tests run faster
    with mock.patch('asyncio.sleep', new=lambda _: asyncio.sleep(0)):
        # Collect all characters from the generator
        result = ""
        async for char in generate_text_response(prompt):
            result += char
    
    # Verify that the response contains a conclusion
    assert "\n\n" in result, "Response should contain a double newline before conclusion"
    
    # Check that one of the conclusion phrases is present
    conclusion_markers = [
        "Based on your prompt",
        "I hope this helps",
        "Thank you for your prompt"
    ]
    
    assert any(marker in result for marker in conclusion_markers), \
        "Response should contain one of the conclusion phrases" 
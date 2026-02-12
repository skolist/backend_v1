"""
Contains the logic to retry calls to Gemini's generate_content method.
"""

import asyncio
import logging
from typing import Any

from google import genai

logger = logging.getLogger(__name__)


async def generate_content_with_retries(
    api_endpoint: str,
    gemini_client: genai.Client,
    model: str,
    contents: Any,
    config: dict[str, Any] | None = None,
    retries: int = 5,
    initial_delay: float = 1.0,
) -> Any:
    """Call Gemini generate_content with retry logic.

    Retries transient failures up to `retries` times with exponential backoff.

    Args:
        gemini_client: Initialized GenAI client with aio support
        model: Gemini model name
        contents: Prompt contents or parts for the request
        config: Optional generation config dict
        retries: Max retry attempts on exception
        initial_delay: Initial backoff delay in seconds

    Returns:
        The response from `gemini_client.aio.models.generate_content`.

    Raises:
        Exception: Re-raises the last exception after exhausting retries.
    """
    attempt = 0
    delay = initial_delay
    last_exc: Exception | None = None

    while attempt < retries:
        try:
            logger.debug(
                f"Attempt {attempt + 1} to call Gemini generate_content for endpoint {api_endpoint}"
            )
            return await gemini_client.aio.models.generate_content(
                model=model,
                contents=contents,
                config=config or {},
            )
        except Exception as e:
            last_exc = e
            attempt += 1
            if attempt >= retries:
                logger.error(
                    f"Gemini generate_content failed after {retries} retries for endpoint {api_endpoint}: {e}",
                    exc_info=True,
                )
                raise last_exc from e
            logger.warning(
                f"Gemini call failed (attempt {attempt}/{retries}) for endpoint {api_endpoint}: {e}. Retrying in {delay}s."
            )
            await asyncio.sleep(delay)
            delay = min(delay * 2, 16.0)

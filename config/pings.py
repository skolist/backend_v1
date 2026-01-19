# pylint: disable=broad-exception-caught
"""
Module Exposes a function to test if all API and SECURE KEYs are work
"""

import time
import functools
import logging

import requests

from openai import OpenAI
from google import genai
from supabase import create_client

logger = logging.getLogger(__name__)


def with_retries(retries: int = 5, initial_delay: float = 1.0):
    """Decorator to retry a function with exponential backoff."""

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            last_exc = None
            for attempt in range(retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exc = e
                    if attempt < retries - 1:
                        logger.warning(
                            "Retry attempt failed",
                            extra={
                                "function_name": func.__name__,
                                "attempt": attempt + 1,
                                "max_retries": retries,
                                "error": str(e),
                                "retry_delay_seconds": delay,
                            },
                        )
                        time.sleep(delay)
                        delay = min(delay * 2, 16.0)
            logger.error(
                "Function failed after all retries",
                extra={
                    "function_name": func.__name__,
                    "max_retries": retries,
                    "final_error": str(last_exc),
                },
            )
            return False

        return wrapper

    return decorator


@with_retries(retries=5)
def check_gemini_api_key(gemini_key):
    """To Check if Gemini Key works"""
    try:
        client = genai.Client(api_key=gemini_key)

        response = client.models.generate_content(
            model="gemini-2.5-flash", contents="Are you working?"
        )
        logger.info(
            "Gemini API key check passed",
            extra={
                "status": "success",
                "response_preview": response.text[:10] if response.text else None,
            },
        )
        return True

    except Exception as e:
        logger.error(
            "Gemini API key check failed",
            extra={
                "status": "failure",
                "error": str(e),
            },
        )
        raise


@with_retries(retries=5)
def check_openai_api_key(openai_key) -> bool:
    """To Check if OPENAI API KEY works"""
    try:
        client = OpenAI(api_key=openai_key)  # picks OPENAI_API_KEY from env

        resp = client.responses.create(model="gpt-4.1-mini", input="Say OK")

        logger.info(
            "OpenAI API key check passed",
            extra={
                "status": "success",
                "response_preview": resp.output_text[:10] if resp.output_text else None,
            },
        )
        return True

    except Exception as e:
        logger.error(
            "OpenAI API key check failed",
            extra={
                "status": "failure",
                "error": str(e),
            },
        )
        raise


@with_retries(retries=5)
def check_supabase_connection(supabase_url, supabase_anon_key) -> bool:
    """To check if SUPABASE_URL and SUPABASE_ANON_KEY works"""
    try:
        headers = {
            "apikey": supabase_anon_key,
            "Authorization": f"Bearer {supabase_anon_key}",
        }

        r = requests.get(f"{supabase_url}/rest/v1/", headers=headers, timeout=5)

        # 401 = key accepted but no resource (EXPECTED)
        if r.status_code in (200, 401, 404):
            logger.info(
                "Supabase connection check passed",
                extra={
                    "status": "success",
                    "http_status_code": r.status_code,
                },
            )
            return True
        raise RuntimeError(f"Unexpected status code: {r.status_code}")

    except Exception as e:
        logger.error(
            "Supabase connection check failed",
            extra={
                "status": "failure",
                "error": str(e),
            },
        )
        raise


@with_retries(retries=5)
def check_supabase_service_key(supabase_url, service_key) -> bool:
    """To check if SUPABASE_SERVICE_KEY works"""
    try:
        supabase = create_client(supabase_url, service_key)

        # Service key must bypass RLS
        # This query should succeed even if RLS is enabled
        supabase.table("users").select("id").limit(1).execute()
        logger.info(
            "Supabase service key check passed",
            extra={
                "status": "success",
            },
        )
        return True

    except Exception as e:
        logger.error(
            "Supabase service key check failed",
            extra={
                "status": "failure",
                "error": str(e),
            },
        )
        raise

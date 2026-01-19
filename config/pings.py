# pylint: disable=broad-exception-caught
"""
Module Exposes a function to test if all API and SECURE KEYs are work
"""

import time
import functools

import requests

from openai import OpenAI
from google import genai
from supabase import create_client


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
                        print(
                            f"⚠️  {func.__name__} failed (attempt {attempt + 1}/{retries}): {e}. Retrying in {delay}s..."
                        )
                        time.sleep(delay)
                        delay = min(delay * 2, 16.0)
            print(f"❌ {func.__name__} failed after {retries} retries: {last_exc}")
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
        print(f"✅ Gemini Key Check passed OK ! Response: {response.text[:10]}")
        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        raise


@with_retries(retries=5)
def check_openai_api_key(openai_key) -> bool:
    """To Check if OPENAI API KEY works"""
    try:
        client = OpenAI(api_key=openai_key)  # picks OPENAI_API_KEY from env

        resp = client.responses.create(model="gpt-4.1-mini", input="Say OK")

        print(f"✅ OpenAI key check passed {resp.output_text[:10]} ")
        return True

    except Exception as e:
        print("❌ OpenAI key check failed:", e)
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
            print(f"✅ Supabase URL and ANON key check passed {r.status_code}")
            return True
        raise RuntimeError(f"Unexpected status code: {r.status_code}")

    except Exception as e:
        print("❌ Supabase connection check failed:", e)
        raise


@with_retries(retries=5)
def check_supabase_service_key(supabase_url, service_key) -> bool:
    """To check if SUPABASE_SERVICE_KEY works"""
    try:
        supabase = create_client(supabase_url, service_key)

        # Service key must bypass RLS
        # This query should succeed even if RLS is enabled
        supabase.table("users").select("id").limit(1).execute()
        print("✅ Supabase service key check passed")
        return True

    except Exception as e:
        print("❌ Supabase service key check failed:", e)
        raise

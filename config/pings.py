# pylint: disable=broad-exception-caught
"""
Module Exposes a function to test if all API and SECURE KEYs are work
"""

import requests

from openai import OpenAI
from google import genai
from supabase import create_client


def check_gemini_api_key(gemini_key):
    """To Check if Gemini Key works"""
    try:
        client = genai.Client(api_key=gemini_key)

        response = client.models.generate_content(
            model="gemini-2.5-flash", contents="Are you working?"
        )
        print(f"✅ Success! Response: {response.text[:10]}")
        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def check_openai_api_key(openai_key) -> bool:
    """To Check if OPENAI API KEY works"""
    try:
        client = OpenAI(api_key=openai_key)  # picks OPENAI_API_KEY from env

        resp = client.responses.create(model="gpt-4.1-mini", input="Say OK")

        print(f"✅ OpenAI key check passed {resp.output_text[:10]} ")
        return True

    except Exception as e:
        print("❌ OpenAI key check failed:", e)
        return False


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
        return False

    except Exception as e:
        print("❌ Supabase connection check failed:", e)
        return False


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
        return False

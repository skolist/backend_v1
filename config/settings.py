"""
Loads configuration from environment variables.
"""

import os
import logging

from dotenv import load_dotenv

from .pings import (
    check_gemini_api_key,
    check_openai_api_key,
    check_supabase_connection,
    check_supabase_service_key,
)

logger = logging.getLogger(__name__)


load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DEPLOYMENT_ENV = os.getenv("DEPLOYMENT_ENV")
LOGGING_LEVEL = os.getenv("LOGGING_LEVEL", "INFO").upper()

logger.info("Configuration loaded. Environment mode: %s", DEPLOYMENT_ENV)

if not SUPABASE_URL:
    logger.warning("SUPABASE_URL is not set.")
if not SUPABASE_SERVICE_KEY:
    logger.warning("SUPABASE_SERVICE_KEY is not set.")
if not GEMINI_API_KEY:
    logger.warning("GEMINI_API_KEY is not set.")
if not OPENAI_API_KEY:
    logger.warning("OPENAI_API_KEY is not set.")
if not DEPLOYMENT_ENV or DEPLOYMENT_ENV not in {"PRODUCTION", "STAGE", "LOCAL"}:
    logger.warning("DEPLOYMENT_ENV is not set. Defaulting to LOCAL.")
    DEPLOYMENT_ENV = "LOCAL"

check_gemini_api_key(GEMINI_API_KEY)
check_openai_api_key(OPENAI_API_KEY)
check_supabase_connection(SUPABASE_URL, SUPABASE_SERVICE_KEY)
check_supabase_service_key(SUPABASE_URL, SUPABASE_SERVICE_KEY)

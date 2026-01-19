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
PING = os.getenv("PING", "FALSE").upper()

logger.info(
    "Configuration loaded",
    extra={
        "deployment_env": DEPLOYMENT_ENV,
        "logging_level": LOGGING_LEVEL,
    },
)

if not SUPABASE_URL:
    logger.warning(
        "Environment variable not set",
        extra={"variable_name": "SUPABASE_URL"},
    )
if not SUPABASE_SERVICE_KEY:
    logger.warning(
        "Environment variable not set",
        extra={"variable_name": "SUPABASE_SERVICE_KEY"},
    )
if not GEMINI_API_KEY:
    logger.warning(
        "Environment variable not set",
        extra={"variable_name": "GEMINI_API_KEY"},
    )
if not OPENAI_API_KEY:
    logger.warning(
        "Environment variable not set",
        extra={"variable_name": "OPENAI_API_KEY"},
    )
if not DEPLOYMENT_ENV or DEPLOYMENT_ENV not in {"PRODUCTION", "STAGE", "LOCAL"}:
    logger.warning(
        "Invalid or missing DEPLOYMENT_ENV, defaulting to LOCAL",
        extra={
            "variable_name": "DEPLOYMENT_ENV",
            "current_value": DEPLOYMENT_ENV,
            "default_value": "LOCAL",
        },
    )
    DEPLOYMENT_ENV = "LOCAL"

if PING == "TRUE":
    check_gemini_api_key(GEMINI_API_KEY)
    check_openai_api_key(OPENAI_API_KEY)
    check_supabase_connection(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    check_supabase_service_key(SUPABASE_URL, SUPABASE_SERVICE_KEY)
else:
    logger.info("Ping Skipped")

"""
Loads configuration from environment variables.
"""

import os
import logging

from dotenv import load_dotenv

logger = logging.getLogger(__name__)


load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PRODUCTION = os.getenv("PRODUCTION", "false").lower() == "true"
LOGGING_LEVEL = os.getenv("LOGGING_LEVEL", "INFO").upper()

logger.info("Configuration loaded. Production mode: %s", PRODUCTION)
if not SUPABASE_URL:
    logger.warning("SUPABASE_URL is not set.")
if not SUPABASE_SERVICE_KEY:
    logger.warning("SUPABASE_SERVICE_KEY is not set.")
if not GEMINI_API_KEY:
    logger.warning("GEMINI_API_KEY is not set.")
if not OPENAI_API_KEY:
    logger.warning("OPENAI_API_KEY is not set.")

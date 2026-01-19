"""
Sets up logging configuration for the application.
Logs are written to both console and a timestamped file in the logs/ directory.
"""

import logging
import os
from datetime import datetime
from pathlib import Path

from .settings import LOGGING_LEVEL

# Create logs directory if it doesn't exist
LOGS_DIR = Path(__file__).parent.parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)

# Generate log filename with datetime when server starts
LOG_FILENAME = datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + ".log"
LOG_FILEPATH = LOGS_DIR / LOG_FILENAME

# Configure root logger
logging.basicConfig(
    level=getattr(logging, LOGGING_LEVEL, logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),  # Console output
        logging.FileHandler(LOG_FILEPATH, mode="a", encoding="utf-8"),  # File output
    ],
)

# Silence noisy third-party loggers
for noisy_logger in [
    "httpcore",
    "httpx",
    "hpack",
    "google_genai",
    "urllib3",
    "asyncio",
]:
    logging.getLogger(noisy_logger).setLevel(logging.WARNING)

logger = logging.getLogger(__name__)
logger.info(f"Logging initialized. Log file: {LOG_FILEPATH}")

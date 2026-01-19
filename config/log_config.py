"""
Sets up logging configuration for the application.
Logs are written to both console and a timestamped file in the logs/ directory.
Console output is colored: DEBUG=white, INFO=green, WARNING=yellow, ERROR=red.
"""

import logging
from datetime import datetime
from pathlib import Path

from .settings import LOGGING_LEVEL

# Create logs directory if it doesn't exist
LOGS_DIR = Path(__file__).parent.parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)

# Generate log filename with datetime when server starts
LOG_FILENAME = datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + ".log"
LOG_FILEPATH = LOGS_DIR / LOG_FILENAME


# ============================================================================
# COLORED CONSOLE FORMATTER
# ============================================================================


class ColoredFormatter(logging.Formatter):
    """
    Custom formatter that adds ANSI color codes to log levels.

    Colors:
        DEBUG: White (default terminal color)
        INFO: Green
        WARNING: Yellow
        ERROR: Red
        CRITICAL: Red + Bold
    """

    # ANSI escape codes for colors
    RESET = "\033[0m"
    WHITE = "\033[37m"  # DEBUG - white
    GREEN = "\033[32m"  # INFO - green
    YELLOW = "\033[33m"  # WARNING - yellow
    RED = "\033[31m"  # ERROR - red
    BOLD_RED = "\033[1;31m"  # CRITICAL - bold red

    LEVEL_COLORS = {
        logging.DEBUG: WHITE,
        logging.INFO: GREEN,
        logging.WARNING: YELLOW,
        logging.ERROR: RED,
        logging.CRITICAL: BOLD_RED,
    }

    def __init__(self, fmt: str, datefmt: str = None):
        super().__init__(fmt, datefmt)

    def format(self, record: logging.LogRecord) -> str:
        # Get color for this level
        color = self.LEVEL_COLORS.get(record.levelno, self.WHITE)

        # Format the record normally first
        formatted = super().format(record)

        # Wrap entire message with color
        return f"{color}{formatted}{self.RESET}"


# ============================================================================
# LOG FORMAT
# ============================================================================

# Format: "DEBUG: 2026-01-19 10:30:45 | message"
LOG_FORMAT = "%(levelname)s: %(asctime)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# File format (no colors, includes module name)
FILE_FORMAT = "%(levelname)s: %(asctime)s | %(name)s | %(message)s"

# Create handlers
console_handler = logging.StreamHandler()
console_handler.setFormatter(ColoredFormatter(LOG_FORMAT, DATE_FORMAT))

file_handler = logging.FileHandler(LOG_FILEPATH, mode="a", encoding="utf-8")
file_handler.setFormatter(logging.Formatter(FILE_FORMAT, DATE_FORMAT))

# Configure root logger
logging.basicConfig(
    level=getattr(logging, LOGGING_LEVEL, logging.INFO),
    handlers=[console_handler, file_handler],
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

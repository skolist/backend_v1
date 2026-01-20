"""
Sets up structured JSON logging configuration for the application.
Logs are written to both console (colored) and a timestamped JSON file in the logs/ directory.

Usage:
    from config.logger import setup_logging
    setup_logging()

    import logging
    logger = logging.getLogger(__name__)
    logger.info("Message", extra={"key": "value"})
"""

import logging
import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from pythonjsonlogger import jsonlogger

load_dotenv()
# ============================================================================
# CONFIGURATION
# ============================================================================

# Get logging level from environment, default to INFO
LOGGING_LEVEL = os.getenv("LOGGING_LEVEL", "INFO").upper()

# Create logs directory if it doesn't exist
LOGS_DIR = Path(__file__).parent.parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)

# Generate log filename with datetime when server starts
LOG_FILENAME = datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + ".json"
LOG_FILEPATH = LOGS_DIR / LOG_FILENAME

# Track if logging has been set up
_logging_configured = False


# ============================================================================
# CUSTOM JSON FORMATTER
# ============================================================================


class StructuredJsonFormatter(jsonlogger.JsonFormatter):
    """
    Custom JSON formatter that adds standard fields to every log entry.

    Output format:
    {
        "timestamp": "2026-01-20T10:30:45.123456",
        "level": "INFO",
        "logger": "module.name",
        "message": "Log message",
        ...extra fields...
    }
    """

    def add_fields(self, log_record, record, message_dict):
        """Add custom fields to the log record."""
        super().add_fields(log_record, record, message_dict)

        # Add standard fields
        log_record["timestamp"] = datetime.utcnow().isoformat()
        log_record["level"] = record.levelname
        log_record["logger"] = record.name

        # Add source location for debugging
        log_record["module"] = record.module
        log_record["function"] = record.funcName
        log_record["line"] = record.lineno

        # Ensure message is present
        if "message" not in log_record:
            log_record["message"] = record.getMessage()


# ============================================================================
# COLORED CONSOLE FORMATTER (for development)
# ============================================================================


class ColoredConsoleFormatter(logging.Formatter):
    """
    Custom formatter that adds ANSI color codes to log levels for console output.

    Colors:
        DEBUG: White (default terminal color)
        INFO: Green
        WARNING: Yellow
        ERROR: Red
        CRITICAL: Red + Bold
    """

    # ANSI escape codes for colors
    RESET = "\033[0m"
    WHITE = "\033[37m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    RED = "\033[31m"
    BOLD_RED = "\033[1;31m"

    LEVEL_COLORS = {
        logging.DEBUG: WHITE,
        logging.INFO: GREEN,
        logging.WARNING: YELLOW,
        logging.ERROR: RED,
        logging.CRITICAL: BOLD_RED,
    }

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record with color and structured extras."""
        color = self.LEVEL_COLORS.get(record.levelno, self.WHITE)

        # Format timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Build base message
        base_msg = f"{record.levelname}: {timestamp} | {record.name} | {record.getMessage()}"

        # Append extra fields if present (excluding standard LogRecord attributes)
        standard_attrs = {
            "name", "msg", "args", "created", "filename", "funcName", "levelname",
            "levelno", "lineno", "module", "msecs", "pathname", "process",
            "processName", "relativeCreated", "stack_info", "exc_info", "exc_text",
            "thread", "threadName", "taskName", "message",
        }

        extra_fields = {
            k: v for k, v in record.__dict__.items()
            if k not in standard_attrs and not k.startswith("_")
        }

        if extra_fields:
            extras_str = " | " + " ".join(f"{k}={v}" for k, v in extra_fields.items())
            base_msg += extras_str

        return f"{color}{base_msg}{self.RESET}"


# ============================================================================
# SETUP FUNCTION
# ============================================================================


def setup_logging() -> None:
    """
    Initialize the global logging configuration.

    Sets up:
    - Colored console handler for development visibility
    - JSON file handler for structured log storage
    - Silences noisy third-party loggers

    This function is idempotent - calling it multiple times has no effect.
    """
    global _logging_configured

    if _logging_configured:
        return

    # Get the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, LOGGING_LEVEL, logging.INFO))

    # Clear any existing handlers
    root_logger.handlers.clear()

    # Console handler with colored output
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(ColoredConsoleFormatter())
    console_handler.setLevel(getattr(logging, LOGGING_LEVEL, logging.INFO))
    root_logger.addHandler(console_handler)

    # File handler with JSON output
    file_handler = logging.FileHandler(LOG_FILEPATH, mode="a", encoding="utf-8")
    json_formatter = StructuredJsonFormatter()
    file_handler.setFormatter(json_formatter)
    file_handler.setLevel(logging.DEBUG)  # Capture all levels to file
    root_logger.addHandler(file_handler)

    # Silence noisy third-party loggers
    noisy_loggers = [
        "httpcore",
        "httpx",
        "hpack",
        "google_genai",
        "urllib3",
        "asyncio",
        "uvicorn.access",
        "openai",
        "openai._base_client",
        "multipart",
        "python_multipart",
    ]
    for noisy_logger in noisy_loggers:
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)

    _logging_configured = True

    # Log initialization
    logger = logging.getLogger(__name__)
    logger.info(
        "Logging initialized",
        extra={
            "log_file": str(LOG_FILEPATH),
            "log_level": LOGGING_LEVEL,
        },
    )


# ============================================================================
# AUTO-INITIALIZATION
# ============================================================================

# Automatically set up logging when this module is imported
setup_logging()

"""
Sets up logging configuration for the application.
"""

import logging

from .settings import LOGGING_LEVEL

logger = logging.getLogger(__name__)
logger.setLevel(LOGGING_LEVEL)

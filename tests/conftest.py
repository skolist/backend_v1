"""
Root conftest for all tests.

Defines shared pytest options and environment loading.

CRITICAL: Environment loading happens at module load time (before pytest_configure)
to ensure test env vars are set BEFORE any app imports occur.
"""

# =============================================================================
# EARLY ENVIRONMENT LOADING - MUST BE BEFORE ANY APP IMPORTS
# =============================================================================
# This runs at import time, before pytest hooks and before any test file imports
# app code. This ensures .env.test values are in os.environ before config/settings.py
# is imported and captures its module-level variables.

import os
from pathlib import Path

from dotenv import load_dotenv

_backend_dir = Path(__file__).parent.parent
_env_test = _backend_dir / ".env.test"
_env_loaded = None

if _env_test.exists():
    # override=True ensures test values take precedence
    load_dotenv(_env_test, override=True)
    _env_loaded = str(_env_test)

# =============================================================================
# STANDARD IMPORTS (safe now that env is loaded)
# =============================================================================

import pytest


def pytest_addoption(parser):
    """Add custom command-line options to pytest."""
    parser.addoption(
        "--gemini-live",
        action="store_true",
        default=False,
        help="Use real Gemini API instead of mocks",
    )


def pytest_configure(config):
    """
    Log which environment file was loaded.

    NOTE: Actual env loading happens at module import time (above).
    This hook just reports what happened.
    """
    if _env_loaded:
        print(f"\n[pytest] Loaded environment from {_env_loaded}")
    else:
        print("\n[pytest] No .env.test found, using system environment")


@pytest.fixture(scope="session")
def use_live_gemini(request):
    """Check if --gemini-live flag was passed."""
    return request.config.getoption("--gemini-live")


@pytest.fixture(scope="session")
def supabase_available():
    """
    Check if Supabase credentials are available.

    Returns True if SUPABASE_URL and SUPABASE_SERVICE_KEY are set.
    Integration tests can use this to skip gracefully.
    """
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY")
    return bool(url and key)


def pytest_collection_modifyitems(config, items):
    """
    Automatically add markers based on test location.

    - tests/unit/* -> @pytest.mark.unit
    - tests/integration/* -> @pytest.mark.integration
    """
    for item in items:
        # Get the test file path relative to tests/
        test_path = str(item.fspath)

        if "/tests/unit/" in test_path:
            item.add_marker(pytest.mark.unit)
        elif "/tests/integration/" in test_path:
            item.add_marker(pytest.mark.integration)

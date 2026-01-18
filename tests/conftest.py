"""
Root conftest for all tests.

Defines shared pytest options.
"""

import pytest


def pytest_addoption(parser):
    """Add --gemini-live option to pytest."""
    parser.addoption(
        "--gemini-live",
        action="store_true",
        default=False,
        help="Use real Gemini API instead of mocks",
    )


@pytest.fixture(scope="session")
def use_live_gemini(request):
    """Check if --gemini-live flag was passed."""
    return request.config.getoption("--gemini-live")

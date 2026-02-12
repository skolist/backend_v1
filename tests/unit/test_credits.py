"""
Unit tests for credits.py using pytest.

Tests the credit checking and deduction functionality.
"""

import uuid
from unittest.mock import MagicMock, patch

import pytest

from api.v1.qgen.credits import check_user_has_credits, deduct_user_credits

# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def user_id():
    """Generate a random user ID for testing."""
    return uuid.uuid4()


@pytest.fixture
def mock_supabase_client():
    """Create a mock Supabase client."""
    return MagicMock()


# ============================================================================
# CHECK CREDITS TESTS
# ============================================================================


class TestCheckUserHasCredits:
    """Tests for check_user_has_credits function."""

    @patch("api.v1.qgen.credits.get_supabase_client")
    def test_returns_true_when_user_has_credits(self, mock_get_client, user_id):
        """Test that check returns True when user has positive credits."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        # Chain for select().eq().single().execute()
        mock_response = MagicMock()
        mock_response.data = {"credits": 1000}
        mock_chain = mock_client.table.return_value.select.return_value
        mock_chain.eq.return_value.single.return_value.execute.return_value = mock_response

        result = check_user_has_credits(user_id)

        assert result is True
        mock_client.table.assert_called_with("users")

    @patch("api.v1.qgen.credits.get_supabase_client")
    def test_returns_false_when_user_has_zero_credits(self, mock_get_client, user_id):
        """Test that check returns False when user has zero credits."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_response = MagicMock()
        mock_response.data = {"credits": 0}
        mock_chain = mock_client.table.return_value.select.return_value
        mock_chain.eq.return_value.single.return_value.execute.return_value = mock_response

        result = check_user_has_credits(user_id)

        assert result is False

    @patch("api.v1.qgen.credits.get_supabase_client")
    def test_returns_false_when_user_has_negative_credits(self, mock_get_client, user_id):
        """Test that check returns False when user has negative credits."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_response = MagicMock()
        mock_response.data = {"credits": -10}
        mock_chain = mock_client.table.return_value.select.return_value
        mock_chain.eq.return_value.single.return_value.execute.return_value = mock_response

        result = check_user_has_credits(user_id)

        assert result is False

    @patch("api.v1.qgen.credits.get_supabase_client")
    def test_returns_true_when_user_has_one_credit(self, mock_get_client, user_id):
        """Test that check returns True when user has exactly 1 credit."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_response = MagicMock()
        mock_response.data = {"credits": 1}
        mock_chain = mock_client.table.return_value.select.return_value
        mock_chain.eq.return_value.single.return_value.execute.return_value = mock_response

        result = check_user_has_credits(user_id)

        assert result is True


# ============================================================================
# DEDUCT CREDITS TESTS
# ============================================================================


class TestDeductUserCredits:
    """Tests for deduct_user_credits function."""

    @patch("api.v1.qgen.credits.get_supabase_client")
    def test_deducts_credits_correctly(self, mock_get_client, user_id):
        """Test that credits are deducted correctly."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        # Mock fetch response with 1000 credits
        mock_fetch_response = MagicMock()
        mock_fetch_response.data = {"credits": 1000}
        mock_chain = mock_client.table.return_value.select.return_value
        mock_chain.eq.return_value.single.return_value.execute.return_value = mock_fetch_response

        deduct_user_credits(user_id, 100)

        # Verify update called with 900 (1000 - 100)
        mock_client.table("users").update.assert_called_with({"credits": 900})

    @patch("api.v1.qgen.credits.get_supabase_client")
    def test_floors_credits_at_zero(self, mock_get_client, user_id):
        """Test that credits cannot go below zero."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        # Mock fetch response with 5 credits
        mock_fetch_response = MagicMock()
        mock_fetch_response.data = {"credits": 5}
        mock_chain = mock_client.table.return_value.select.return_value
        mock_chain.eq.return_value.single.return_value.execute.return_value = mock_fetch_response

        # Deduct more than available
        deduct_user_credits(user_id, 10)

        # Verify update called with 0 (max(0, 5-10))
        mock_client.table("users").update.assert_called_with({"credits": 0})

    @patch("api.v1.qgen.credits.get_supabase_client")
    def test_deducts_exact_amount(self, mock_get_client, user_id):
        """Test that exact amount is deducted."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_fetch_response = MagicMock()
        mock_fetch_response.data = {"credits": 50}
        mock_chain = mock_client.table.return_value.select.return_value
        mock_chain.eq.return_value.single.return_value.execute.return_value = mock_fetch_response

        deduct_user_credits(user_id, 50)

        mock_client.table("users").update.assert_called_with({"credits": 0})

    @patch("api.v1.qgen.credits.get_supabase_client")
    def test_deducts_zero_credits(self, mock_get_client, user_id):
        """Test that deducting zero credits does nothing (optimization)."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        deduct_user_credits(user_id, 0)

        # Should not call get_supabase_client when deducting 0
        mock_get_client.assert_not_called()

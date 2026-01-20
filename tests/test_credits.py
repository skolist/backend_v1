"""
Unit tests for credits.py
"""

import unittest
from unittest.mock import MagicMock, patch
import uuid
import sys
import os

from api.v1.qgen.credits import check_user_has_credits, deduct_user_credits

class TestCreditsValues(unittest.TestCase):
    
    def setUp(self):
        self.user_id = uuid.uuid4()
        
    @patch("api.v1.qgen.credits.get_supabase_client")
    def test_check_user_has_credits_true(self, mock_get_client):
        # Mock setup
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        
        # Chain for select().eq().single().execute()
        mock_table = mock_client.table.return_value
        mock_select = mock_table.select.return_value
        mock_eq = mock_select.eq.return_value
        mock_single = mock_eq.single.return_value
        
        # Mock response with 1000 credits
        mock_response = MagicMock()
        mock_response.data = {"credits": 1000}
        mock_single.execute.return_value = mock_response
        
        # Test
        result = check_user_has_credits(self.user_id)
        
        # Verify
        self.assertTrue(result)
        mock_client.table.assert_called_with("users")
        
    @patch("api.v1.qgen.credits.get_supabase_client")
    def test_check_user_has_credits_false(self, mock_get_client):
        # Mock setup
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        
        # Chain
        mock_response = MagicMock()
        mock_response.data = {"credits": 0}
        
        mock_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_response
        
        # Test
        result = check_user_has_credits(self.user_id)
        self.assertFalse(result)

    @patch("api.v1.qgen.credits.get_supabase_client")
    def test_deduct_user_credits_success(self, mock_get_client):
        # Mock setup
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        
        # Mock Fetch response (1000 credits)
        mock_fetch_response = MagicMock()
        mock_fetch_response.data = {"credits": 1000}
        
        # Chain for fetch
        mock_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_fetch_response
        
        # Chain for update
        mock_update_chain = mock_client.table.return_value.update.return_value.eq.return_value
        
        # Test
        deduct_user_credits(self.user_id, 100)
        
        # Verify update called with 900
        mock_client.table("users").update.assert_called_with({"credits": 900})
        
    @patch("api.v1.qgen.credits.get_supabase_client")
    def test_deduct_user_credits_floor_zero(self, mock_get_client):
        # Mock setup
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        
        # Mock Fetch response (5 credits)
        mock_fetch_response = MagicMock()
        mock_fetch_response.data = {"credits": 5}
        
        # Chain for fetch
        mock_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_fetch_response
        
        # Test deducting 10
        deduct_user_credits(self.user_id, 10)
        
        # Verify update called with 0 (max(0, 5-10))
        mock_client.table("users").update.assert_called_with({"credits": 0})

if __name__ == "__main__":
    unittest.main()

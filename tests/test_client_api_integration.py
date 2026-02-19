"""
Integration tests for StockMon client API communication.

These tests verify the complete API communication workflow including
mocking the requests library to simulate real API responses.
"""

import os
import unittest
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import requests

from client.main import call_api, get_api_url


class TestCallApiIntegration(unittest.TestCase):
    """Integration tests for call_api with realistic scenarios."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.config: Dict[str, Any] = {
            "api_url": "https://stockmon.up.railway.app/check-alerts",
            "silence_hours": 48,
            "tickers": {
                "AAPL": {"buy": 170.0, "sell": 190.0},
                "MSFT": {"buy": 400.0, "sell": 420.0},
            },
        }

    @patch.dict(os.environ, {"API_KEY": "test-api-key-12345"})
    @patch("requests.post")
    def test_call_api_with_alerts_and_errors(self, mock_post: MagicMock) -> None:
        """Test API call that returns both alerts and errors."""
        mock_response: MagicMock = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "alerts": [
                {
                    "ticker": "AAPL",
                    "type": "buy",
                    "threshold": 170.0,
                    "reached": 168.5,
                    "current": 172.3,
                },
                {
                    "ticker": "MSFT",
                    "type": "sell",
                    "threshold": 420.0,
                    "reached": 421.5,
                    "current": 419.8,
                },
            ],
            "errors": [{"ticker": "INVALID", "error": "Ticker not found"}],
            "market_open": True,
            "service_degraded": False,
            "checked_at": "2024-02-06T14:30:00Z",
        }
        mock_post.return_value = mock_response

        response: Dict[str, Any] = call_api(self.config)

        # Verify response structure
        self.assertEqual(len(response["alerts"]), 2)
        self.assertEqual(len(response["errors"]), 1)
        self.assertTrue(response["market_open"])
        self.assertFalse(response["service_degraded"])

        # Verify alert details
        self.assertEqual(response["alerts"][0]["ticker"], "AAPL")
        self.assertEqual(response["alerts"][0]["type"], "buy")
        self.assertEqual(response["alerts"][1]["ticker"], "MSFT")
        self.assertEqual(response["alerts"][1]["type"], "sell")

        # Verify error details
        self.assertEqual(response["errors"][0]["ticker"], "INVALID")

    @patch.dict(os.environ, {"API_KEY": "test-api-key-12345"})
    @patch("requests.post")
    def test_call_api_market_closed(self, mock_post: MagicMock) -> None:
        """Test API call when market is closed."""
        mock_response: MagicMock = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "alerts": [],
            "errors": [],
            "market_open": False,
            "service_degraded": False,
            "checked_at": "2024-02-06T22:30:00Z",
        }
        mock_post.return_value = mock_response

        response: Dict[str, Any] = call_api(self.config)

        self.assertFalse(response["market_open"])
        self.assertEqual(len(response["alerts"]), 0)

    @patch.dict(os.environ, {"API_KEY": "test-api-key-12345"})
    @patch("requests.post")
    def test_call_api_service_degraded(self, mock_post: MagicMock) -> None:
        """Test API call when service is degraded."""
        mock_response: MagicMock = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "alerts": [],
            "errors": [
                {"ticker": "AAPL", "error": "Failed to fetch data from YFinance"},
                {"ticker": "MSFT", "error": "Failed to fetch data from YFinance"},
            ],
            "market_open": True,
            "service_degraded": True,
            "checked_at": "2024-02-06T14:30:00Z",
        }
        mock_post.return_value = mock_response

        response: Dict[str, Any] = call_api(self.config)

        self.assertTrue(response["service_degraded"])
        self.assertEqual(len(response["errors"]), 2)
        self.assertEqual(len(response["alerts"]), 0)

    @patch.dict(
        os.environ,
        {
            "API_KEY": "test-api-key-12345",
            "API_URL": "http://localhost:8000/check-alerts",
        },
    )
    @patch("requests.post")
    def test_call_api_with_url_override(self, mock_post: MagicMock) -> None:
        """Test API call with URL override from environment variable."""
        mock_response: MagicMock = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "alerts": [],
            "errors": [],
            "market_open": True,
            "service_degraded": False,
            "checked_at": "2024-02-06T14:30:00Z",
        }
        mock_post.return_value = mock_response

        response: Dict[str, Any] = call_api(self.config)

        # Verify the overridden URL was used
        call_args = mock_post.call_args
        self.assertEqual(call_args[0][0], "http://localhost:8000/check-alerts")
        self.assertEqual(response["alerts"], [])

    @patch.dict(os.environ, {"API_KEY": "test-api-key-12345"})
    @patch("requests.post")
    def test_call_api_retry_succeeds_after_500_error(
        self, mock_post: MagicMock
    ) -> None:
        """Test that API call succeeds after initial 500 error."""
        # First call returns 500, second call succeeds
        mock_error_response: MagicMock = MagicMock()
        mock_error_response.status_code = 500
        mock_error_response.text = "Internal Server Error"

        mock_success_response: MagicMock = MagicMock()
        mock_success_response.status_code = 200
        mock_success_response.json.return_value = {
            "alerts": [],
            "errors": [],
            "market_open": True,
            "service_degraded": False,
            "checked_at": "2024-02-06T14:30:00Z",
        }

        mock_post.side_effect = [mock_error_response, mock_success_response]

        response: Dict[str, Any] = call_api(self.config)

        # Verify retry occurred
        self.assertEqual(mock_post.call_count, 2)
        self.assertEqual(response["alerts"], [])

    @patch.dict(os.environ, {"API_KEY": "test-api-key-12345"})
    @patch("requests.post")
    def test_call_api_transient_network_error_recovery(
        self, mock_post: MagicMock
    ) -> None:
        """Test recovery from transient network errors."""
        # Simulate connection error on first attempt, success on second
        mock_success_response: MagicMock = MagicMock()
        mock_success_response.status_code = 200
        mock_success_response.json.return_value = {
            "alerts": [
                {
                    "ticker": "AAPL",
                    "type": "buy",
                    "threshold": 170.0,
                    "reached": 168.5,
                    "current": 172.3,
                }
            ],
            "errors": [],
            "market_open": True,
            "service_degraded": False,
            "checked_at": "2024-02-06T14:30:00Z",
        }

        mock_post.side_effect = [
            requests.exceptions.ConnectionError("Network unreachable"),
            mock_success_response,
        ]

        response: Dict[str, Any] = call_api(self.config)

        # Verify retry occurred and succeeded
        self.assertEqual(mock_post.call_count, 2)
        self.assertEqual(len(response["alerts"]), 1)
        self.assertEqual(response["alerts"][0]["ticker"], "AAPL")

    @patch.dict(
        os.environ,
        {"API_KEY": "test-api-key-12345"},
        clear=False,
    )
    @patch("requests.post")
    def test_call_api_full_payload_structure(self, mock_post: MagicMock) -> None:
        """Test that the request payload is correctly structured.

        This test verifies the complete request structure including URL, headers,
        and payload. It respects API_URL environment variable override if present,
        which is the expected behavior during Docker integration tests.
        """
        mock_response: MagicMock = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "alerts": [],
            "errors": [],
            "market_open": True,
            "service_degraded": False,
            "checked_at": "2024-02-06T14:30:00Z",
        }
        mock_post.return_value = mock_response

        call_api(self.config)

        # Verify full request structure
        # Note: get_api_url respects API_URL env var override (used in Docker tests)
        expected_url: str = get_api_url(self.config)
        call_args = mock_post.call_args
        self.assertEqual(call_args[0][0], expected_url)

        # Verify headers
        headers: Dict[str, str] = call_args[1]["headers"]
        self.assertEqual(headers["X-API-Key"], "test-api-key-12345")
        self.assertEqual(headers["Content-Type"], "application/json")

        # Verify payload structure matches config tickers
        payload: Dict[str, Dict[str, float]] = call_args[1]["json"]
        self.assertEqual(len(payload), 2)
        self.assertIn("AAPL", payload)
        self.assertIn("MSFT", payload)
        self.assertEqual(payload["AAPL"]["buy"], 170.0)
        self.assertEqual(payload["AAPL"]["sell"], 190.0)
        self.assertEqual(payload["MSFT"]["buy"], 400.0)
        self.assertEqual(payload["MSFT"]["sell"], 420.0)

        # Verify timeout
        self.assertEqual(call_args[1]["timeout"], 60)


if __name__ == "__main__":
    unittest.main()  # type: ignore[not-callable]

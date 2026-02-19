"""
Unit tests for StockMon client API communication.

These tests verify that the client correctly calls the /check-alerts API endpoint,
handles authentication, retries on failure, and gracefully handles errors.
"""

import os
import unittest
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import requests

from client.main import call_api


class TestCallApi(unittest.TestCase):
    """Test suite for call_api function."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.config: Dict[str, Any] = {
            "api_url": "https://stockmon.up.railway.app/check-alerts",
            "silence_hours": 48,
            "tickers": {
                "AAPL": {"buy": 170.0, "sell": 190.0},
                "MSFT": {"buy": 400.0},
            },
        }
        self.api_key: str = "test-api-key-12345"
        self.success_response: Dict[str, Any] = {
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

    @patch.dict(os.environ, {"API_KEY": "test-api-key-12345"})
    @patch("requests.post")
    def test_call_api_success(self, mock_post: MagicMock) -> None:
        """Test successful API call with valid response."""
        # Mock successful response
        mock_response: MagicMock = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.success_response
        mock_post.return_value = mock_response

        response: Dict[str, Any] = call_api(self.config)

        # Verify API was called correctly
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        self.assertEqual(call_args[0][0], self.config["api_url"])
        self.assertEqual(call_args[1]["headers"]["X-API-Key"], self.api_key)
        self.assertEqual(call_args[1]["timeout"], 60)

        # Verify request payload
        expected_payload: Dict[str, Dict[str, float]] = {
            "AAPL": {"buy": 170.0, "sell": 190.0},
            "MSFT": {"buy": 400.0},
        }
        self.assertEqual(call_args[1]["json"], expected_payload)

        # Verify response
        self.assertEqual(response, self.success_response)
        self.assertEqual(len(response["alerts"]), 1)
        self.assertEqual(response["alerts"][0]["ticker"], "AAPL")

    @patch.dict(os.environ, {"API_KEY": "test-api-key-12345"})
    @patch("requests.post")
    def test_call_api_401_unauthorized(self, mock_post: MagicMock) -> None:
        """Test handling of 401 Unauthorized error."""
        mock_response: MagicMock = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "401 Client Error: Unauthorized"
        )
        mock_post.return_value = mock_response

        with self.assertRaises(requests.exceptions.HTTPError) as context:
            call_api(self.config)

        self.assertIn("401", str(context.exception))
        # Should only make one attempt (no retry on 401)
        self.assertEqual(mock_post.call_count, 1)

    @patch.dict(os.environ, {"API_KEY": "test-api-key-12345"})
    @patch("requests.post")
    def test_call_api_timeout_with_retry(self, mock_post: MagicMock) -> None:
        """Test timeout handling with single retry."""
        # First call times out, second succeeds
        mock_response: MagicMock = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.success_response
        mock_post.side_effect = [requests.exceptions.Timeout(), mock_response]

        response: Dict[str, Any] = call_api(self.config)

        # Should retry once after timeout
        self.assertEqual(mock_post.call_count, 2)
        self.assertEqual(response, self.success_response)

    @patch.dict(os.environ, {"API_KEY": "test-api-key-12345"})
    @patch("requests.post")
    def test_call_api_timeout_exhausts_retries(self, mock_post: MagicMock) -> None:
        """Test timeout handling when all retries are exhausted."""
        # Both attempts time out
        mock_post.side_effect = [
            requests.exceptions.Timeout(),
            requests.exceptions.Timeout(),
        ]

        with self.assertRaises(requests.exceptions.Timeout):
            call_api(self.config)

        # Should make 2 attempts total (initial + 1 retry)
        self.assertEqual(mock_post.call_count, 2)

    @patch.dict(os.environ, {"API_KEY": "test-api-key-12345"})
    @patch("requests.post")
    def test_call_api_connection_error_with_retry(self, mock_post: MagicMock) -> None:
        """Test connection error handling with single retry."""
        # First call fails with connection error, second succeeds
        mock_response: MagicMock = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.success_response
        mock_post.side_effect = [requests.exceptions.ConnectionError(), mock_response]

        response: Dict[str, Any] = call_api(self.config)

        # Should retry once after connection error
        self.assertEqual(mock_post.call_count, 2)
        self.assertEqual(response, self.success_response)

    @patch.dict(os.environ, {"API_KEY": "test-api-key-12345"})
    @patch("requests.post")
    def test_call_api_connection_error_exhausts_retries(
        self, mock_post: MagicMock
    ) -> None:
        """Test connection error handling when all retries are exhausted."""
        # Both attempts fail with connection error
        mock_post.side_effect = [
            requests.exceptions.ConnectionError(),
            requests.exceptions.ConnectionError(),
        ]

        with self.assertRaises(requests.exceptions.ConnectionError):
            call_api(self.config)

        # Should make 2 attempts total (initial + 1 retry)
        self.assertEqual(mock_post.call_count, 2)

    @patch.dict(os.environ, {}, clear=True)
    def test_call_api_missing_api_key(self) -> None:
        """Test error handling when API_KEY environment variable is missing."""
        with self.assertRaises(ValueError) as context:
            call_api(self.config)

        self.assertIn("API_KEY", str(context.exception))

    @patch.dict(os.environ, {"API_KEY": ""})
    def test_call_api_empty_api_key(self) -> None:
        """Test error handling when API_KEY environment variable is empty."""
        with self.assertRaises(ValueError) as context:
            call_api(self.config)

        self.assertIn("API_KEY", str(context.exception))

    @patch.dict(os.environ, {"API_KEY": "test-api-key-12345"})
    @patch("requests.post")
    def test_call_api_500_server_error_with_retry(self, mock_post: MagicMock) -> None:
        """Test handling of 500 server error with retry."""
        # First call returns 500, second succeeds
        mock_error_response: MagicMock = MagicMock()
        mock_error_response.status_code = 500
        mock_error_response.text = "Internal Server Error"

        mock_success_response: MagicMock = MagicMock()
        mock_success_response.status_code = 200
        mock_success_response.json.return_value = self.success_response

        mock_post.side_effect = [mock_error_response, mock_success_response]

        response: Dict[str, Any] = call_api(self.config)

        # Should retry once after 500 error
        self.assertEqual(mock_post.call_count, 2)
        self.assertEqual(response, self.success_response)

    @patch.dict(os.environ, {"API_KEY": "test-api-key-12345"})
    @patch("requests.post")
    def test_call_api_empty_tickers(self, mock_post: MagicMock) -> None:
        """Test API call with empty tickers configuration."""
        empty_config: Dict[str, Any] = {
            "api_url": "https://stockmon.up.railway.app/check-alerts",
            "silence_hours": 48,
            "tickers": {},
        }

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

        response: Dict[str, Any] = call_api(empty_config)

        # Verify empty payload was sent
        call_args = mock_post.call_args
        self.assertEqual(call_args[1]["json"], {})
        self.assertEqual(response["alerts"], [])

    @patch.dict(os.environ, {"API_KEY": "test-api-key-12345"})
    @patch("requests.post")
    def test_call_api_request_exception_no_retry(self, mock_post: MagicMock) -> None:
        """Test that RequestException (non-retryable) is not retried."""
        # Generic RequestException should not be retried (only specific ones)
        mock_post.side_effect = requests.exceptions.RequestException("Generic error")

        with self.assertRaises(requests.exceptions.RequestException):
            call_api(self.config)

        # Should only make one attempt (no retry for generic errors)
        self.assertEqual(mock_post.call_count, 1)

    @patch.dict(os.environ, {"API_KEY": "test-api-key-12345"})
    @patch("requests.post")
    def test_call_api_none_status_code(self, mock_post: MagicMock) -> None:
        """Test that None status_code raises RuntimeError."""
        # Create a mock response with status_code set to None
        mock_response: MagicMock = MagicMock()
        mock_response.status_code = None
        mock_post.return_value = mock_response

        with self.assertRaises(RuntimeError) as context:
            call_api(self.config)

        # Verify the error message
        self.assertIn("no status code", str(context.exception).lower())

        # Should only make one attempt (not a retryable error)
        self.assertEqual(mock_post.call_count, 1)


if __name__ == "__main__":
    unittest.main()  # type: ignore[not-callable]

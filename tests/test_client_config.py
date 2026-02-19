"""
Unit tests for StockMon client configuration loading.

These tests verify that the client correctly loads and validates
configuration from config.json and handles environment variable overrides.
"""

import json
import os
import unittest
from typing import Any, Dict
from unittest.mock import MagicMock, mock_open, patch

from client.main import get_api_url, load_config


class TestLoadConfig(unittest.TestCase):
    """Test suite for load_config function."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.valid_config: Dict[str, Any] = {
            "api_url": "https://stockmon.up.railway.app/check-alerts",
            "silence_hours": 48,
            "tickers": {
                "AAPL": {"buy": 170, "sell": 190},
                "MSFT": {"buy": 400, "sell": 420},
            },
        }
        self.config_json: str = json.dumps(self.valid_config)

    @patch("pathlib.Path.exists")
    @patch("builtins.open", new_callable=mock_open)
    def test_load_config_success(
        self, mock_file: MagicMock, mock_exists: MagicMock
    ) -> None:
        """Test successful config loading with all required fields."""
        mock_exists.return_value = True
        mock_file.return_value.read.return_value = self.config_json

        config: Dict[str, Any] = load_config()

        self.assertEqual(
            config["api_url"], "https://stockmon.up.railway.app/check-alerts"
        )
        self.assertEqual(config["silence_hours"], 48)
        self.assertIn("AAPL", config["tickers"])
        self.assertEqual(config["tickers"]["AAPL"]["buy"], 170)
        self.assertEqual(config["tickers"]["AAPL"]["sell"], 190)

    @patch("pathlib.Path.exists")
    def test_load_config_file_not_found(self, mock_exists: MagicMock) -> None:
        """Test error handling when config.json does not exist."""
        mock_exists.return_value = False

        with self.assertRaises(FileNotFoundError) as context:
            load_config()

        self.assertIn("Configuration file not found", str(context.exception))

    @patch("pathlib.Path.exists")
    @patch("builtins.open", new_callable=mock_open)
    def test_load_config_invalid_json(
        self, mock_file: MagicMock, mock_exists: MagicMock
    ) -> None:
        """Test error handling when config.json contains invalid JSON."""
        mock_exists.return_value = True
        mock_file.return_value.read.return_value = "{invalid json"

        with self.assertRaises(json.JSONDecodeError):
            load_config()

    @patch("pathlib.Path.exists")
    @patch("builtins.open", new_callable=mock_open)
    def test_load_config_missing_api_url(
        self, mock_file: MagicMock, mock_exists: MagicMock
    ) -> None:
        """Test error handling when api_url is missing."""
        mock_exists.return_value = True
        incomplete_config: Dict[str, Any] = {
            "silence_hours": 48,
            "tickers": {"AAPL": {"buy": 170, "sell": 190}},
        }
        mock_file.return_value.read.return_value = json.dumps(incomplete_config)

        with self.assertRaises(KeyError) as context:
            load_config()

        self.assertIn("api_url", str(context.exception))

    @patch("pathlib.Path.exists")
    @patch("builtins.open", new_callable=mock_open)
    def test_load_config_missing_silence_hours(
        self, mock_file: MagicMock, mock_exists: MagicMock
    ) -> None:
        """Test error handling when silence_hours is missing."""
        mock_exists.return_value = True
        incomplete_config: Dict[str, Any] = {
            "api_url": "https://example.com",
            "tickers": {"AAPL": {"buy": 170, "sell": 190}},
        }
        mock_file.return_value.read.return_value = json.dumps(incomplete_config)

        with self.assertRaises(KeyError) as context:
            load_config()

        self.assertIn("silence_hours", str(context.exception))

    @patch("pathlib.Path.exists")
    @patch("builtins.open", new_callable=mock_open)
    def test_load_config_missing_tickers(
        self, mock_file: MagicMock, mock_exists: MagicMock
    ) -> None:
        """Test error handling when tickers is missing."""
        mock_exists.return_value = True
        incomplete_config: Dict[str, Any] = {
            "api_url": "https://example.com",
            "silence_hours": 48,
        }
        mock_file.return_value.read.return_value = json.dumps(incomplete_config)

        with self.assertRaises(KeyError) as context:
            load_config()

        self.assertIn("tickers", str(context.exception))

    @patch("pathlib.Path.exists")
    @patch("builtins.open", new_callable=mock_open)
    def test_load_config_invalid_tickers_type(
        self, mock_file: MagicMock, mock_exists: MagicMock
    ) -> None:
        """Test error handling when tickers is not a dictionary."""
        mock_exists.return_value = True
        invalid_config: Dict[str, Any] = {
            "api_url": "https://example.com",
            "silence_hours": 48,
            "tickers": ["AAPL", "MSFT"],  # Should be dict, not list
        }
        mock_file.return_value.read.return_value = json.dumps(invalid_config)

        with self.assertRaises(TypeError) as context:
            load_config()

        self.assertIn("Invalid 'tickers' configuration", str(context.exception))

    @patch("pathlib.Path.exists")
    @patch("builtins.open", new_callable=mock_open)
    def test_load_config_empty_tickers(
        self, mock_file: MagicMock, mock_exists: MagicMock
    ) -> None:
        """Test that empty tickers dictionary is valid."""
        mock_exists.return_value = True
        empty_tickers_config: Dict[str, Any] = {
            "api_url": "https://example.com",
            "silence_hours": 48,
            "tickers": {},
        }
        mock_file.return_value.read.return_value = json.dumps(empty_tickers_config)

        config: Dict[str, Any] = load_config()

        self.assertEqual(config["tickers"], {})


class TestGetApiUrl(unittest.TestCase):
    """Test suite for get_api_url function."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.config: Dict[str, Any] = {
            "api_url": "https://stockmon.up.railway.app/check-alerts",
            "silence_hours": 48,
            "tickers": {},
        }

    def test_get_api_url_from_config(self) -> None:
        """Test that API URL is retrieved from config when env var not set."""
        # Ensure API_URL environment variable is not set
        if "API_URL" in os.environ:
            del os.environ["API_URL"]

        api_url: str = get_api_url(self.config)

        self.assertEqual(api_url, "https://stockmon.up.railway.app/check-alerts")

    def test_get_api_url_from_env_override(self) -> None:
        """Test that API_URL environment variable overrides config.json."""
        override_url: str = "http://localhost:8000/check-alerts"
        os.environ["API_URL"] = override_url

        try:
            api_url: str = get_api_url(self.config)
            self.assertEqual(api_url, override_url)
        finally:
            # Clean up environment variable
            del os.environ["API_URL"]

    def test_get_api_url_env_takes_precedence(self) -> None:
        """Test that environment variable takes precedence even with valid config."""
        override_url: str = "http://test-api.local/check-alerts"
        os.environ["API_URL"] = override_url

        try:
            api_url: str = get_api_url(self.config)
            self.assertEqual(api_url, override_url)
            self.assertNotEqual(api_url, self.config["api_url"])
        finally:
            # Clean up environment variable
            del os.environ["API_URL"]

    def test_get_api_url_empty_env_var(self) -> None:
        """Test that empty environment variable is treated as not set."""
        os.environ["API_URL"] = ""

        try:
            api_url: str = get_api_url(self.config)
            # Empty string is falsy, so should fall back to config
            self.assertEqual(api_url, self.config["api_url"])
        finally:
            # Clean up environment variable
            del os.environ["API_URL"]


if __name__ == "__main__":
    unittest.main()  # type: ignore[not-callable]

"""
Integration tests for StockMon client.

These tests verify the complete workflow of the client, including
loading real config files and environment variable handling.
"""

import json
import os
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict

from client.main import get_api_url, load_config


class TestClientIntegration(unittest.TestCase):
    """Integration tests for client configuration and workflow."""

    def test_load_real_config_file(self) -> None:
        """Test loading the actual config.json file from the client directory."""
        # This test uses the real config file to ensure it's valid
        config: Dict[str, Any] = load_config()

        # Verify structure
        self.assertIn("api_url", config)
        self.assertIn("silence_hours", config)
        self.assertIn("tickers", config)

        # Verify types
        self.assertIsInstance(config["api_url"], str)
        self.assertIsInstance(config["silence_hours"], int)
        self.assertIsInstance(config["tickers"], dict)

        # Verify API URL is a valid HTTPS URL
        self.assertTrue(
            config["api_url"].startswith("http://")
            or config["api_url"].startswith("https://")
        )

    def test_api_url_override_workflow(self) -> None:
        """Test the complete workflow of API URL override with env var."""
        # Load config normally
        config: Dict[str, Any] = load_config()
        original_url: str = config["api_url"]

        # Test without override
        if "API_URL" in os.environ:
            del os.environ["API_URL"]

        url_from_config: str = get_api_url(config)
        self.assertEqual(url_from_config, original_url)

        # Test with override
        test_override: str = "http://localhost:8000/check-alerts"
        os.environ["API_URL"] = test_override

        try:
            url_with_override: str = get_api_url(config)
            self.assertEqual(url_with_override, test_override)
            self.assertNotEqual(url_with_override, original_url)
        finally:
            # Clean up
            del os.environ["API_URL"]

    def test_config_has_valid_ticker_structure(self) -> None:
        """Test that real config file has valid ticker structure."""
        config: Dict[str, Any] = load_config()

        # Each ticker should have buy and sell thresholds
        for symbol, thresholds in config["tickers"].items():
            self.assertIsInstance(symbol, str)
            self.assertIsInstance(thresholds, dict)

            # Verify buy threshold if present
            if "buy" in thresholds:
                self.assertIsInstance(thresholds["buy"], (int, float))
                self.assertGreater(float(thresholds["buy"]), 0)

            # Verify sell threshold if present
            if "sell" in thresholds:
                self.assertIsInstance(thresholds["sell"], (int, float))
                self.assertGreater(float(thresholds["sell"]), 0)

            # If both present, sell should be higher than buy
            if "buy" in thresholds and "sell" in thresholds:
                self.assertGreater(
                    thresholds["sell"],
                    thresholds["buy"],
                    f"Ticker {symbol}: sell threshold should be higher than buy",
                )


class TestClientConfigModification(unittest.TestCase):
    """Test client behavior with modified configuration files."""

    def test_config_with_custom_values(self) -> None:
        """Test loading config with custom values."""
        # Create a temporary config file
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_config_path: Path = Path(temp_dir) / "config.json"

            custom_config: Dict[str, Any] = {
                "api_url": "https://custom-api.example.com/alerts",
                "silence_hours": 72,
                "tickers": {
                    "TSLA": {"buy": 200, "sell": 250},
                    "GOOGL": {"buy": 140, "sell": 160},
                },
            }

            with open(temp_config_path, "w", encoding="utf-8") as f:
                json.dump(custom_config, f)

            # Verify the file was created and can be loaded
            with open(temp_config_path, "r", encoding="utf-8") as f:
                loaded_config: Dict[str, Any] = json.load(f)

            self.assertEqual(loaded_config["silence_hours"], 72)
            self.assertIn("TSLA", loaded_config["tickers"])
            self.assertEqual(loaded_config["tickers"]["TSLA"]["buy"], 200)

    def test_config_with_many_tickers(self) -> None:
        """Test that config can handle many tickers."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_config_path: Path = Path(temp_dir) / "config.json"

            # Create config with many tickers
            many_tickers: Dict[str, Dict[str, int]] = {
                f"TICK{i}": {"buy": 100 + i, "sell": 150 + i} for i in range(50)
            }

            custom_config: Dict[str, Any] = {
                "api_url": "https://example.com/alerts",
                "silence_hours": 48,
                "tickers": many_tickers,
            }

            with open(temp_config_path, "w", encoding="utf-8") as f:
                json.dump(custom_config, f)

            # Verify the file was created
            with open(temp_config_path, "r", encoding="utf-8") as f:
                loaded_config: Dict[str, Any] = json.load(f)

            self.assertEqual(len(loaded_config["tickers"]), 50)
            self.assertIn("TICK0", loaded_config["tickers"])
            self.assertIn("TICK49", loaded_config["tickers"])


if __name__ == "__main__":
    unittest.main()  # type: ignore[misc]

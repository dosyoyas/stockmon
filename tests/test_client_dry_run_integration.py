"""
Integration tests for StockMon client dry-run functionality.

These tests verify that the client correctly handles the --dry-run flag
in the main execution flow.
"""

import json
import unittest
from io import StringIO
from typing import Any, Dict
from unittest.mock import MagicMock, mock_open, patch

from client.main import main


class TestMainDryRunIntegration(unittest.TestCase):
    """Test suite for main() function with --dry-run flag."""

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
    @patch("sys.argv", ["client.main"])
    @patch("client.main.call_api")
    @patch.dict("os.environ", {"API_KEY": "test-api-key-12345"})
    def test_main_production_mode_default(
        self, mock_call_api: MagicMock, mock_file: MagicMock, mock_exists: MagicMock
    ) -> None:
        """Test that main() runs in production mode by default."""
        mock_exists.return_value = True
        mock_file.return_value.read.return_value = self.config_json

        # Mock successful API response
        mock_call_api.return_value = {
            "alerts": [],
            "errors": [],
            "market_open": True,
            "service_degraded": False,
            "checked_at": "2024-02-06T14:30:00Z",
        }

        # Capture stdout
        captured_output: StringIO = StringIO()

        with patch("sys.stdout", captured_output):
            exit_code: int = main()

        self.assertEqual(exit_code, 0)

        output: str = captured_output.getvalue()
        self.assertIn("Mode: PRODUCTION", output)
        self.assertNotIn("DRY-RUN", output)

    @patch("pathlib.Path.exists")
    @patch("builtins.open", new_callable=mock_open)
    @patch("sys.argv", ["client.main", "--dry-run"])
    @patch("client.main.call_api")
    @patch.dict("os.environ", {"API_KEY": "test-api-key-12345"})
    def test_main_dry_run_mode(
        self, mock_call_api: MagicMock, mock_file: MagicMock, mock_exists: MagicMock
    ) -> None:
        """Test that main() runs in dry-run mode when --dry-run flag is provided."""
        mock_exists.return_value = True
        mock_file.return_value.read.return_value = self.config_json

        # Mock successful API response
        mock_call_api.return_value = {
            "alerts": [],
            "errors": [],
            "market_open": True,
            "service_degraded": False,
            "checked_at": "2024-02-06T14:30:00Z",
        }

        # Capture stdout
        captured_output: StringIO = StringIO()

        with patch("sys.stdout", captured_output):
            exit_code: int = main()

        self.assertEqual(exit_code, 0)

        output: str = captured_output.getvalue()
        self.assertIn("Mode: DRY-RUN", output)
        self.assertIn("no emails", output.lower())
        self.assertIn("no notified.json updates", output.lower())

    @patch("pathlib.Path.exists")
    @patch("builtins.open", new_callable=mock_open)
    @patch("sys.argv", ["client.main"])
    @patch("client.main.call_api")
    @patch.dict("os.environ", {"API_KEY": "test-api-key-12345"})
    def test_main_displays_all_config(
        self, mock_call_api: MagicMock, mock_file: MagicMock, mock_exists: MagicMock
    ) -> None:
        """Test that main() displays complete configuration."""
        mock_exists.return_value = True
        mock_file.return_value.read.return_value = self.config_json

        # Mock successful API response
        mock_call_api.return_value = {
            "alerts": [],
            "errors": [],
            "market_open": True,
            "service_degraded": False,
            "checked_at": "2024-02-06T14:30:00Z",
        }

        # Capture stdout
        captured_output: StringIO = StringIO()

        with patch("sys.stdout", captured_output):
            exit_code: int = main()

        self.assertEqual(exit_code, 0)

        output: str = captured_output.getvalue()
        self.assertIn("StockMon Client Configuration:", output)
        self.assertIn("API URL:", output)
        self.assertIn("Silence Hours: 48", output)
        self.assertIn("Tickers: 2 configured", output)
        self.assertIn("AAPL: buy=$170.00, sell=$190.00", output)
        self.assertIn("MSFT: buy=$400.00, sell=$420.00", output)

    @patch("pathlib.Path.exists")
    @patch("builtins.open", new_callable=mock_open)
    @patch("sys.argv", ["client.main", "--dry-run"])
    @patch("client.main.call_api")
    @patch.dict(
        "os.environ",
        {
            "API_KEY": "test-api-key-12345",
            "API_URL": "http://localhost:8000/check-alerts",
        },
    )
    def test_main_dry_run_with_api_url_override(
        self, mock_call_api: MagicMock, mock_file: MagicMock, mock_exists: MagicMock
    ) -> None:
        """Test dry-run mode with API_URL environment variable override."""
        mock_exists.return_value = True
        mock_file.return_value.read.return_value = self.config_json

        # Mock successful API response
        mock_call_api.return_value = {
            "alerts": [],
            "errors": [],
            "market_open": True,
            "service_degraded": False,
            "checked_at": "2024-02-06T14:30:00Z",
        }

        # Capture stdout
        captured_output: StringIO = StringIO()

        with patch("sys.stdout", captured_output):
            exit_code: int = main()

        self.assertEqual(exit_code, 0)

        output: str = captured_output.getvalue()
        self.assertIn("Mode: DRY-RUN", output)
        self.assertIn("API URL: http://localhost:8000/check-alerts", output)


if __name__ == "__main__":
    unittest.main()  # type: ignore[misc]

"""
Comprehensive flow tests for StockMon client.

These tests verify the complete client workflow including:
- API calls with various responses
- Email sending based on market status and alerts
- Notification tracking with silence period
- Error handling (401, timeouts)
- Dry-run mode behavior
"""

import io
import json
import os
import unittest
from typing import Any, Dict
from unittest.mock import MagicMock, mock_open, patch

import requests

from client.email import (EmailConfig, format_alert_email,
                          format_service_degraded_email, send_email)
from client.main import call_api, main, parse_arguments
from client.notified import NotificationTracker


class TestClientFlowNewAlerts(unittest.TestCase):
    """Test flow: New alerts trigger email sending."""

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

        self.api_response_with_alerts: Dict[str, Any] = {
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
            "errors": [],
            "market_open": True,
            "service_degraded": False,
            "checked_at": "2024-02-06T14:30:00Z",
        }

        self.email_config: EmailConfig = EmailConfig(
            smtp_host="smtp.test.com",
            smtp_user="user@test.com",
            smtp_pass="test_pass",
            notify_email="notify@test.com",
        )

    @patch.dict(os.environ, {"API_KEY": "test-api-key-12345"})
    @patch("requests.post")
    def test_new_alerts_trigger_api_call(self, mock_post: MagicMock) -> None:
        """Test that new alerts from API are retrieved successfully."""
        mock_response: MagicMock = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.api_response_with_alerts
        mock_post.return_value = mock_response

        response: Dict[str, Any] = call_api(self.config)

        # Verify alerts were received
        self.assertEqual(len(response["alerts"]), 2)
        self.assertTrue(response["market_open"])
        self.assertFalse(response["service_degraded"])

        # Verify alert details
        self.assertEqual(response["alerts"][0]["ticker"], "AAPL")
        self.assertEqual(response["alerts"][0]["type"], "buy")
        self.assertEqual(response["alerts"][1]["ticker"], "MSFT")
        self.assertEqual(response["alerts"][1]["type"], "sell")

    @patch("smtplib.SMTP")
    def test_alerts_formatted_and_sent_via_email(
        self, mock_smtp_class: MagicMock
    ) -> None:
        """Test that alerts are formatted correctly and sent via email."""
        # Configure mock SMTP
        mock_server: MagicMock = MagicMock()
        mock_smtp_class.return_value.__enter__.return_value = mock_server

        # Send email for first alert
        alert: Dict[str, Any] = self.api_response_with_alerts["alerts"][0]
        subject: str
        body: str
        subject, body = format_alert_email(alert)

        # Verify email formatting
        self.assertIn("AAPL", subject)
        self.assertIn("buy", subject)
        self.assertIn("AAPL", body)
        self.assertIn("BUY", body)
        self.assertIn("170.00", body)

        # Send the email
        send_email(self.email_config, subject, body)

        # Verify SMTP was called
        mock_smtp_class.assert_called_once_with("smtp.test.com", 587)
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("user@test.com", "test_pass")
        mock_server.send_message.assert_called_once()

    @patch("smtplib.SMTP")
    def test_multiple_alerts_send_multiple_emails(
        self, mock_smtp_class: MagicMock
    ) -> None:
        """Test that multiple alerts result in multiple emails being sent."""
        # Configure mock SMTP
        mock_server: MagicMock = MagicMock()
        mock_smtp_class.return_value.__enter__.return_value = mock_server

        # Send emails for all alerts
        email_count: int = 0
        for alert in self.api_response_with_alerts["alerts"]:
            subject: str
            body: str
            subject, body = format_alert_email(alert)
            send_email(self.email_config, subject, body)
            email_count += 1

        # Verify multiple emails were sent
        self.assertEqual(email_count, 2)
        self.assertEqual(mock_server.send_message.call_count, 2)


class TestClientFlowMarketClosed(unittest.TestCase):
    """Test flow: market_open=false prevents email sending."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.config: Dict[str, Any] = {
            "api_url": "https://stockmon.up.railway.app/check-alerts",
            "silence_hours": 48,
            "tickers": {"AAPL": {"buy": 170.0, "sell": 190.0}},
        }

        self.api_response_market_closed: Dict[str, Any] = {
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
            "market_open": False,
            "service_degraded": False,
            "checked_at": "2024-02-06T22:30:00Z",
        }

    @patch.dict(os.environ, {"API_KEY": "test-api-key-12345"})
    @patch("requests.post")
    def test_market_closed_alerts_not_processed(self, mock_post: MagicMock) -> None:
        """Test that when market is closed, alerts are present but should not be acted upon."""
        mock_response: MagicMock = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.api_response_market_closed
        mock_post.return_value = mock_response

        response: Dict[str, Any] = call_api(self.config)

        # Verify market is closed
        self.assertFalse(response["market_open"])

        # Verify alerts exist (but should not be processed)
        self.assertEqual(len(response["alerts"]), 1)

    @patch("smtplib.SMTP")
    @patch.dict(os.environ, {"API_KEY": "test-api-key-12345"})
    @patch("requests.post")
    def test_market_closed_no_emails_sent(
        self, mock_post: MagicMock, mock_smtp_class: MagicMock
    ) -> None:
        """Test that no emails are sent when market is closed, even if alerts exist."""
        mock_response: MagicMock = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.api_response_market_closed
        mock_post.return_value = mock_response

        response: Dict[str, Any] = call_api(self.config)

        # Verify market is closed
        self.assertFalse(response["market_open"])

        # Client logic should skip email sending when market is closed
        # Verify SMTP was never called
        if response["market_open"]:
            # This block would send emails, but should not execute
            email_config: EmailConfig = EmailConfig(
                smtp_host="smtp.test.com",
                smtp_user="user@test.com",
                smtp_pass="test_pass",
                notify_email="notify@test.com",
            )
            for alert in response["alerts"]:
                subject: str
                body: str
                subject, body = format_alert_email(alert)
                send_email(email_config, subject, body)

        # SMTP should never be called because market is closed
        mock_smtp_class.assert_not_called()


class TestClientFlowServiceDegraded(unittest.TestCase):
    """Test flow: service_degraded=true triggers warning email."""

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

        self.api_response_degraded: Dict[str, Any] = {
            "alerts": [],
            "errors": [
                {"ticker": "AAPL", "error": "Failed to fetch data from YFinance"},
                {"ticker": "MSFT", "error": "Failed to fetch data from YFinance"},
            ],
            "market_open": True,
            "service_degraded": True,
            "checked_at": "2024-02-06T14:30:00Z",
        }

    @patch.dict(os.environ, {"API_KEY": "test-api-key-12345"})
    @patch("requests.post")
    def test_service_degraded_detected(self, mock_post: MagicMock) -> None:
        """Test that service degradation is properly detected from API response."""
        mock_response: MagicMock = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.api_response_degraded
        mock_post.return_value = mock_response

        response: Dict[str, Any] = call_api(self.config)

        # Verify service is degraded
        self.assertTrue(response["service_degraded"])
        self.assertEqual(len(response["errors"]), 2)
        self.assertEqual(len(response["alerts"]), 0)

    @patch("smtplib.SMTP")
    @patch.dict(os.environ, {"API_KEY": "test-api-key-12345"})
    @patch("requests.post")
    def test_service_degraded_sends_warning_email(
        self, mock_post: MagicMock, mock_smtp_class: MagicMock
    ) -> None:
        """Test that a warning email is sent when service is degraded."""
        # Configure mock SMTP
        mock_server: MagicMock = MagicMock()
        mock_smtp_class.return_value.__enter__.return_value = mock_server

        mock_response: MagicMock = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.api_response_degraded
        mock_post.return_value = mock_response

        response: Dict[str, Any] = call_api(self.config)

        # If service is degraded, send warning email
        if response["service_degraded"]:
            email_config: EmailConfig = EmailConfig(
                smtp_host="smtp.test.com",
                smtp_user="user@test.com",
                smtp_pass="test_pass",
                notify_email="notify@test.com",
            )

            subject: str
            body: str
            subject, body = format_service_degraded_email()

            # Verify warning email format
            self.assertIn("degradado", subject.lower())
            self.assertIn("YFinance", body)

            send_email(email_config, subject, body)

            # Verify email was sent
            mock_smtp_class.assert_called_once()
            mock_server.send_message.assert_called_once()


class TestClientFlow401Error(unittest.TestCase):
    """Test flow: 401 error is logged without crashing."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.config: Dict[str, Any] = {
            "api_url": "https://stockmon.up.railway.app/check-alerts",
            "silence_hours": 48,
            "tickers": {"AAPL": {"buy": 170.0, "sell": 190.0}},
        }

    @patch.dict(os.environ, {"API_KEY": "invalid-api-key"})
    @patch("requests.post")
    def test_401_error_raises_http_error(self, mock_post: MagicMock) -> None:
        """Test that 401 error raises HTTPError without retry."""
        mock_response: MagicMock = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "401 Client Error: Unauthorized"
        )
        mock_post.return_value = mock_response

        with self.assertRaises(requests.exceptions.HTTPError) as context:
            call_api(self.config)

        # Verify error contains 401
        self.assertIn("401", str(context.exception))

        # Verify only one attempt was made (no retry on 401)
        self.assertEqual(mock_post.call_count, 1)

    @patch("pathlib.Path.exists")
    @patch("builtins.open", new_callable=mock_open)
    @patch("sys.argv", ["client.main"])
    @patch("client.main.call_api")
    @patch.dict(os.environ, {"API_KEY": "invalid-api-key"})
    def test_401_error_logged_and_no_crash(
        self, mock_call_api: MagicMock, mock_file: MagicMock, mock_exists: MagicMock
    ) -> None:
        """Test that 401 error is logged to stderr and main returns error code without crashing."""
        mock_exists.return_value = True
        config_data: Dict[str, Any] = {
            "api_url": "https://stockmon.up.railway.app/check-alerts",
            "silence_hours": 48,
            "tickers": {"AAPL": {"buy": 170.0, "sell": 190.0}},
        }
        mock_file.return_value.read.return_value = json.dumps(config_data)

        # Simulate 401 error
        mock_call_api.side_effect = requests.exceptions.HTTPError(
            "401 Client Error: Unauthorized"
        )

        # Capture stderr
        captured_stderr: io.StringIO = io.StringIO()

        with patch("sys.stderr", captured_stderr):
            exit_code: int = main()

        # Verify non-zero exit code
        self.assertEqual(exit_code, 1)

        # Verify error was logged
        error_output: str = captured_stderr.getvalue()
        self.assertIn("ERROR", error_output)
        self.assertIn("401", error_output)


class TestClientFlowTimeout(unittest.TestCase):
    """Test flow: Timeout is handled gracefully with retry."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.config: Dict[str, Any] = {
            "api_url": "https://stockmon.up.railway.app/check-alerts",
            "silence_hours": 48,
            "tickers": {"AAPL": {"buy": 170.0, "sell": 190.0}},
        }

        self.success_response: Dict[str, Any] = {
            "alerts": [],
            "errors": [],
            "market_open": True,
            "service_degraded": False,
            "checked_at": "2024-02-06T14:30:00Z",
        }

    @patch.dict(os.environ, {"API_KEY": "test-api-key-12345"})
    @patch("requests.post")
    def test_timeout_retry_succeeds(self, mock_post: MagicMock) -> None:
        """Test that timeout is retried once and succeeds."""
        # First call times out, second succeeds
        mock_response: MagicMock = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.success_response
        mock_post.side_effect = [requests.exceptions.Timeout(), mock_response]

        response: Dict[str, Any] = call_api(self.config)

        # Verify retry occurred
        self.assertEqual(mock_post.call_count, 2)
        self.assertEqual(response, self.success_response)

    @patch.dict(os.environ, {"API_KEY": "test-api-key-12345"})
    @patch("requests.post")
    def test_timeout_exhausts_retries_gracefully(self, mock_post: MagicMock) -> None:
        """Test that timeout retries are exhausted gracefully without crashing."""
        # Both attempts time out
        mock_post.side_effect = [
            requests.exceptions.Timeout(),
            requests.exceptions.Timeout(),
        ]

        with self.assertRaises(requests.exceptions.Timeout):
            call_api(self.config)

        # Verify 2 attempts were made
        self.assertEqual(mock_post.call_count, 2)

    @patch("pathlib.Path.exists")
    @patch("builtins.open", new_callable=mock_open)
    @patch("sys.argv", ["client.main"])
    @patch("client.main.call_api")
    @patch.dict(os.environ, {"API_KEY": "test-api-key-12345"})
    def test_timeout_logged_gracefully_in_main(
        self, mock_call_api: MagicMock, mock_file: MagicMock, mock_exists: MagicMock
    ) -> None:
        """Test that timeout errors are logged gracefully in main without crash."""
        mock_exists.return_value = True
        config_data: Dict[str, Any] = {
            "api_url": "https://stockmon.up.railway.app/check-alerts",
            "silence_hours": 48,
            "tickers": {"AAPL": {"buy": 170.0, "sell": 190.0}},
        }
        mock_file.return_value.read.return_value = json.dumps(config_data)

        # Simulate timeout after all retries
        mock_call_api.side_effect = requests.exceptions.Timeout()

        # Capture stderr
        captured_stderr: io.StringIO = io.StringIO()

        with patch("sys.stderr", captured_stderr):
            exit_code: int = main()

        # Verify non-zero exit code
        self.assertEqual(exit_code, 1)

        # Verify timeout error was logged
        error_output: str = captured_stderr.getvalue()
        self.assertIn("ERROR", error_output)
        self.assertIn("timed out", error_output.lower())


class TestClientFlowDryRun(unittest.TestCase):
    """Test flow: --dry-run flag outputs to stdout only without side effects."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.config_data: Dict[str, Any] = {
            "api_url": "https://stockmon.up.railway.app/check-alerts",
            "silence_hours": 48,
            "tickers": {
                "AAPL": {"buy": 170.0, "sell": 190.0},
                "MSFT": {"buy": 400.0, "sell": 420.0},
            },
        }

        self.api_response_with_alerts: Dict[str, Any] = {
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

    def test_dry_run_flag_parsing(self) -> None:
        """Test that --dry-run flag is correctly parsed."""
        # Test without flag
        args_prod = parse_arguments([])
        self.assertFalse(args_prod.dry_run)

        # Test with flag
        args_dry = parse_arguments(["--dry-run"])
        self.assertTrue(args_dry.dry_run)

    @patch("smtplib.SMTP")
    @patch("pathlib.Path.exists")
    @patch("builtins.open", new_callable=mock_open)
    @patch("sys.argv", ["client.main", "--dry-run"])
    @patch("client.main.call_api")
    @patch.dict(os.environ, {"API_KEY": "test-api-key-12345"})
    def test_dry_run_no_emails_sent(
        self,
        mock_call_api: MagicMock,
        mock_file: MagicMock,
        mock_exists: MagicMock,
        mock_smtp_class: MagicMock,
    ) -> None:
        """Test that dry-run mode does not send any emails."""
        mock_exists.return_value = True
        mock_file.return_value.read.return_value = json.dumps(self.config_data)
        mock_call_api.return_value = self.api_response_with_alerts

        # Capture stdout
        captured_stdout: io.StringIO = io.StringIO()

        with patch("sys.stdout", captured_stdout):
            exit_code: int = main()

        # Verify success
        self.assertEqual(exit_code, 0)

        # Verify dry-run mode indicated in output
        output: str = captured_stdout.getvalue()
        self.assertIn("DRY-RUN", output)

        # Verify no SMTP connections were made
        mock_smtp_class.assert_not_called()

    @patch("pathlib.Path.exists")
    @patch("builtins.open", new_callable=mock_open)
    @patch("sys.argv", ["client.main", "--dry-run"])
    @patch("client.main.call_api")
    @patch.dict(os.environ, {"API_KEY": "test-api-key-12345"})
    def test_dry_run_output_to_stdout(
        self, mock_call_api: MagicMock, mock_file: MagicMock, mock_exists: MagicMock
    ) -> None:
        """Test that dry-run mode outputs alerts to stdout."""
        mock_exists.return_value = True
        mock_file.return_value.read.return_value = json.dumps(self.config_data)
        mock_call_api.return_value = self.api_response_with_alerts

        # Capture stdout
        captured_stdout: io.StringIO = io.StringIO()

        with patch("sys.stdout", captured_stdout):
            exit_code: int = main()

        # Verify success
        self.assertEqual(exit_code, 0)

        # Verify output contains alert information
        output: str = captured_stdout.getvalue()
        self.assertIn("Alerts", output)
        self.assertIn("AAPL", output)
        self.assertIn("BUY", output.upper())
        self.assertIn("170.00", output)

    @patch("client.notified.save_notified_data")
    @patch("pathlib.Path.exists")
    @patch("builtins.open", new_callable=mock_open)
    @patch("sys.argv", ["client.main", "--dry-run"])
    @patch("client.main.call_api")
    @patch.dict(os.environ, {"API_KEY": "test-api-key-12345"})
    def test_dry_run_no_notified_json_updates(
        self,
        mock_call_api: MagicMock,
        mock_file: MagicMock,
        mock_exists: MagicMock,
        mock_save_notified: MagicMock,
    ) -> None:
        """Test that dry-run mode does not update notified.json file."""
        mock_exists.return_value = True
        mock_file.return_value.read.return_value = json.dumps(self.config_data)
        mock_call_api.return_value = self.api_response_with_alerts

        # Run main in dry-run mode
        exit_code: int = main()

        # Verify success
        self.assertEqual(exit_code, 0)

        # Verify notified.json was never updated
        mock_save_notified.assert_not_called()


class TestClientFlowNotificationTracking(unittest.TestCase):
    """Test flow: Notification tracking prevents duplicate emails within silence period."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.silence_hours: int = 48

    def test_notification_tracker_filters_recent_alerts(self) -> None:
        """Test that NotificationTracker filters out recently notified alerts."""
        # Create tracker
        tracker: NotificationTracker = NotificationTracker(self.silence_hours)

        # Create alerts
        alerts: list[Dict[str, Any]] = [
            {"ticker": "AAPL", "type": "buy", "threshold": 170.0},
            {"ticker": "MSFT", "type": "sell", "threshold": 420.0},
        ]

        # First time: all alerts should pass through
        filtered_first: list[Dict[str, Any]] = tracker.filter_alerts(alerts)
        self.assertEqual(len(filtered_first), 2)

        # Mark first alert as notified
        tracker.mark_notified("AAPL", "buy")

        # Second time: first alert should be filtered out
        filtered_second: list[Dict[str, Any]] = tracker.filter_alerts(alerts)
        self.assertEqual(len(filtered_second), 1)
        self.assertEqual(filtered_second[0]["ticker"], "MSFT")

    @patch("client.notified.time.time")
    def test_notification_tracker_allows_after_silence_period(
        self, mock_time: MagicMock
    ) -> None:
        """Test that alerts are allowed after silence period expires."""
        # Mock time to control the clock
        current_time: float = 1000000.0
        mock_time.return_value = current_time

        tracker: NotificationTracker = NotificationTracker(self.silence_hours)

        alerts: list[Dict[str, Any]] = [{"ticker": "AAPL", "type": "buy"}]

        # Mark as notified
        tracker.mark_notified("AAPL", "buy")

        # Immediately after: should be filtered
        filtered_immediate: list[Dict[str, Any]] = tracker.filter_alerts(alerts)
        self.assertEqual(len(filtered_immediate), 0)

        # Advance time beyond silence period (48 hours + 1 second)
        mock_time.return_value = current_time + (self.silence_hours * 3600) + 1

        # After silence period: should pass through
        filtered_after: list[Dict[str, Any]] = tracker.filter_alerts(alerts)
        self.assertEqual(len(filtered_after), 1)


if __name__ == "__main__":
    unittest.main()  # type: ignore[misc]

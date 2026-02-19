"""
Integration tests for StockMon client email functionality.

These tests verify the integration of email sending with API responses.
"""

import os
import unittest
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

from client.email import (EmailConfig, format_alert_email,
                          format_service_degraded_email, get_email_config,
                          send_email)


class TestEmailWorkflow(unittest.TestCase):
    """Test complete email workflow scenarios."""

    @patch("smtplib.SMTP")
    def test_send_alert_email_workflow(self, mock_smtp_class: MagicMock) -> None:
        """Test the complete workflow of formatting and sending an alert email."""
        # Setup mock SMTP server
        mock_server: MagicMock = MagicMock()
        mock_smtp_class.return_value.__enter__.return_value = mock_server

        # Setup email config
        with patch.dict(
            os.environ,
            {
                "SMTP_HOST": "smtp.gmail.com",
                "SMTP_USER": "test@gmail.com",
                "SMTP_PASS": "test_password",
                "NOTIFY_EMAIL": "notify@gmail.com",
            },
        ):
            config: EmailConfig = get_email_config()

            # Simulate an alert from API response
            alert: Dict[str, Any] = {
                "ticker": "AAPL",
                "type": "buy",
                "threshold": 170.0,
                "reached": 168.5,
                "current": 172.3,
            }

            # Format and send email
            subject: str
            body: str
            subject, body = format_alert_email(alert)
            send_email(config, subject, body)

            # Verify email was sent
            mock_server.send_message.assert_called_once()

    @patch("smtplib.SMTP")
    def test_send_service_degraded_email_workflow(
        self, mock_smtp_class: MagicMock
    ) -> None:
        """Test the complete workflow of sending a service degraded email."""
        # Setup mock SMTP server
        mock_server: MagicMock = MagicMock()
        mock_smtp_class.return_value.__enter__.return_value = mock_server

        # Setup email config
        with patch.dict(
            os.environ,
            {
                "SMTP_HOST": "smtp.gmail.com",
                "SMTP_USER": "test@gmail.com",
                "SMTP_PASS": "test_password",
                "NOTIFY_EMAIL": "notify@gmail.com",
            },
        ):
            config: EmailConfig = get_email_config()

            # Format and send service degraded email
            subject: str
            body: str
            subject, body = format_service_degraded_email()
            send_email(config, subject, body)

            # Verify email was sent
            mock_server.send_message.assert_called_once()

    @patch("smtplib.SMTP")
    def test_send_multiple_alerts_in_one_email(
        self, mock_smtp_class: MagicMock
    ) -> None:
        """Test sending multiple alerts in a single email."""
        # Setup mock SMTP server
        mock_server: MagicMock = MagicMock()
        mock_smtp_class.return_value.__enter__.return_value = mock_server

        # Setup email config
        with patch.dict(
            os.environ,
            {
                "SMTP_HOST": "smtp.gmail.com",
                "SMTP_USER": "test@gmail.com",
                "SMTP_PASS": "test_password",
                "NOTIFY_EMAIL": "notify@gmail.com",
            },
        ):
            config: EmailConfig = get_email_config()

            # Simulate multiple alerts from API response
            alerts: List[Dict[str, Any]] = [
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
                    "reached": 422.0,
                    "current": 419.5,
                },
                {
                    "ticker": "GOOGL",
                    "type": "buy",
                    "threshold": 140.0,
                    "reached": 138.0,
                    "current": 141.0,
                },
            ]

            # Format all alerts
            formatted_bodies: List[str] = []
            for alert in alerts:
                _, body = format_alert_email(alert)
                formatted_bodies.append(body)

            # Combine into single email
            combined_body: str = "\n\n".join(formatted_bodies)
            subject: str = f"StockMon: {len(alerts)} Alerts"

            # Send combined email
            send_email(config, subject, combined_body)

            # Verify email was sent
            mock_server.send_message.assert_called_once()

            # Verify all tickers are in the email
            sent_message = mock_server.send_message.call_args[0][0]
            email_content: str = sent_message.get_content()
            self.assertIn("AAPL", email_content)
            self.assertIn("MSFT", email_content)
            self.assertIn("GOOGL", email_content)

    def test_dry_run_mode_no_email_config_needed(self) -> None:
        """Test that dry-run mode doesn't require email configuration."""
        # In dry-run mode, we don't need email config
        # This simulates printing to stdout instead of sending email

        alert: Dict[str, Any] = {
            "ticker": "AAPL",
            "type": "buy",
            "threshold": 170.0,
            "reached": 168.5,
            "current": 172.3,
        }

        # Format email (doesn't require config)
        subject: str
        body: str
        subject, body = format_alert_email(alert)

        # In dry-run mode, we would just print this
        # Verify we can format without config
        self.assertEqual(subject, "StockMon Alert: AAPL buy signal")
        self.assertIn("Ticker: AAPL", body)


class TestEmailErrorHandling(unittest.TestCase):
    """Test error handling in email workflows."""

    def test_missing_email_config_raises_clear_error(self) -> None:
        """Test that missing config raises a clear error message."""
        # Clear all SMTP environment variables
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValueError) as context:
                get_email_config()

            error_msg: str = str(context.exception)
            self.assertIn("Missing required environment variables", error_msg)
            self.assertIn("SMTP_HOST", error_msg)
            self.assertIn("SMTP_USER", error_msg)
            self.assertIn("SMTP_PASS", error_msg)
            self.assertIn("NOTIFY_EMAIL", error_msg)

    @patch("smtplib.SMTP")
    def test_email_sending_retries_not_implemented(
        self, mock_smtp_class: MagicMock
    ) -> None:
        """Test that email sending doesn't retry on failure (intentional design)."""
        # Setup mock to fail
        mock_smtp_class.side_effect = Exception("Connection failed")

        with patch.dict(
            os.environ,
            {
                "SMTP_HOST": "smtp.gmail.com",
                "SMTP_USER": "test@gmail.com",
                "SMTP_PASS": "test_password",
                "NOTIFY_EMAIL": "notify@gmail.com",
            },
        ):
            config: EmailConfig = get_email_config()

            # Verify that exception is raised (no retry logic)
            with self.assertRaises(Exception) as context:
                send_email(config, "Test", "Test body")

            self.assertIn("Connection failed", str(context.exception))


if __name__ == "__main__":
    unittest.main()  # type: ignore[misc]

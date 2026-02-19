"""
Unit tests for StockMon client email functionality.

These tests verify email sending functionality using mocked SMTP.
"""

import os
import smtplib
import unittest
from email.message import EmailMessage
from typing import Any, Dict
from unittest.mock import MagicMock, patch

from client.email import (EmailConfig, format_alert_email,
                          format_service_degraded_email, get_email_config,
                          send_email)


class TestEmailConfig(unittest.TestCase):
    """Test email configuration loading from environment variables."""

    def test_get_email_config_all_vars_present(self) -> None:
        """Test loading email config when all environment variables are present."""
        with patch.dict(
            os.environ,
            {
                "SMTP_HOST": "smtp.test.com",
                "SMTP_USER": "user@test.com",
                "SMTP_PASS": "test_password",
                "NOTIFY_EMAIL": "notify@test.com",
            },
        ):
            config: EmailConfig = get_email_config()

            self.assertEqual(config.smtp_host, "smtp.test.com")
            self.assertEqual(config.smtp_user, "user@test.com")
            self.assertEqual(config.smtp_pass, "test_password")
            self.assertEqual(config.notify_email, "notify@test.com")

    def test_get_email_config_missing_smtp_host(self) -> None:
        """Test that missing SMTP_HOST raises ValueError."""
        with patch.dict(
            os.environ,
            {
                "SMTP_USER": "user@test.com",
                "SMTP_PASS": "test_password",
                "NOTIFY_EMAIL": "notify@test.com",
            },
            clear=True,
        ):
            with self.assertRaises(ValueError) as context:
                get_email_config()

            self.assertIn("SMTP_HOST", str(context.exception))

    def test_get_email_config_missing_smtp_user(self) -> None:
        """Test that missing SMTP_USER raises ValueError."""
        with patch.dict(
            os.environ,
            {
                "SMTP_HOST": "smtp.test.com",
                "SMTP_PASS": "test_password",
                "NOTIFY_EMAIL": "notify@test.com",
            },
            clear=True,
        ):
            with self.assertRaises(ValueError) as context:
                get_email_config()

            self.assertIn("SMTP_USER", str(context.exception))

    def test_get_email_config_missing_smtp_pass(self) -> None:
        """Test that missing SMTP_PASS raises ValueError."""
        with patch.dict(
            os.environ,
            {
                "SMTP_HOST": "smtp.test.com",
                "SMTP_USER": "user@test.com",
                "NOTIFY_EMAIL": "notify@test.com",
            },
            clear=True,
        ):
            with self.assertRaises(ValueError) as context:
                get_email_config()

            self.assertIn("SMTP_PASS", str(context.exception))

    def test_get_email_config_missing_notify_email(self) -> None:
        """Test that missing NOTIFY_EMAIL raises ValueError."""
        with patch.dict(
            os.environ,
            {
                "SMTP_HOST": "smtp.test.com",
                "SMTP_USER": "user@test.com",
                "SMTP_PASS": "test_password",
            },
            clear=True,
        ):
            with self.assertRaises(ValueError) as context:
                get_email_config()

            self.assertIn("NOTIFY_EMAIL", str(context.exception))


class TestEmailFormatting(unittest.TestCase):
    """Test email formatting for alerts and service degradation."""

    def test_format_alert_email_buy_signal(self) -> None:
        """Test formatting email for a buy signal alert."""
        alert: Dict[str, Any] = {
            "ticker": "AAPL",
            "type": "buy",
            "threshold": 170.0,
            "reached": 168.5,
            "current": 172.3,
        }

        subject: str
        body: str
        subject, body = format_alert_email(alert)

        # Verify subject format
        self.assertEqual(subject, "StockMon Alert: AAPL buy signal")

        # Verify body contains all required information
        self.assertIn("Ticker: AAPL", body)
        self.assertIn("Tipo: BUY", body)
        self.assertIn("Umbral: $170.00", body)
        self.assertIn("Alcanzado: $168.50", body)
        self.assertIn("Actual: $172.30", body)
        self.assertIn("Generado por StockMon", body)

    def test_format_alert_email_sell_signal(self) -> None:
        """Test formatting email for a sell signal alert."""
        alert: Dict[str, Any] = {
            "ticker": "MSFT",
            "type": "sell",
            "threshold": 420.0,
            "reached": 422.75,
            "current": 419.5,
        }

        subject: str
        body: str
        subject, body = format_alert_email(alert)

        # Verify subject format
        self.assertEqual(subject, "StockMon Alert: MSFT sell signal")

        # Verify body contains all required information
        self.assertIn("Ticker: MSFT", body)
        self.assertIn("Tipo: SELL", body)
        self.assertIn("Umbral: $420.00", body)
        self.assertIn("Alcanzado: $422.75", body)
        self.assertIn("Actual: $419.50", body)
        self.assertIn("Generado por StockMon", body)

    def test_format_service_degraded_email(self) -> None:
        """Test formatting email for service degradation."""
        subject: str
        body: str
        subject, body = format_service_degraded_email()

        # Verify subject format matches spec exactly
        self.assertEqual(subject, "StockMon: Servicio degradado - Revisar API")

        # Verify body contains required information
        self.assertIn("YFinance parece no funcionar", body)
        self.assertIn("Todos los tickers fallaron", body)
        self.assertIn("actualizar las dependencias de la API", body)


class TestEmailSending(unittest.TestCase):
    """Test email sending functionality with mocked SMTP."""

    @patch("smtplib.SMTP")
    def test_send_email_success(self, mock_smtp_class: MagicMock) -> None:
        """Test successful email sending."""
        # Setup mock SMTP server
        mock_server: MagicMock = MagicMock()
        mock_smtp_class.return_value.__enter__.return_value = mock_server

        # Setup email config
        config: EmailConfig = EmailConfig(
            smtp_host="smtp.test.com",
            smtp_user="user@test.com",
            smtp_pass="test_password",
            notify_email="notify@test.com",
        )

        # Send email
        subject: str = "Test Subject"
        body: str = "Test Body"
        send_email(config, subject, body)

        # Verify SMTP connection was established
        mock_smtp_class.assert_called_once_with("smtp.test.com", 587)

        # Verify STARTTLS was called
        mock_server.starttls.assert_called_once()

        # Verify login was called with correct credentials
        mock_server.login.assert_called_once_with("user@test.com", "test_password")

        # Verify send_message was called
        mock_server.send_message.assert_called_once()

        # Verify the message content
        sent_message: EmailMessage = mock_server.send_message.call_args[0][0]
        self.assertEqual(sent_message["Subject"], "Test Subject")
        self.assertEqual(sent_message["From"], "user@test.com")
        self.assertEqual(sent_message["To"], "notify@test.com")
        self.assertEqual(sent_message.get_content().strip(), "Test Body")

    @patch("smtplib.SMTP")
    def test_send_email_smtp_connection_failure(
        self, mock_smtp_class: MagicMock
    ) -> None:
        """Test email sending when SMTP connection fails."""
        # Setup mock to raise exception on connection
        mock_smtp_class.side_effect = smtplib.SMTPConnectError(421, "Cannot connect")

        config: EmailConfig = EmailConfig(
            smtp_host="smtp.test.com",
            smtp_user="user@test.com",
            smtp_pass="test_password",
            notify_email="notify@test.com",
        )

        # Verify that exception is raised
        with self.assertRaises(smtplib.SMTPConnectError):
            send_email(config, "Test", "Test body")

    @patch("smtplib.SMTP")
    def test_send_email_authentication_failure(
        self, mock_smtp_class: MagicMock
    ) -> None:
        """Test email sending when authentication fails."""
        # Setup mock SMTP server that fails on login
        mock_server: MagicMock = MagicMock()
        mock_server.login.side_effect = smtplib.SMTPAuthenticationError(
            535, "Authentication failed"
        )
        mock_smtp_class.return_value.__enter__.return_value = mock_server

        config: EmailConfig = EmailConfig(
            smtp_host="smtp.test.com",
            smtp_user="user@test.com",
            smtp_pass="wrong_password",
            notify_email="notify@test.com",
        )

        # Verify that exception is raised
        with self.assertRaises(smtplib.SMTPAuthenticationError):
            send_email(config, "Test", "Test body")

    @patch("smtplib.SMTP")
    def test_send_email_with_multiple_alerts(self, mock_smtp_class: MagicMock) -> None:
        """Test sending email with multiple alerts in the body."""
        # Setup mock SMTP server
        mock_server: MagicMock = MagicMock()
        mock_smtp_class.return_value.__enter__.return_value = mock_server

        config: EmailConfig = EmailConfig(
            smtp_host="smtp.test.com",
            smtp_user="user@test.com",
            smtp_pass="test_password",
            notify_email="notify@test.com",
        )

        # Create body with multiple alerts
        alert1: Dict[str, Any] = {
            "ticker": "AAPL",
            "type": "buy",
            "threshold": 170.0,
            "reached": 168.5,
            "current": 172.3,
        }
        alert2: Dict[str, Any] = {
            "ticker": "MSFT",
            "type": "sell",
            "threshold": 420.0,
            "reached": 422.0,
            "current": 419.0,
        }

        _, body1 = format_alert_email(alert1)
        _, body2 = format_alert_email(alert2)
        combined_body: str = body1 + "\n\n" + body2

        # Send email
        send_email(config, "Multiple Alerts", combined_body)

        # Verify email was sent
        mock_server.send_message.assert_called_once()
        sent_message: EmailMessage = mock_server.send_message.call_args[0][0]
        message_body: str = sent_message.get_content()

        # Verify both alerts are in the body
        self.assertIn("AAPL", message_body)
        self.assertIn("MSFT", message_body)


if __name__ == "__main__":
    unittest.main()  # type: ignore[misc]

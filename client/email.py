"""
StockMon Client - Email functionality.

This module provides email sending capabilities for the StockMon client,
including formatting alerts and sending notifications via SMTP.
"""

import os
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage
from typing import Any, Dict, Tuple


@dataclass
class EmailConfig:
    """
    Configuration for SMTP email sending.

    Attributes:
        smtp_host: SMTP server hostname (e.g., smtp.gmail.com).
        smtp_user: SMTP username/email address.
        smtp_pass: SMTP password or app password.
        notify_email: Destination email address for notifications.
    """

    smtp_host: str
    smtp_user: str
    smtp_pass: str
    notify_email: str


def get_email_config() -> EmailConfig:
    """
    Load email configuration from environment variables.

    Required environment variables:
        - SMTP_HOST: SMTP server hostname
        - SMTP_USER: SMTP username/email
        - SMTP_PASS: SMTP password or app password
        - NOTIFY_EMAIL: Destination email for notifications

    Returns:
        EmailConfig: Configuration object with SMTP settings.

    Raises:
        ValueError: If any required environment variable is missing.

    Example:
        os.environ["SMTP_HOST"] = "smtp.gmail.com"
        os.environ["SMTP_USER"] = "user@gmail.com"
        os.environ["SMTP_PASS"] = "app_password"
        os.environ["NOTIFY_EMAIL"] = "notify@email.com"

        config = get_email_config()
    """
    smtp_host: str | None = os.environ.get("SMTP_HOST")
    smtp_user: str | None = os.environ.get("SMTP_USER")
    smtp_pass: str | None = os.environ.get("SMTP_PASS")
    notify_email: str | None = os.environ.get("NOTIFY_EMAIL")

    missing_vars: list[str] = []

    if not smtp_host:
        missing_vars.append("SMTP_HOST")
    if not smtp_user:
        missing_vars.append("SMTP_USER")
    if not smtp_pass:
        missing_vars.append("SMTP_PASS")
    if not notify_email:
        missing_vars.append("NOTIFY_EMAIL")

    if missing_vars:
        raise ValueError(
            f"Missing required environment variables: {', '.join(missing_vars)}\n"
            "Please set these variables in your .env file or environment."
        )

    # After validation, we know these are not None
    # Assert this for type checker since we raised ValueError if any were None
    assert smtp_host is not None
    assert smtp_user is not None
    assert smtp_pass is not None
    assert notify_email is not None

    return EmailConfig(
        smtp_host=smtp_host,
        smtp_user=smtp_user,
        smtp_pass=smtp_pass,
        notify_email=notify_email,
    )


def format_alert_email(alert: Dict[str, Any]) -> Tuple[str, str]:
    """
    Format an alert into email subject and body.

    Args:
        alert: Alert dictionary with keys: ticker, type, threshold, reached, current.

    Returns:
        Tuple[str, str]: A tuple of (subject, body).

    Example:
        alert = {
            "ticker": "AAPL",
            "type": "buy",
            "threshold": 170.0,
            "reached": 168.5,
            "current": 172.3
        }
        subject, body = format_alert_email(alert)

        # subject: "StockMon Alert: AAPL buy signal"
        # body contains formatted alert details
    """
    ticker: str = alert["ticker"]
    signal_type: str = alert["type"]
    threshold: float = alert["threshold"]
    reached: float = alert["reached"]
    current: float = alert["current"]

    # Format subject per spec: "StockMon Alert: {ticker} {signal_type} signal"
    subject: str = f"StockMon Alert: {ticker} {signal_type} signal"

    # Format body per spec (lines 103-111 of client_plan.md)
    body: str = f"""Ticker: {ticker}
Tipo: {signal_type.upper()}
Umbral: ${threshold:.2f}
Alcanzado: ${reached:.2f}
Actual: ${current:.2f}

---
Generado por StockMon"""

    return subject, body


def format_service_degraded_email() -> Tuple[str, str]:
    """
    Format a service degraded notification email.

    This is sent when the API returns service_degraded: true,
    indicating that YFinance is likely not functioning correctly.

    Returns:
        Tuple[str, str]: A tuple of (subject, body).

    Example:
        subject, body = format_service_degraded_email()

        # subject: "StockMon: Servicio degradado - Revisar API"
        # body: Warning message about YFinance issues
    """
    # Format per spec (lines 116-124 of client_plan.md)
    subject: str = "StockMon: Servicio degradado - Revisar API"

    body: str = """YFinance parece no funcionar. Todos los tickers fallaron.
Es probable que necesites actualizar las dependencias de la API."""

    return subject, body


def send_email(config: EmailConfig, subject: str, body: str) -> None:
    """
    Send an email via SMTP.

    Args:
        config: Email configuration with SMTP settings.
        subject: Email subject line.
        body: Email body content (plain text).

    Raises:
        smtplib.SMTPConnectError: If connection to SMTP server fails.
        smtplib.SMTPAuthenticationError: If SMTP authentication fails.
        smtplib.SMTPException: For other SMTP-related errors.

    Example:
        config = EmailConfig(
            smtp_host="smtp.gmail.com",
            smtp_user="user@gmail.com",
            smtp_pass="app_password",
            notify_email="notify@email.com"
        )
        send_email(config, "Test Alert", "This is a test alert.")
    """
    # Create email message
    msg: EmailMessage = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = config.smtp_user
    msg["To"] = config.notify_email
    msg.set_content(body)

    # Connect to SMTP server and send email
    with smtplib.SMTP(config.smtp_host, 587) as server:
        server.starttls()  # Enable TLS encryption
        server.login(config.smtp_user, config.smtp_pass)
        server.send_message(msg)

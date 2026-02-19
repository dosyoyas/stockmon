"""
Unit tests for pytest fixtures in conftest.py.

These tests verify that the custom fixtures for client testing work correctly.
"""

import json
import time
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock

from client.email import EmailConfig, send_email


def test_mock_api_response_structure(mock_api_response: Dict[str, Any]) -> None:
    """Test that mock_api_response has the correct structure."""
    # Verify required keys are present
    assert "alerts" in mock_api_response
    assert "errors" in mock_api_response
    assert "market_open" in mock_api_response
    assert "service_degraded" in mock_api_response
    assert "checked_at" in mock_api_response

    # Verify data types
    assert isinstance(mock_api_response["alerts"], list)
    assert isinstance(mock_api_response["errors"], list)
    assert isinstance(mock_api_response["market_open"], bool)
    assert isinstance(mock_api_response["service_degraded"], bool)
    assert isinstance(mock_api_response["checked_at"], str)


def test_mock_api_response_has_alerts(mock_api_response: Dict[str, Any]) -> None:
    """Test that mock_api_response contains alerts."""
    assert len(mock_api_response["alerts"]) > 0
    assert len(mock_api_response["errors"]) == 0
    assert not mock_api_response["service_degraded"]
    assert mock_api_response["market_open"]


def test_mock_api_response_alert_structure(mock_api_response: Dict[str, Any]) -> None:
    """Test that alerts in mock_api_response have correct structure."""
    alert: Dict[str, Any] = mock_api_response["alerts"][0]

    # Verify alert has required fields
    assert "ticker" in alert
    assert "type" in alert
    assert "threshold" in alert
    assert "reached" in alert
    assert "current" in alert

    # Verify data types
    assert isinstance(alert["ticker"], str)
    assert isinstance(alert["type"], str)
    assert isinstance(alert["threshold"], (int, float))
    assert isinstance(alert["reached"], (int, float))
    assert isinstance(alert["current"], (int, float))


def test_mock_api_degraded_structure(mock_api_degraded: Dict[str, Any]) -> None:
    """Test that mock_api_degraded has the correct structure."""
    # Verify required keys are present
    assert "alerts" in mock_api_degraded
    assert "errors" in mock_api_degraded
    assert "market_open" in mock_api_degraded
    assert "service_degraded" in mock_api_degraded
    assert "checked_at" in mock_api_degraded


def test_mock_api_degraded_has_errors(mock_api_degraded: Dict[str, Any]) -> None:
    """Test that mock_api_degraded indicates service degradation."""
    assert len(mock_api_degraded["alerts"]) == 0
    assert len(mock_api_degraded["errors"]) > 0
    assert mock_api_degraded["service_degraded"]


def test_mock_api_degraded_error_structure(mock_api_degraded: Dict[str, Any]) -> None:
    """Test that errors in mock_api_degraded have correct structure."""
    error: Dict[str, str] = mock_api_degraded["errors"][0]

    # Verify error has required fields
    assert "ticker" in error
    assert "error" in error

    # Verify data types
    assert isinstance(error["ticker"], str)
    assert isinstance(error["error"], str)


def test_mock_smtp_email_sending(mock_smtp: MagicMock) -> None:
    """Test that mock_smtp allows email sending without real SMTP."""
    # Create email config
    config: EmailConfig = EmailConfig(
        smtp_host="smtp.test.com",
        smtp_user="user@test.com",
        smtp_pass="test_password",
        notify_email="notify@test.com",
    )

    # Send email (should not raise exception)
    send_email(config, "Test Subject", "Test Body")

    # Verify mock was called
    mock_smtp.assert_called_once_with("smtp.test.com", 587)

    # Get the mock server instance
    mock_server: MagicMock = mock_smtp.return_value.__enter__.return_value

    # Verify server methods were called
    mock_server.starttls.assert_called_once()
    mock_server.login.assert_called_once_with("user@test.com", "test_password")
    mock_server.send_message.assert_called_once()


def test_mock_smtp_multiple_emails(mock_smtp: MagicMock) -> None:
    """Test sending multiple emails with mock_smtp."""
    config: EmailConfig = EmailConfig(
        smtp_host="smtp.test.com",
        smtp_user="user@test.com",
        smtp_pass="test_password",
        notify_email="notify@test.com",
    )

    # Send two emails
    send_email(config, "Email 1", "Body 1")
    send_email(config, "Email 2", "Body 2")

    # Verify mock was called twice
    assert mock_smtp.call_count == 2


def test_temp_notified_file_exists(temp_notified_file: Path) -> None:
    """Test that temp_notified_file creates a file."""
    assert temp_notified_file.exists()
    assert temp_notified_file.name == "notified.json"


def test_temp_notified_file_is_empty_json(temp_notified_file: Path) -> None:
    """Test that temp_notified_file starts with empty JSON object."""
    with open(temp_notified_file, "r", encoding="utf-8") as notified_json:
        data: Dict[str, float] = json.load(notified_json)

    assert data == {}


def test_temp_notified_file_can_write_and_read(temp_notified_file: Path) -> None:
    """Test that temp_notified_file can be written to and read from."""
    # Write notification data
    current_time: float = time.time()
    test_data: Dict[str, float] = {
        "AAPL:buy": current_time,
        "MSFT:sell": current_time - 3600,
    }

    with open(temp_notified_file, "w", encoding="utf-8") as notified_json:
        json.dump(test_data, notified_json)

    # Read it back
    with open(temp_notified_file, "r", encoding="utf-8") as notified_json:
        loaded_data: Dict[str, float] = json.load(notified_json)

    # Verify data was preserved
    assert loaded_data["AAPL:buy"] == current_time
    assert loaded_data["MSFT:sell"] == current_time - 3600


def test_temp_notified_file_in_tmp_directory(temp_notified_file: Path) -> None:
    """Test that temp_notified_file is in a temporary directory."""
    # The parent directory should be a pytest tmp_path
    assert temp_notified_file.parent.exists()
    assert temp_notified_file.parent.is_dir()

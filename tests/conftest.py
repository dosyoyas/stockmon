"""
StockMon Test Configuration.

This module provides pytest fixtures for testing the StockMon API.
"""

# pylint: disable=W0621,C0415

import os
from pathlib import Path
from typing import Any, Dict, Generator
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture
def mock_yfinance() -> Generator[MagicMock, None, None]:
    """
    Mock yfinance.Ticker to return controlled test data.

    This fixture mocks the yfinance.Ticker class to avoid making real API calls
    to Yahoo Finance during tests. It provides a configurable mock that returns
    predefined DataFrames for historical data.

    Yields:
        MagicMock: A mocked Ticker class with history() method configured.

    Example:
        def test_stock_data(mock_yfinance):
            # Ticker instance returns controlled data
            ticker = yfinance.Ticker("AAPL")
            data = ticker.history(period="1d", interval="1h")
            assert not data.empty
    """
    with patch("yfinance.Ticker") as mock_ticker_class:
        # Create a mock instance that will be returned when Ticker() is called
        mock_ticker_instance: MagicMock = MagicMock()

        # Configure the history() method to return a DataFrame with test data
        # Default: 24 hourly data points with predictable values
        default_data: Dict[str, list[float]] = {
            "Open": [170.0] * 24,
            "High": [175.0] * 24,
            "Low": [168.0] * 24,
            "Close": [172.0] * 24,
            "Volume": [1000000] * 24,
        }
        mock_ticker_instance.history.return_value = pd.DataFrame(default_data)

        # When yfinance.Ticker("SYMBOL") is called, return the mock instance
        mock_ticker_class.return_value = mock_ticker_instance

        yield mock_ticker_class


@pytest.fixture
def test_api_key() -> str:
    """
    Provide a test API key for authenticated requests.

    Returns:
        str: A test API key value.
    """
    return "test-api-key-12345"


@pytest.fixture
def app(test_api_key: str, monkeypatch: pytest.MonkeyPatch) -> FastAPI:
    """
    Create a FastAPI application instance for testing.

    This fixture sets up the FastAPI app with test configuration, including
    setting the API_KEY environment variable.

    Args:
        test_api_key: The test API key to use.
        monkeypatch: Pytest's monkeypatch fixture for modifying environment.

    Returns:
        FastAPI: A configured FastAPI application instance.
    """
    # Set the API_KEY environment variable for the test
    monkeypatch.setenv("API_KEY", test_api_key)

    # Import the app here to ensure environment variables are set first
    # This avoids import-time errors when the main app tries to read API_KEY
    try:
        from app.main import \
            app as fastapi_app  # type: ignore[import-not-found]

        return fastapi_app
    except ImportError:
        # If app doesn't exist yet, create a minimal FastAPI app for testing
        # This allows tests to be written before the main application is implemented
        minimal_app: FastAPI = FastAPI(title="StockMon Test API")

        @minimal_app.get("/health")
        async def health() -> Dict[str, str]:
            """Health check endpoint."""
            return {"status": "ok"}

        return minimal_app


@pytest.fixture
def client(app: FastAPI, test_api_key: str) -> TestClient:
    """
    FastAPI TestClient with valid API key authentication.

    This fixture provides a test client that includes the X-API-Key header
    in all requests, simulating authenticated requests.

    Args:
        app: The FastAPI application instance.
        test_api_key: The test API key to use in headers.

    Returns:
        TestClient: A configured test client with authentication headers.

    Example:
        def test_authenticated_endpoint(client):
            response = client.post("/check-alerts", json={"AAPL": {"buy": 170}})
            assert response.status_code == 200
    """
    test_client: TestClient = TestClient(app)
    # Set default headers for all requests
    test_client.headers.update({"X-API-Key": test_api_key})
    return test_client


@pytest.fixture
def client_no_auth(app: FastAPI) -> TestClient:
    """
    FastAPI TestClient without API key authentication.

    This fixture provides a test client without any authentication headers,
    useful for testing authentication failures and public endpoints.

    Args:
        app: The FastAPI application instance.

    Returns:
        TestClient: A test client without authentication headers.

    Example:
        def test_unauthenticated_endpoint(client_no_auth):
            response = client_no_auth.post("/check-alerts", json={})
            assert response.status_code == 401
    """
    return TestClient(app)


@pytest.fixture
def sample_ticker_data() -> Dict[str, Dict[str, float]]:
    """
    Provide sample ticker threshold data for testing.

    Returns:
        Dict[str, Dict[str, float]]: Sample ticker thresholds.

    Example:
        def test_with_sample_data(sample_ticker_data):
            assert "AAPL" in sample_ticker_data
            assert sample_ticker_data["AAPL"]["buy"] == 170.0
    """
    return {
        "AAPL": {"buy": 170.0, "sell": 190.0},
        "MSFT": {"buy": 400.0, "sell": 420.0},
        "GOOGL": {"buy": 140.0, "sell": 160.0},
    }


@pytest.fixture
def mock_yfinance_with_data(
    mock_yfinance: MagicMock,
) -> Generator[MagicMock, None, None]:
    """
    Mock yfinance.Ticker with configurable data per ticker symbol.

    This is an advanced fixture that allows tests to configure different
    responses for different ticker symbols.

    Args:
        mock_yfinance: The basic mock_yfinance fixture.

    Yields:
        MagicMock: A mocked Ticker class with per-symbol configuration.

    Example:
        def test_multiple_tickers(mock_yfinance_with_data):
            # Configure specific data for AAPL
            configure_ticker_data(mock_yfinance_with_data, "AAPL",
                                  high=195.0, low=165.0)
    """

    def create_ticker_data(  # pylint: disable=R0913,R0917
        high: float = 175.0,
        low: float = 168.0,
        open_price: float = 170.0,
        close: float = 172.0,
        volume: int = 1000000,
        periods: int = 24,
    ) -> pd.DataFrame:
        """
        Create a DataFrame with specified price data.

        Args:
            high: High price for the period.
            low: Low price for the period.
            open_price: Opening price.
            close: Closing price.
            volume: Trading volume.
            periods: Number of data points (hours).

        Returns:
            pd.DataFrame: A DataFrame with the specified data.
        """
        data: Dict[str, list[float]] = {
            "Open": [open_price] * periods,
            "High": [high] * periods,
            "Low": [low] * periods,
            "Close": [close] * periods,
            "Volume": [volume] * periods,
        }
        return pd.DataFrame(data)

    # Store the data creation function on the mock for test access
    mock_yfinance.create_ticker_data = create_ticker_data
    yield mock_yfinance


@pytest.fixture(autouse=True)
def reset_environment() -> Generator[None, None, None]:
    """
    Reset environment variables after each test.

    This fixture automatically runs for every test and ensures that
    environment variables are cleaned up to prevent test pollution.

    Yields:
        None
    """
    # Store original environment
    original_env: Dict[str, str] = os.environ.copy()

    yield

    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def mock_api_response() -> Dict[str, Any]:
    """
    Provide a mock successful API response.

    This fixture returns a dictionary representing a typical successful
    response from the /check-alerts endpoint with alerts and no errors.

    Returns:
        Dict[str, Any]: A mock API response with alerts, errors, market status.

    Example:
        def test_api_handling(mock_api_response):
            # Use mock_api_response as return value for mocked requests
            assert len(mock_api_response["alerts"]) > 0
            assert not mock_api_response["service_degraded"]
    """
    return {
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


@pytest.fixture
def mock_api_degraded() -> Dict[str, Any]:
    """
    Provide a mock degraded API response.

    This fixture returns a dictionary representing an API response when
    the service is degraded (e.g., YFinance is not working properly).
    It contains errors for all tickers and no alerts.

    Returns:
        Dict[str, Any]: A mock API response indicating service degradation.

    Example:
        def test_degraded_handling(mock_api_degraded):
            assert mock_api_degraded["service_degraded"]
            assert len(mock_api_degraded["errors"]) > 0
            assert len(mock_api_degraded["alerts"]) == 0
    """
    return {
        "alerts": [],
        "errors": [
            {"ticker": "AAPL", "error": "Failed to fetch data from YFinance"},
            {"ticker": "MSFT", "error": "Failed to fetch data from YFinance"},
        ],
        "market_open": True,
        "service_degraded": True,
        "checked_at": "2024-02-06T14:30:00Z",
    }


@pytest.fixture
def mock_smtp() -> Generator[MagicMock, None, None]:
    """
    Mock SMTP server for email sending tests.

    This fixture mocks the smtplib.SMTP class to avoid sending real emails
    during tests. It provides a configured mock that simulates successful
    SMTP connections, authentication, and message sending.

    Yields:
        MagicMock: A mocked SMTP class with context manager support.

    Example:
        def test_email_sending(mock_smtp):
            # SMTP is already mocked, send_email will not send real emails
            from client.email import send_email, EmailConfig
            config = EmailConfig(
                smtp_host="smtp.test.com",
                smtp_user="user@test.com",
                smtp_pass="test_pass",
                notify_email="notify@test.com"
            )
            send_email(config, "Test", "Test body")
            # Verify mock was called
            mock_smtp.assert_called_once()
    """
    with patch("smtplib.SMTP") as mock_smtp_class:
        # Create a mock server instance that will be returned by the context manager
        mock_server: MagicMock = MagicMock()

        # Configure the SMTP class to return our mock server when used as context manager
        mock_smtp_class.return_value.__enter__.return_value = mock_server
        mock_smtp_class.return_value.__exit__.return_value = None

        # Configure mock server methods
        mock_server.starttls.return_value = None
        mock_server.login.return_value = None
        mock_server.send_message.return_value = {}

        yield mock_smtp_class


@pytest.fixture
def temp_notified_file(tmp_path: Path) -> Generator[Path, None, None]:
    """
    Provide a temporary notified.json file for testing.

    This fixture creates a temporary directory with a notified.json file
    that can be used for testing notification tracking functionality.
    The file is automatically cleaned up after the test completes.

    Args:
        tmp_path: Pytest's built-in temporary directory fixture.

    Yields:
        Path: Path to the temporary notified.json file.

    Example:
        def test_notification_tracking(temp_notified_file):
            # Write notification data
            with open(temp_notified_file, "w") as f:
                json.dump({"AAPL:buy": time.time()}, f)

            # Read it back
            with open(temp_notified_file, "r") as f:
                data = json.load(f)
            assert "AAPL:buy" in data
    """
    # Create a temporary notified.json file
    notified_file: Path = tmp_path / "notified.json"

    # Initialize with empty JSON object
    notified_file.write_text("{}", encoding="utf-8")

    # Patch the client.notified module to use this temp file
    with patch("client.notified.Path") as mock_path_class:
        # When Path(__file__).parent.resolve() is called in client.notified,
        # return the tmp_path directory
        mock_path_instance: MagicMock = MagicMock()
        mock_path_instance.parent.resolve.return_value = tmp_path
        mock_path_class.return_value = mock_path_instance

        yield notified_file

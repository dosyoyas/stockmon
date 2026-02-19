"""
Unit tests for conftest.py fixtures.

This module tests that all pytest fixtures are working correctly
and can be used in other test files.
"""

from typing import Dict
from unittest.mock import MagicMock

import pandas as pd
import yfinance
from fastapi import FastAPI
from fastapi.testclient import TestClient


def test_mock_yfinance_fixture(mock_yfinance: MagicMock) -> None:
    """
    Test that mock_yfinance fixture correctly mocks yfinance.Ticker.

    Args:
        mock_yfinance: The mocked yfinance.Ticker fixture.
    """
    # Create a ticker instance (should use the mock)
    ticker = yfinance.Ticker("AAPL")

    # Call history method
    data: pd.DataFrame = ticker.history(period="1d", interval="1h")

    # Verify the mock was called
    assert mock_yfinance.called, "yfinance.Ticker should have been called"

    # Verify the returned data is a DataFrame
    assert isinstance(data, pd.DataFrame), "Should return a DataFrame"

    # Verify the DataFrame has expected columns
    expected_columns: set[str] = {"Open", "High", "Low", "Close", "Volume"}
    assert set(data.columns) == expected_columns, "DataFrame should have OHLCV columns"

    # Verify the DataFrame has 24 rows (default mock data)
    assert len(data) == 24, "Should have 24 hourly data points"

    # Verify the history method was called on the ticker instance
    ticker.history.assert_called_once_with(period="1d", interval="1h")  # type: ignore[attr-defined]


def test_test_api_key_fixture(test_api_key: str) -> None:
    """
    Test that test_api_key fixture provides a valid API key string.

    Args:
        test_api_key: The test API key fixture.
    """
    assert isinstance(test_api_key, str), "API key should be a string"
    assert len(test_api_key) > 0, "API key should not be empty"
    assert test_api_key == "test-api-key-12345", "Should return expected test API key"


def test_app_fixture(app: FastAPI) -> None:
    """
    Test that app fixture provides a FastAPI application instance.

    Args:
        app: The FastAPI application fixture.
    """
    assert isinstance(app, FastAPI), "Should return a FastAPI instance"
    assert app.title in [
        "StockMon Test API",
        "StockMon API",
    ], "App should have correct title"


def test_client_fixture_has_auth_header(client: TestClient, test_api_key: str) -> None:
    """
    Test that client fixture includes authentication headers.

    Args:
        client: The authenticated test client fixture.
        test_api_key: The test API key fixture.
    """
    assert isinstance(client, TestClient), "Should return a TestClient instance"
    assert "X-API-Key" in client.headers, "Client should have X-API-Key header"
    assert (
        client.headers["X-API-Key"] == test_api_key
    ), "Client should use correct API key"


def test_client_no_auth_fixture(client_no_auth: TestClient) -> None:
    """
    Test that client_no_auth fixture does not include authentication headers.

    Args:
        client_no_auth: The unauthenticated test client fixture.
    """
    assert isinstance(client_no_auth, TestClient), "Should return a TestClient instance"
    assert (
        "X-API-Key" not in client_no_auth.headers
    ), "Client should not have X-API-Key header"


def test_client_can_call_health_endpoint(client: TestClient) -> None:
    """
    Test that the authenticated client can call the /health endpoint.

    Args:
        client: The authenticated test client fixture.
    """
    response = client.get("/health")
    assert response.status_code == 200, "Health endpoint should return 200"
    assert response.json() == {"status": "ok"}, "Should return health status"


def test_client_no_auth_can_call_health_endpoint(client_no_auth: TestClient) -> None:
    """
    Test that the unauthenticated client can call the /health endpoint.

    The /health endpoint should be accessible without authentication.

    Args:
        client_no_auth: The unauthenticated test client fixture.
    """
    response = client_no_auth.get("/health")
    assert response.status_code == 200, "Health endpoint should return 200"
    assert response.json() == {"status": "ok"}, "Should return health status"


def test_sample_ticker_data_fixture(
    sample_ticker_data: Dict[str, Dict[str, float]],
) -> None:
    """
    Test that sample_ticker_data fixture provides valid test data.

    Args:
        sample_ticker_data: The sample ticker data fixture.
    """
    assert isinstance(sample_ticker_data, dict), "Should return a dictionary"
    assert len(sample_ticker_data) > 0, "Should have at least one ticker"

    # Verify AAPL exists with expected structure
    assert "AAPL" in sample_ticker_data, "Should include AAPL ticker"
    assert "buy" in sample_ticker_data["AAPL"], "AAPL should have buy threshold"
    assert "sell" in sample_ticker_data["AAPL"], "AAPL should have sell threshold"

    # Verify values are numbers
    for ticker, thresholds in sample_ticker_data.items():
        assert isinstance(ticker, str), f"Ticker {ticker} should be a string"
        assert isinstance(thresholds, dict), f"Thresholds for {ticker} should be a dict"
        assert isinstance(
            thresholds.get("buy"), float
        ), f"Buy threshold for {ticker} should be a float"
        assert isinstance(
            thresholds.get("sell"), float
        ), f"Sell threshold for {ticker} should be a float"


def test_mock_yfinance_with_data_fixture(mock_yfinance_with_data: MagicMock) -> None:
    """
    Test that mock_yfinance_with_data fixture provides data creation function.

    Args:
        mock_yfinance_with_data: The advanced mock yfinance fixture.
    """
    assert hasattr(
        mock_yfinance_with_data, "create_ticker_data"
    ), "Should have create_ticker_data function"

    # Test the data creation function
    custom_data: pd.DataFrame = mock_yfinance_with_data.create_ticker_data(
        high=200.0, low=150.0, open_price=160.0, close=180.0, volume=5000000, periods=10
    )

    assert isinstance(custom_data, pd.DataFrame), "Should return a DataFrame"
    assert len(custom_data) == 10, "Should have 10 data points"
    assert custom_data["High"].iloc[0] == 200.0, "High should match specified value"
    assert custom_data["Low"].iloc[0] == 150.0, "Low should match specified value"
    assert custom_data["Open"].iloc[0] == 160.0, "Open should match specified value"
    assert custom_data["Close"].iloc[0] == 180.0, "Close should match specified value"
    assert (
        custom_data["Volume"].iloc[0] == 5000000
    ), "Volume should match specified value"


def test_fixtures_work_together(
    client: TestClient,
    mock_yfinance: MagicMock,
    sample_ticker_data: Dict[str, Dict[str, float]],
) -> None:
    """
    Test that multiple fixtures can be used together in a single test.

    This verifies that fixtures don't conflict and can be composed.

    Args:
        client: The authenticated test client fixture.
        mock_yfinance: The mocked yfinance.Ticker fixture.
        sample_ticker_data: The sample ticker data fixture.
    """
    # All fixtures should be available
    assert client is not None, "Client fixture should be available"
    assert mock_yfinance is not None, "Mock yfinance fixture should be available"
    assert sample_ticker_data is not None, "Sample data fixture should be available"

    # Verify yfinance mock is active
    ticker = yfinance.Ticker("AAPL")
    data: pd.DataFrame = ticker.history(period="1d", interval="1h")
    assert not data.empty, "Mock should return data"

    # Verify client has auth header
    assert "X-API-Key" in client.headers, "Client should be authenticated"

    # Verify sample data is usable
    assert len(sample_ticker_data) > 0, "Sample data should be available"

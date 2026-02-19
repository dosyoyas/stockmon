"""
StockMon API - Main Application Unit Tests.

This module tests the FastAPI application endpoints including /check-alerts,
/health, and market open logic. Tests use mocks to avoid real API calls.
"""

# pylint: disable=W0621,C0415

from datetime import datetime, timezone
from typing import Dict, Generator
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
import pytz
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.main import is_market_open


class TestIsMarketOpen:
    """Test the market open detection logic."""

    def test_market_open_tuesday_afternoon(self) -> None:
        """Test market is open on Tuesday at 2:00 PM ET."""
        eastern: pytz.BaseTzInfo = pytz.timezone("US/Eastern")
        # Tuesday, February 6, 2024 at 2:00 PM ET
        dt: datetime = eastern.localize(datetime(2024, 2, 6, 14, 0, 0))
        assert is_market_open(dt) is True

    def test_market_closed_saturday(self) -> None:
        """Test market is closed on Saturday."""
        eastern: pytz.BaseTzInfo = pytz.timezone("US/Eastern")
        # Saturday, February 10, 2024 at 2:00 PM ET
        dt: datetime = eastern.localize(datetime(2024, 2, 10, 14, 0, 0))
        assert is_market_open(dt) is False

    def test_market_closed_sunday(self) -> None:
        """Test market is closed on Sunday."""
        eastern: pytz.BaseTzInfo = pytz.timezone("US/Eastern")
        # Sunday, February 11, 2024 at 2:00 PM ET
        dt: datetime = eastern.localize(datetime(2024, 2, 11, 14, 0, 0))
        assert is_market_open(dt) is False

    def test_market_closed_before_930am(self) -> None:
        """Test market is closed before 9:30 AM ET."""
        eastern: pytz.BaseTzInfo = pytz.timezone("US/Eastern")
        # Tuesday, February 6, 2024 at 9:00 AM ET
        dt: datetime = eastern.localize(datetime(2024, 2, 6, 9, 0, 0))
        assert is_market_open(dt) is False

    def test_market_open_at_930am(self) -> None:
        """Test market is open at exactly 9:30 AM ET."""
        eastern: pytz.BaseTzInfo = pytz.timezone("US/Eastern")
        # Tuesday, February 6, 2024 at 9:30 AM ET
        dt: datetime = eastern.localize(datetime(2024, 2, 6, 9, 30, 0))
        assert is_market_open(dt) is True

    def test_market_open_at_929am(self) -> None:
        """Test market is closed at 9:29 AM ET (before opening)."""
        eastern: pytz.BaseTzInfo = pytz.timezone("US/Eastern")
        # Tuesday, February 6, 2024 at 9:29 AM ET
        dt: datetime = eastern.localize(datetime(2024, 2, 6, 9, 29, 0))
        assert is_market_open(dt) is False

    def test_market_open_at_359pm(self) -> None:
        """Test market is open at 3:59 PM ET (before closing)."""
        eastern: pytz.BaseTzInfo = pytz.timezone("US/Eastern")
        # Tuesday, February 6, 2024 at 3:59 PM ET
        dt: datetime = eastern.localize(datetime(2024, 2, 6, 15, 59, 0))
        assert is_market_open(dt) is True

    def test_market_closed_at_4pm(self) -> None:
        """Test market is closed at exactly 4:00 PM ET."""
        eastern: pytz.BaseTzInfo = pytz.timezone("US/Eastern")
        # Tuesday, February 6, 2024 at 4:00 PM ET
        dt: datetime = eastern.localize(datetime(2024, 2, 6, 16, 0, 0))
        assert is_market_open(dt) is False

    def test_market_closed_after_4pm(self) -> None:
        """Test market is closed after 4:00 PM ET."""
        eastern: pytz.BaseTzInfo = pytz.timezone("US/Eastern")
        # Tuesday, February 6, 2024 at 5:00 PM ET
        dt: datetime = eastern.localize(datetime(2024, 2, 6, 17, 0, 0))
        assert is_market_open(dt) is False

    def test_market_open_monday(self) -> None:
        """Test market is open on Monday during trading hours."""
        eastern: pytz.BaseTzInfo = pytz.timezone("US/Eastern")
        # Monday, February 5, 2024 at 2:00 PM ET
        dt: datetime = eastern.localize(datetime(2024, 2, 5, 14, 0, 0))
        assert is_market_open(dt) is True

    def test_market_open_friday(self) -> None:
        """Test market is open on Friday during trading hours."""
        eastern: pytz.BaseTzInfo = pytz.timezone("US/Eastern")
        # Friday, February 9, 2024 at 2:00 PM ET
        dt: datetime = eastern.localize(datetime(2024, 2, 9, 14, 0, 0))
        assert is_market_open(dt) is True

    def test_timezone_conversion_from_utc(self) -> None:
        """Test that UTC times are correctly converted to ET."""
        # 7:00 PM UTC = 2:00 PM ET (during EST, UTC-5)
        # Tuesday, February 6, 2024 at 7:00 PM UTC
        dt: datetime = datetime(2024, 2, 6, 19, 0, 0, tzinfo=timezone.utc)
        assert is_market_open(dt) is True


class TestHealthEndpoint:
    """Test the /health endpoint."""

    @pytest.fixture
    def client(self, app: FastAPI) -> TestClient:
        """
        Create a test client without authentication.

        Args:
            app: The FastAPI application instance.

        Returns:
            TestClient: A test client.
        """
        return TestClient(app)

    def test_health_endpoint_returns_ok(self, client: TestClient) -> None:
        """Test /health endpoint returns ok status."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_health_endpoint_no_auth_required(self, client: TestClient) -> None:
        """Test /health endpoint does not require authentication."""
        # Request without X-API-Key header should succeed
        response = client.get("/health")
        assert response.status_code == 200


class TestRootEndpoint:
    """Test the / endpoint."""

    def test_root_endpoint_returns_api_info(self, client_no_auth: TestClient) -> None:
        """Test / endpoint returns API information."""
        response = client_no_auth.get("/")
        assert response.status_code == 200
        json_data: Dict[str, str] = response.json()
        assert "name" in json_data
        assert "version" in json_data
        assert "description" in json_data
        assert json_data["name"] == "StockMon API"


class TestCheckAlertsAuthentication:
    """Test authentication for /check-alerts endpoint."""

    def test_check_alerts_requires_authentication(
        self, client_no_auth: TestClient
    ) -> None:
        """Test /check-alerts endpoint requires authentication."""
        response = client_no_auth.post(
            "/check-alerts",
            json={"AAPL": {"buy": 170.0}},
        )
        assert response.status_code == 401

    def test_check_alerts_accepts_valid_api_key(self, client: TestClient) -> None:
        """Test /check-alerts endpoint accepts valid API key."""
        # Mock yfinance to avoid real API calls
        with patch("app.services.stock.yfinance.Ticker") as mock_ticker_class:
            mock_ticker: MagicMock = MagicMock()
            mock_ticker.history.return_value = pd.DataFrame(
                {
                    "Low": [168.0],
                    "High": [175.0],
                    "Close": [172.0],
                }
            )
            mock_ticker_class.return_value = mock_ticker

            response = client.post(
                "/check-alerts",
                json={"AAPL": {"buy": 170.0}},
            )
            # Should not be 401 (authentication should pass)
            assert response.status_code != 401


class TestCheckAlertsAlertLogic:
    """Test alert generation logic for /check-alerts endpoint."""

    @pytest.fixture
    def mock_yfinance_data(self) -> Generator[MagicMock, None, None]:
        """
        Mock yfinance.Ticker to return controlled test data.

        Yields:
            MagicMock: A mocked Ticker class.
        """
        with patch("app.services.stock.yfinance.Ticker") as mock_ticker_class:
            yield mock_ticker_class

    def test_buy_alert_triggered_when_min_below_threshold(
        self, client: TestClient, mock_yfinance_data: MagicMock
    ) -> None:
        """Test buy alert is triggered when min price is at or below buy threshold."""
        # Configure mock to return data where min=168.0, max=175.0, current=172.0
        mock_ticker: MagicMock = MagicMock()
        mock_ticker.history.return_value = pd.DataFrame(
            {
                "Low": [168.0, 169.0],
                "High": [175.0, 176.0],
                "Close": [172.0, 173.0],
            }
        )
        mock_yfinance_data.return_value = mock_ticker

        response = client.post(
            "/check-alerts",
            json={"AAPL": {"buy": 170.0}},  # Buy threshold = 170, min = 168
        )

        assert response.status_code == 200
        data: Dict = response.json()
        assert len(data["alerts"]) == 1
        alert: Dict = data["alerts"][0]
        assert alert["ticker"] == "AAPL"
        assert alert["type"] == "buy"
        assert alert["threshold"] == 170.0
        assert alert["reached"] == 168.0
        assert alert["current"] == 173.0

    def test_sell_alert_triggered_when_max_above_threshold(
        self, client: TestClient, mock_yfinance_data: MagicMock
    ) -> None:
        """Test sell alert is triggered when max price is at or above sell threshold."""
        # Configure mock to return data where min=168.0, max=195.0, current=172.0
        mock_ticker: MagicMock = MagicMock()
        mock_ticker.history.return_value = pd.DataFrame(
            {
                "Low": [168.0, 169.0],
                "High": [195.0, 196.0],
                "Close": [172.0, 173.0],
            }
        )
        mock_yfinance_data.return_value = mock_ticker

        response = client.post(
            "/check-alerts",
            json={"AAPL": {"sell": 190.0}},  # Sell threshold = 190, max = 196
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["alerts"]) == 1
        alert = data["alerts"][0]
        assert alert["ticker"] == "AAPL"
        assert alert["type"] == "sell"
        assert alert["threshold"] == 190.0
        assert alert["reached"] == 196.0

    def test_both_alerts_triggered_when_highly_volatile(
        self, client: TestClient, mock_yfinance_data: MagicMock
    ) -> None:
        """Test both buy and sell alerts are triggered for highly volatile ticker."""
        # Configure mock to return data where min=165.0, max=195.0, current=180.0
        mock_ticker: MagicMock = MagicMock()
        mock_ticker.history.return_value = pd.DataFrame(
            {
                "Low": [165.0, 166.0],
                "High": [195.0, 196.0],
                "Close": [180.0, 181.0],
            }
        )
        mock_yfinance_data.return_value = mock_ticker

        response = client.post(
            "/check-alerts",
            json={"AAPL": {"buy": 170.0, "sell": 190.0}},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["alerts"]) == 2
        # Should have both buy and sell alerts
        alert_types: list[str] = [alert["type"] for alert in data["alerts"]]
        assert "buy" in alert_types
        assert "sell" in alert_types

    def test_no_alert_when_thresholds_not_breached(
        self, client: TestClient, mock_yfinance_data: MagicMock
    ) -> None:
        """Test no alerts when thresholds are not breached."""
        # Configure mock to return data where min=170.0, max=175.0, current=172.0
        mock_ticker: MagicMock = MagicMock()
        mock_ticker.history.return_value = pd.DataFrame(
            {
                "Low": [170.0, 171.0],
                "High": [175.0, 176.0],
                "Close": [172.0, 173.0],
            }
        )
        mock_yfinance_data.return_value = mock_ticker

        response = client.post(
            "/check-alerts",
            json={"AAPL": {"buy": 160.0, "sell": 190.0}},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["alerts"]) == 0
        assert len(data["errors"]) == 0


class TestCheckAlertsErrorHandling:
    """Test error handling for /check-alerts endpoint."""

    @pytest.fixture
    def mock_yfinance_data(self) -> Generator[MagicMock, None, None]:
        """
        Mock yfinance.Ticker to return controlled test data.

        Yields:
            MagicMock: A mocked Ticker class.
        """
        with patch("app.services.stock.yfinance.Ticker") as mock_ticker_class:
            yield mock_ticker_class

    def test_invalid_ticker_returns_error(
        self, client: TestClient, mock_yfinance_data: MagicMock
    ) -> None:
        """Test invalid ticker is handled gracefully and returns error."""
        # Configure mock to return empty DataFrame (invalid ticker)
        mock_ticker: MagicMock = MagicMock()
        mock_ticker.history.return_value = pd.DataFrame()
        mock_yfinance_data.return_value = mock_ticker

        response = client.post(
            "/check-alerts",
            json={"INVALID": {"buy": 100.0}},
        )

        assert response.status_code == 200
        data: Dict = response.json()
        assert len(data["errors"]) == 1
        error: Dict = data["errors"][0]
        assert error["ticker"] == "INVALID"
        assert "Invalid ticker" in error["error"]

    def test_partial_failure_continues_processing(
        self, client: TestClient, mock_yfinance_data: MagicMock
    ) -> None:
        """Test partial failure continues processing other tickers."""

        def ticker_side_effect(symbol: str) -> MagicMock:
            """Return different data based on ticker symbol."""
            mock_ticker: MagicMock = MagicMock()
            if symbol == "INVALID":
                # Return empty DataFrame for invalid ticker
                mock_ticker.history.return_value = pd.DataFrame()
            else:
                # Return valid data for AAPL
                mock_ticker.history.return_value = pd.DataFrame(
                    {
                        "Low": [168.0, 169.0],
                        "High": [175.0, 176.0],
                        "Close": [172.0, 173.0],
                    }
                )
            return mock_ticker

        mock_yfinance_data.side_effect = ticker_side_effect

        response = client.post(
            "/check-alerts",
            json={
                "AAPL": {"buy": 170.0},
                "INVALID": {"buy": 100.0},
            },
        )

        assert response.status_code == 200
        data = response.json()
        # Should have 1 alert from AAPL and 1 error from INVALID
        assert len(data["alerts"]) == 1
        assert len(data["errors"]) == 1
        assert data["alerts"][0]["ticker"] == "AAPL"
        assert data["errors"][0]["ticker"] == "INVALID"


class TestCheckAlertsResponseStructure:
    """Test response structure for /check-alerts endpoint."""

    @pytest.fixture
    def mock_yfinance_data(self) -> Generator[MagicMock, None, None]:
        """
        Mock yfinance.Ticker to return controlled test data.

        Yields:
            MagicMock: A mocked Ticker class.
        """
        with patch("app.services.stock.yfinance.Ticker") as mock_ticker_class:
            mock_ticker: MagicMock = MagicMock()
            mock_ticker.history.return_value = pd.DataFrame(
                {
                    "Low": [170.0],
                    "High": [175.0],
                    "Close": [172.0],
                }
            )
            mock_ticker_class.return_value = mock_ticker
            yield mock_ticker_class

    def test_response_contains_required_fields(
        self, client: TestClient, mock_yfinance_data: MagicMock
    ) -> None:
        """Test response contains all required fields."""
        _ = mock_yfinance_data  # Required for fixture activation
        response = client.post(
            "/check-alerts",
            json={"AAPL": {"buy": 160.0}},
        )

        assert response.status_code == 200
        data: Dict = response.json()
        assert "alerts" in data
        assert "errors" in data
        assert "market_open" in data
        assert "service_degraded" in data
        assert "checked_at" in data

    def test_checked_at_is_valid_iso8601(
        self, client: TestClient, mock_yfinance_data: MagicMock
    ) -> None:
        """Test checked_at is a valid ISO 8601 timestamp."""
        _ = mock_yfinance_data  # Required for fixture activation
        response = client.post(
            "/check-alerts",
            json={"AAPL": {"buy": 160.0}},
        )

        assert response.status_code == 200
        data: Dict = response.json()
        # Should be able to parse as datetime
        checked_at_str: str = data["checked_at"]
        checked_at: datetime = datetime.fromisoformat(
            checked_at_str.replace("Z", "+00:00")
        )
        assert isinstance(checked_at, datetime)

    def test_service_degraded_false_when_some_succeed(
        self, client: TestClient, mock_yfinance_data: MagicMock
    ) -> None:
        """Test service_degraded is false when at least one ticker succeeds."""
        _ = mock_yfinance_data  # Required for fixture activation
        response = client.post(
            "/check-alerts",
            json={"AAPL": {"buy": 160.0}},
        )

        assert response.status_code == 200
        data: Dict = response.json()
        assert data["service_degraded"] is False

    def test_service_degraded_true_when_all_fail(
        self, client: TestClient, mock_yfinance_data: MagicMock
    ) -> None:
        """Test service_degraded is true when all tickers fail."""
        # Configure mock to always return empty DataFrame
        mock_ticker: MagicMock = MagicMock()
        mock_ticker.history.return_value = pd.DataFrame()
        mock_yfinance_data.return_value = mock_ticker

        response = client.post(
            "/check-alerts",
            json={
                "AAPL": {"buy": 160.0},
                "MSFT": {"buy": 400.0},
            },
        )

        assert response.status_code == 200
        data: Dict = response.json()
        assert data["service_degraded"] is True
        assert len(data["errors"]) == 2
        assert len(data["alerts"]) == 0


class TestCheckAlertsValidation:
    """Test request validation for /check-alerts endpoint."""

    def test_max_20_tickers_accepted(self, client: TestClient) -> None:
        """Test that exactly 20 tickers are accepted."""
        # Create request with exactly 20 tickers
        tickers: Dict[str, Dict[str, float]] = {
            f"TICK{i:02d}": {"buy": 100.0} for i in range(20)
        }

        with patch("app.services.stock.yfinance.Ticker") as mock_ticker_class:
            mock_ticker: MagicMock = MagicMock()
            mock_ticker.history.return_value = pd.DataFrame(
                {
                    "Low": [100.0],
                    "High": [110.0],
                    "Close": [105.0],
                }
            )
            mock_ticker_class.return_value = mock_ticker

            response = client.post("/check-alerts", json=tickers)
            assert response.status_code == 200

    def test_more_than_20_tickers_rejected(self, client: TestClient) -> None:
        """Test that more than 20 tickers are rejected with 422."""
        # Create request with 21 tickers
        tickers: Dict[str, Dict[str, float]] = {
            f"TICK{i:02d}": {"buy": 100.0} for i in range(21)
        }

        response = client.post("/check-alerts", json=tickers)
        assert response.status_code == 422

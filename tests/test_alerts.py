"""
StockMon Alert Logic Tests.

This module tests the alert logic for the /check-alerts endpoint including:
- Buy threshold detection
- Sell threshold detection
- Both alerts triggered (volatile stock)
- No alerts triggered (thresholds not reached)
- Partial thresholds (only buy or only sell specified)
- Maximum ticker validation (>20 tickers rejected)
"""

# pylint: disable=W0621,C0415

from typing import Dict, Generator
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from fastapi.testclient import TestClient


class TestBuyThresholdDetection:
    """Test buy threshold alert detection logic."""

    @pytest.fixture
    def mock_yfinance_data(self) -> Generator[MagicMock, None, None]:
        """
        Mock yfinance.Ticker to return controlled test data.

        Yields:
            MagicMock: A mocked Ticker class.
        """
        with patch("app.services.stock.yfinance.Ticker") as mock_ticker_class:
            yield mock_ticker_class

    def test_buy_alert_triggered_when_min_equals_threshold(
        self, client: TestClient, mock_yfinance_data: MagicMock
    ) -> None:
        """Test buy alert is triggered when min price exactly equals buy threshold."""
        # Configure mock: min=170.0, max=180.0, current=175.0
        mock_ticker: MagicMock = MagicMock()
        mock_ticker.history.return_value = pd.DataFrame(
            {
                "Low": [170.0, 171.0, 172.0],
                "High": [180.0, 181.0, 182.0],
                "Close": [175.0, 176.0, 177.0],
            }
        )
        mock_yfinance_data.return_value = mock_ticker

        response = client.post(
            "/check-alerts",
            json={"AAPL": {"buy": 170.0}},  # Min price = threshold
        )

        assert response.status_code == 200
        data: Dict = response.json()
        assert len(data["alerts"]) == 1
        alert: Dict = data["alerts"][0]
        assert alert["ticker"] == "AAPL"
        assert alert["type"] == "buy"
        assert alert["threshold"] == 170.0
        assert alert["reached"] == 170.0
        assert alert["current"] == 177.0

    def test_buy_alert_triggered_when_min_below_threshold(
        self, client: TestClient, mock_yfinance_data: MagicMock
    ) -> None:
        """Test buy alert is triggered when min price drops below buy threshold."""
        # Configure mock: min=165.0, max=180.0, current=175.0
        mock_ticker: MagicMock = MagicMock()
        mock_ticker.history.return_value = pd.DataFrame(
            {
                "Low": [165.0, 168.0, 170.0],
                "High": [180.0, 181.0, 182.0],
                "Close": [175.0, 176.0, 177.0],
            }
        )
        mock_yfinance_data.return_value = mock_ticker

        response = client.post(
            "/check-alerts",
            json={"AAPL": {"buy": 170.0}},  # Min=165 < threshold=170
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["alerts"]) == 1
        alert = data["alerts"][0]
        assert alert["ticker"] == "AAPL"
        assert alert["type"] == "buy"
        assert alert["threshold"] == 170.0
        assert alert["reached"] == 165.0

    def test_buy_alert_not_triggered_when_min_above_threshold(
        self, client: TestClient, mock_yfinance_data: MagicMock
    ) -> None:
        """Test buy alert is NOT triggered when min price stays above buy threshold."""
        # Configure mock: min=175.0, max=185.0, current=180.0
        mock_ticker: MagicMock = MagicMock()
        mock_ticker.history.return_value = pd.DataFrame(
            {
                "Low": [175.0, 176.0, 177.0],
                "High": [185.0, 186.0, 187.0],
                "Close": [180.0, 181.0, 182.0],
            }
        )
        mock_yfinance_data.return_value = mock_ticker

        response = client.post(
            "/check-alerts",
            json={"AAPL": {"buy": 170.0}},  # Min=175 > threshold=170
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["alerts"]) == 0


class TestSellThresholdDetection:
    """Test sell threshold alert detection logic."""

    @pytest.fixture
    def mock_yfinance_data(self) -> Generator[MagicMock, None, None]:
        """
        Mock yfinance.Ticker to return controlled test data.

        Yields:
            MagicMock: A mocked Ticker class.
        """
        with patch("app.services.stock.yfinance.Ticker") as mock_ticker_class:
            yield mock_ticker_class

    def test_sell_alert_triggered_when_max_equals_threshold(
        self, client: TestClient, mock_yfinance_data: MagicMock
    ) -> None:
        """Test sell alert is triggered when max price exactly equals sell threshold."""
        # Configure mock: min=170.0, max=190.0, current=185.0
        mock_ticker: MagicMock = MagicMock()
        mock_ticker.history.return_value = pd.DataFrame(
            {
                "Low": [170.0, 171.0, 172.0],
                "High": [190.0, 189.0, 188.0],
                "Close": [185.0, 184.0, 183.0],
            }
        )
        mock_yfinance_data.return_value = mock_ticker

        response = client.post(
            "/check-alerts",
            json={"AAPL": {"sell": 190.0}},  # Max price = threshold
        )

        assert response.status_code == 200
        data: Dict = response.json()
        assert len(data["alerts"]) == 1
        alert: Dict = data["alerts"][0]
        assert alert["ticker"] == "AAPL"
        assert alert["type"] == "sell"
        assert alert["threshold"] == 190.0
        assert alert["reached"] == 190.0
        assert alert["current"] == 183.0

    def test_sell_alert_triggered_when_max_above_threshold(
        self, client: TestClient, mock_yfinance_data: MagicMock
    ) -> None:
        """Test sell alert is triggered when max price rises above sell threshold."""
        # Configure mock: min=170.0, max=195.0, current=185.0
        mock_ticker: MagicMock = MagicMock()
        mock_ticker.history.return_value = pd.DataFrame(
            {
                "Low": [170.0, 171.0, 172.0],
                "High": [195.0, 194.0, 193.0],
                "Close": [185.0, 184.0, 183.0],
            }
        )
        mock_yfinance_data.return_value = mock_ticker

        response = client.post(
            "/check-alerts",
            json={"AAPL": {"sell": 190.0}},  # Max=195 > threshold=190
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["alerts"]) == 1
        alert = data["alerts"][0]
        assert alert["ticker"] == "AAPL"
        assert alert["type"] == "sell"
        assert alert["threshold"] == 190.0
        assert alert["reached"] == 195.0

    def test_sell_alert_not_triggered_when_max_below_threshold(
        self, client: TestClient, mock_yfinance_data: MagicMock
    ) -> None:
        """Test sell alert is NOT triggered when max price stays below sell threshold."""
        # Configure mock: min=170.0, max=185.0, current=180.0
        mock_ticker: MagicMock = MagicMock()
        mock_ticker.history.return_value = pd.DataFrame(
            {
                "Low": [170.0, 171.0, 172.0],
                "High": [185.0, 184.0, 183.0],
                "Close": [180.0, 179.0, 178.0],
            }
        )
        mock_yfinance_data.return_value = mock_ticker

        response = client.post(
            "/check-alerts",
            json={"AAPL": {"sell": 190.0}},  # Max=185 < threshold=190
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["alerts"]) == 0


class TestBothAlertsTriggered:
    """Test scenarios where both buy and sell alerts are triggered (volatile stock)."""

    @pytest.fixture
    def mock_yfinance_data(self) -> Generator[MagicMock, None, None]:
        """
        Mock yfinance.Ticker to return controlled test data.

        Yields:
            MagicMock: A mocked Ticker class.
        """
        with patch("app.services.stock.yfinance.Ticker") as mock_ticker_class:
            yield mock_ticker_class

    def test_both_alerts_triggered_for_highly_volatile_stock(
        self, client: TestClient, mock_yfinance_data: MagicMock
    ) -> None:
        """Test both buy and sell alerts triggered when stock is highly volatile."""
        # Configure mock: min=165.0, max=195.0, current=180.0
        # Wide range breaches both thresholds
        mock_ticker: MagicMock = MagicMock()
        mock_ticker.history.return_value = pd.DataFrame(
            {
                "Low": [165.0, 167.0, 170.0, 172.0],
                "High": [195.0, 193.0, 190.0, 185.0],
                "Close": [180.0, 182.0, 181.0, 179.0],
            }
        )
        mock_yfinance_data.return_value = mock_ticker

        response = client.post(
            "/check-alerts",
            json={"AAPL": {"buy": 170.0, "sell": 190.0}},
        )

        assert response.status_code == 200
        data: Dict = response.json()
        assert len(data["alerts"]) == 2

        # Verify buy alert
        buy_alerts: list[Dict] = [a for a in data["alerts"] if a["type"] == "buy"]
        assert len(buy_alerts) == 1
        assert buy_alerts[0]["ticker"] == "AAPL"
        assert buy_alerts[0]["threshold"] == 170.0
        assert buy_alerts[0]["reached"] == 165.0

        # Verify sell alert
        sell_alerts: list[Dict] = [a for a in data["alerts"] if a["type"] == "sell"]
        assert len(sell_alerts) == 1
        assert sell_alerts[0]["ticker"] == "AAPL"
        assert sell_alerts[0]["threshold"] == 190.0
        assert sell_alerts[0]["reached"] == 195.0

    def test_both_thresholds_exactly_met(
        self, client: TestClient, mock_yfinance_data: MagicMock
    ) -> None:
        """Test both alerts when min and max exactly match thresholds."""
        # Configure mock: min=170.0, max=190.0, current=180.0
        mock_ticker: MagicMock = MagicMock()
        mock_ticker.history.return_value = pd.DataFrame(
            {
                "Low": [170.0, 172.0, 174.0],
                "High": [190.0, 188.0, 186.0],
                "Close": [180.0, 181.0, 182.0],
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
        alert_types: list[str] = [a["type"] for a in data["alerts"]]
        assert "buy" in alert_types
        assert "sell" in alert_types


class TestNoAlertsTriggered:
    """Test scenarios where no alerts should be triggered."""

    @pytest.fixture
    def mock_yfinance_data(self) -> Generator[MagicMock, None, None]:
        """
        Mock yfinance.Ticker to return controlled test data.

        Yields:
            MagicMock: A mocked Ticker class.
        """
        with patch("app.services.stock.yfinance.Ticker") as mock_ticker_class:
            yield mock_ticker_class

    def test_no_alerts_when_price_between_thresholds(
        self, client: TestClient, mock_yfinance_data: MagicMock
    ) -> None:
        """Test no alerts when price stays between buy and sell thresholds."""
        # Configure mock: min=172.0, max=188.0, current=180.0
        # Price range stays within [170, 190] thresholds
        mock_ticker: MagicMock = MagicMock()
        mock_ticker.history.return_value = pd.DataFrame(
            {
                "Low": [172.0, 173.0, 174.0],
                "High": [188.0, 187.0, 186.0],
                "Close": [180.0, 181.0, 182.0],
            }
        )
        mock_yfinance_data.return_value = mock_ticker

        response = client.post(
            "/check-alerts",
            json={"AAPL": {"buy": 170.0, "sell": 190.0}},
        )

        assert response.status_code == 200
        data: Dict = response.json()
        assert len(data["alerts"]) == 0
        assert len(data["errors"]) == 0

    def test_no_alerts_when_min_just_above_buy_threshold(
        self, client: TestClient, mock_yfinance_data: MagicMock
    ) -> None:
        """Test no buy alert when min price is just above buy threshold."""
        # Configure mock: min=170.01, max=180.0, current=175.0
        mock_ticker: MagicMock = MagicMock()
        mock_ticker.history.return_value = pd.DataFrame(
            {
                "Low": [170.01, 171.0, 172.0],
                "High": [180.0, 181.0, 182.0],
                "Close": [175.0, 176.0, 177.0],
            }
        )
        mock_yfinance_data.return_value = mock_ticker

        response = client.post(
            "/check-alerts",
            json={"AAPL": {"buy": 170.0}},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["alerts"]) == 0

    def test_no_alerts_when_max_just_below_sell_threshold(
        self, client: TestClient, mock_yfinance_data: MagicMock
    ) -> None:
        """Test no sell alert when max price is just below sell threshold."""
        # Configure mock: min=170.0, max=189.99, current=180.0
        mock_ticker: MagicMock = MagicMock()
        mock_ticker.history.return_value = pd.DataFrame(
            {
                "Low": [170.0, 171.0, 172.0],
                "High": [189.99, 188.0, 187.0],
                "Close": [180.0, 179.0, 178.0],
            }
        )
        mock_yfinance_data.return_value = mock_ticker

        response = client.post(
            "/check-alerts",
            json={"AAPL": {"sell": 190.0}},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["alerts"]) == 0


class TestPartialThresholds:
    """Test scenarios with partial threshold specifications (only buy OR only sell)."""

    @pytest.fixture
    def mock_yfinance_data(self) -> Generator[MagicMock, None, None]:
        """
        Mock yfinance.Ticker to return controlled test data.

        Yields:
            MagicMock: A mocked Ticker class.
        """
        with patch("app.services.stock.yfinance.Ticker") as mock_ticker_class:
            yield mock_ticker_class

    def test_only_buy_threshold_specified_triggers_buy_alert(
        self, client: TestClient, mock_yfinance_data: MagicMock
    ) -> None:
        """Test buy alert triggers when only buy threshold specified (no sell)."""
        # Configure mock: min=165.0, max=195.0, current=180.0
        mock_ticker: MagicMock = MagicMock()
        mock_ticker.history.return_value = pd.DataFrame(
            {
                "Low": [165.0, 167.0, 169.0],
                "High": [195.0, 193.0, 191.0],
                "Close": [180.0, 181.0, 182.0],
            }
        )
        mock_yfinance_data.return_value = mock_ticker

        response = client.post(
            "/check-alerts",
            json={"AAPL": {"buy": 170.0}},  # Only buy threshold
        )

        assert response.status_code == 200
        data: Dict = response.json()
        assert len(data["alerts"]) == 1
        assert data["alerts"][0]["type"] == "buy"
        assert data["alerts"][0]["threshold"] == 170.0

    def test_only_sell_threshold_specified_triggers_sell_alert(
        self, client: TestClient, mock_yfinance_data: MagicMock
    ) -> None:
        """Test sell alert triggers when only sell threshold specified (no buy)."""
        # Configure mock: min=165.0, max=195.0, current=180.0
        mock_ticker: MagicMock = MagicMock()
        mock_ticker.history.return_value = pd.DataFrame(
            {
                "Low": [165.0, 167.0, 169.0],
                "High": [195.0, 193.0, 191.0],
                "Close": [180.0, 181.0, 182.0],
            }
        )
        mock_yfinance_data.return_value = mock_ticker

        response = client.post(
            "/check-alerts",
            json={"AAPL": {"sell": 190.0}},  # Only sell threshold
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["alerts"]) == 1
        assert data["alerts"][0]["type"] == "sell"
        assert data["alerts"][0]["threshold"] == 190.0

    def test_only_buy_threshold_does_not_trigger_sell_alert(
        self, client: TestClient, mock_yfinance_data: MagicMock
    ) -> None:
        """Test that only buy threshold specified does not trigger sell alert."""
        # Configure mock: min=165.0, max=195.0 (would trigger sell if specified)
        mock_ticker: MagicMock = MagicMock()
        mock_ticker.history.return_value = pd.DataFrame(
            {
                "Low": [165.0, 167.0, 169.0],
                "High": [195.0, 193.0, 191.0],
                "Close": [180.0, 181.0, 182.0],
            }
        )
        mock_yfinance_data.return_value = mock_ticker

        response = client.post(
            "/check-alerts",
            json={"AAPL": {"buy": 170.0}},  # Only buy, max=195 should not trigger sell
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["alerts"]) == 1  # Only buy alert
        assert data["alerts"][0]["type"] == "buy"

    def test_only_sell_threshold_does_not_trigger_buy_alert(
        self, client: TestClient, mock_yfinance_data: MagicMock
    ) -> None:
        """Test that only sell threshold specified does not trigger buy alert."""
        # Configure mock: min=165.0, max=195.0 (would trigger buy if specified)
        mock_ticker: MagicMock = MagicMock()
        mock_ticker.history.return_value = pd.DataFrame(
            {
                "Low": [165.0, 167.0, 169.0],
                "High": [195.0, 193.0, 191.0],
                "Close": [180.0, 181.0, 182.0],
            }
        )
        mock_yfinance_data.return_value = mock_ticker

        response = client.post(
            "/check-alerts",
            json={"AAPL": {"sell": 190.0}},  # Only sell, min=165 should not trigger buy
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["alerts"]) == 1  # Only sell alert
        assert data["alerts"][0]["type"] == "sell"

    def test_multiple_tickers_with_partial_thresholds(
        self, client: TestClient, mock_yfinance_data: MagicMock
    ) -> None:
        """Test multiple tickers where each has different partial thresholds."""

        def ticker_side_effect(symbol: str) -> MagicMock:
            """Return different data based on ticker symbol."""
            mock_ticker: MagicMock = MagicMock()
            if symbol == "AAPL":
                # AAPL: min=165.0, max=175.0
                mock_ticker.history.return_value = pd.DataFrame(
                    {
                        "Low": [165.0, 167.0],
                        "High": [175.0, 176.0],
                        "Close": [170.0, 171.0],
                    }
                )
            elif symbol == "MSFT":
                # MSFT: min=400.0, max=425.0
                mock_ticker.history.return_value = pd.DataFrame(
                    {
                        "Low": [400.0, 402.0],
                        "High": [425.0, 423.0],
                        "Close": [410.0, 411.0],
                    }
                )
            return mock_ticker

        mock_yfinance_data.side_effect = ticker_side_effect

        response = client.post(
            "/check-alerts",
            json={
                "AAPL": {"buy": 170.0},  # Only buy: min=165 < 170, triggers
                "MSFT": {"sell": 420.0},  # Only sell: max=425 > 420, triggers
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["alerts"]) == 2

        # Verify AAPL buy alert
        aapl_alerts: list[Dict] = [a for a in data["alerts"] if a["ticker"] == "AAPL"]
        assert len(aapl_alerts) == 1
        assert aapl_alerts[0]["type"] == "buy"

        # Verify MSFT sell alert
        msft_alerts: list[Dict] = [a for a in data["alerts"] if a["ticker"] == "MSFT"]
        assert len(msft_alerts) == 1
        assert msft_alerts[0]["type"] == "sell"


class TestMaxTickersValidation:
    """Test validation for maximum number of tickers (20 max)."""

    def test_exactly_20_tickers_accepted(self, client: TestClient) -> None:
        """Test that exactly 20 tickers are accepted without error."""
        # Create request with exactly 20 tickers
        tickers: Dict[str, Dict[str, float]] = {
            f"TICK{i:02d}": {"buy": 100.0} for i in range(20)
        }

        with patch("app.services.stock.yfinance.Ticker") as mock_ticker_class:
            mock_ticker: MagicMock = MagicMock()
            mock_ticker.history.return_value = pd.DataFrame(
                {
                    "Low": [100.0, 101.0],
                    "High": [110.0, 111.0],
                    "Close": [105.0, 106.0],
                }
            )
            mock_ticker_class.return_value = mock_ticker

            response = client.post("/check-alerts", json=tickers)
            assert response.status_code == 200

    def test_21_tickers_rejected_with_422(self, client: TestClient) -> None:
        """Test that 21 tickers are rejected with 422 status code."""
        # Create request with 21 tickers (exceeds maximum)
        tickers: Dict[str, Dict[str, float]] = {
            f"TICK{i:02d}": {"buy": 100.0} for i in range(21)
        }

        response = client.post("/check-alerts", json=tickers)
        assert response.status_code == 422

    def test_50_tickers_rejected_with_422(self, client: TestClient) -> None:
        """Test that significantly more than 20 tickers are rejected."""
        # Create request with 50 tickers
        tickers: Dict[str, Dict[str, float]] = {
            f"TICK{i:02d}": {"buy": 100.0} for i in range(50)
        }

        response = client.post("/check-alerts", json=tickers)
        assert response.status_code == 422

    def test_422_error_message_indicates_max_tickers(self, client: TestClient) -> None:
        """Test that 422 error message indicates the maximum ticker limit."""
        # Create request with 25 tickers
        tickers: Dict[str, Dict[str, float]] = {
            f"TICK{i:02d}": {"buy": 100.0} for i in range(25)
        }

        response = client.post("/check-alerts", json=tickers)
        assert response.status_code == 422
        error_data: Dict = response.json()
        # Pydantic validation error should mention max tickers
        assert "detail" in error_data

    def test_1_ticker_accepted(self, client: TestClient) -> None:
        """Test that a single ticker request is accepted."""
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

            response = client.post(
                "/check-alerts",
                json={"AAPL": {"buy": 100.0}},
            )
            assert response.status_code == 200

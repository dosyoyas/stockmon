"""
StockMon Stock Service Integration Tests.

This module provides integration tests that verify the stock service works
correctly with real-world-like scenarios, including interaction with the
mocked YFinance API and edge cases.
"""

# pylint: disable=W0621,C0415,R0913

from typing import Any, Dict
from unittest.mock import MagicMock

import pandas as pd
import pytest

from app.services.stock import (InvalidTickerError, MarketClosedError,
                                StockDataTimeoutError, get_24h_range)


class TestStockServiceIntegration:
    """Integration test suite for stock service."""

    def test_multiple_tickers_sequential_calls(self, mock_yfinance: MagicMock) -> None:
        """
        Test that multiple sequential calls work correctly with different data.

        This simulates a real-world scenario where the /check-alerts endpoint
        calls get_24h_range for multiple tickers in sequence.

        Args:
            mock_yfinance: Mocked yfinance.Ticker class.
        """
        # Configure mock to return different data for each ticker
        mock_ticker_instance: MagicMock = mock_yfinance.return_value

        # Prepare data for three different tickers
        tickers_data: Dict[str, Dict[str, list[float]]] = {
            "AAPL": {
                "Open": [170.0, 171.0, 169.0],
                "High": [175.0, 176.0, 174.0],
                "Low": [165.0, 168.0, 166.0],
                "Close": [172.0, 173.0, 171.0],
                "Volume": [1000000, 1100000, 1050000],
            },
            "MSFT": {
                "Open": [400.0, 405.0, 402.0],
                "High": [410.0, 412.0, 408.0],
                "Low": [395.0, 398.0, 396.0],
                "Close": [405.0, 407.0, 404.0],
                "Volume": [2000000, 2100000, 2050000],
            },
            "GOOGL": {
                "Open": [140.0, 142.0, 141.0],
                "High": [145.0, 147.0, 146.0],
                "Low": [138.0, 140.0, 139.0],
                "Close": [143.0, 145.0, 144.0],
                "Volume": [3000000, 3100000, 3050000],
            },
        }

        # Set side_effect to return different data for each call
        mock_ticker_instance.history.side_effect = [
            pd.DataFrame(tickers_data["AAPL"]),
            pd.DataFrame(tickers_data["MSFT"]),
            pd.DataFrame(tickers_data["GOOGL"]),
        ]

        # Call for each ticker and verify results
        min_aapl, max_aapl, current_aapl = get_24h_range("AAPL")
        assert min_aapl == 165.0
        assert max_aapl == 176.0
        assert current_aapl == 171.0

        min_msft, max_msft, current_msft = get_24h_range("MSFT")
        assert min_msft == 395.0
        assert max_msft == 412.0
        assert current_msft == 404.0

        min_googl, max_googl, current_googl = get_24h_range("GOOGL")
        assert min_googl == 138.0
        assert max_googl == 147.0
        assert current_googl == 144.0

        # Verify all three tickers were called
        assert mock_yfinance.call_count == 3

    def test_partial_nan_data_filters_correctly(self, mock_yfinance: MagicMock) -> None:
        """
        Test that partial NaN data is filtered out correctly.

        In real scenarios, some data points may be NaN (pre-market hours,
        data gaps, etc.). The service should filter these out and calculate
        min/max from valid data only.

        Args:
            mock_yfinance: Mocked yfinance.Ticker class.
        """
        # Configure mock with some NaN values mixed with valid data
        data: Dict[str, list[Any]] = {
            "Open": [170.0, None, 169.0, 172.0],
            "High": [175.0, None, 174.0, 177.0],
            "Low": [165.0, None, 166.0, 170.0],
            "Close": [172.0, None, 171.0, 174.5],
            "Volume": [1000000, 0, 1050000, 1100000],
        }
        mock_ticker_instance: MagicMock = mock_yfinance.return_value
        mock_ticker_instance.history.return_value = pd.DataFrame(data)

        # Call the function
        min_price, max_price, current_price = get_24h_range("AAPL")

        # Verify results only include valid (non-NaN) data
        assert min_price == 165.0  # From first valid data point
        assert max_price == 177.0  # From last valid data point
        assert current_price == 174.5  # Last valid close

    def test_mixed_success_and_failure_independent(
        self, mock_yfinance: MagicMock
    ) -> None:
        """
        Test that failures for one ticker don't affect subsequent tickers.

        This verifies the endpoint behavior where some tickers may fail
        but others succeed.

        Args:
            mock_yfinance: Mocked yfinance.Ticker class.
        """
        mock_ticker_instance: MagicMock = mock_yfinance.return_value

        # First call succeeds
        valid_data: Dict[str, list[float]] = {
            "Open": [170.0],
            "High": [175.0],
            "Low": [165.0],
            "Close": [172.0],
            "Volume": [1000000],
        }
        # Second call fails (empty data)
        # Third call succeeds
        mock_ticker_instance.history.side_effect = [
            pd.DataFrame(valid_data),
            pd.DataFrame(),  # Invalid ticker
            pd.DataFrame(valid_data),
        ]

        # First call succeeds
        min_p1, max_p1, current_p1 = get_24h_range("AAPL")
        assert min_p1 == 165.0
        assert max_p1 == 175.0
        assert current_p1 == 172.0

        # Second call fails
        with pytest.raises(InvalidTickerError):
            get_24h_range("INVALID")

        # Third call still succeeds (failure didn't poison state)
        min_p3, max_p3, current_p3 = get_24h_range("MSFT")
        assert min_p3 == 165.0
        assert max_p3 == 175.0
        assert current_p3 == 172.0

    def test_realistic_24h_trading_data(self, mock_yfinance: MagicMock) -> None:
        """
        Test with realistic 24-hour trading data pattern.

        This simulates a full trading day with typical price movements,
        including opening gap, intraday volatility, and closing price.

        Args:
            mock_yfinance: Mocked yfinance.Ticker class.
        """
        # Simulate realistic 24h data: 24 hourly points
        # Pattern: opens at 170, rallies to 180, drops to 165, recovers to 175
        opens: list[float] = [170.0, 172.0, 175.0, 178.0, 180.0, 179.0] * 4
        highs: list[float] = [172.0, 175.0, 178.0, 180.0, 182.0, 181.0] * 4
        lows: list[float] = [168.0, 170.0, 173.0, 176.0, 178.0, 177.0] * 4
        closes: list[float] = [171.0, 174.0, 177.0, 179.0, 180.0, 179.5] * 4
        volumes: list[float] = [
            1000000.0,
            1200000.0,
            1500000.0,
            1800000.0,
            2000000.0,
            1700000.0,
        ] * 4

        data: Dict[str, list[float]] = {
            "Open": opens[:24],
            "High": highs[:24],
            "Low": lows[:24],
            "Close": closes[:24],
            "Volume": volumes[:24],
        }

        mock_ticker_instance: MagicMock = mock_yfinance.return_value
        mock_ticker_instance.history.return_value = pd.DataFrame(data)

        # Call the function
        min_price, max_price, current_price = get_24h_range("AAPL")

        # Verify results capture the full range
        assert min_price == 168.0  # Lowest low in the period
        assert max_price == 182.0  # Highest high in the period
        assert current_price == 179.5  # Last close

    def test_error_messages_include_ticker_info(self, mock_yfinance: MagicMock) -> None:
        """
        Test that all error messages include ticker information for debugging.

        Args:
            mock_yfinance: Mocked yfinance.Ticker class.
        """
        mock_ticker_instance: MagicMock = mock_yfinance.return_value

        # Test InvalidTickerError
        mock_ticker_instance.history.return_value = pd.DataFrame()
        with pytest.raises(InvalidTickerError) as exc_info:
            get_24h_range("BADTICKER")
        assert "BADTICKER" in str(exc_info.value)

        # Test MarketClosedError
        nan_data: Dict[str, list[Any]] = {
            "Open": [None, None],
            "High": [None, None],
            "Low": [None, None],
            "Close": [None, None],
            "Volume": [None, None],
        }
        mock_ticker_instance.history.return_value = pd.DataFrame(nan_data)
        with pytest.raises(MarketClosedError) as exc_info:
            get_24h_range("CLOSEDMARKET")
        assert "CLOSEDMARKET" in str(exc_info.value)

        # Test StockDataTimeoutError
        mock_ticker_instance.history.side_effect = TimeoutError("Connection timeout")
        with pytest.raises(StockDataTimeoutError) as exc_info:
            get_24h_range("TIMEOUT")
        assert "TIMEOUT" in str(exc_info.value)
        assert "timeout" in str(exc_info.value).lower()

    def test_handles_zero_volume_periods(self, mock_yfinance: MagicMock) -> None:
        """
        Test handling of periods with zero or very low volume.

        Args:
            mock_yfinance: Mocked yfinance.Ticker class.
        """
        # Data with zero volume in some periods (pre-market/after-hours)
        data: Dict[str, list[float]] = {
            "Open": [170.0, 170.0, 171.0],
            "High": [175.0, 175.0, 176.0],
            "Low": [165.0, 165.0, 166.0],
            "Close": [172.0, 172.0, 173.0],
            "Volume": [0, 1000000, 0],  # Low/zero volume
        }
        mock_ticker_instance: MagicMock = mock_yfinance.return_value
        mock_ticker_instance.history.return_value = pd.DataFrame(data)

        # Should still calculate min/max correctly
        min_price, max_price, current_price = get_24h_range("AAPL")

        assert min_price == 165.0
        assert max_price == 176.0
        assert current_price == 173.0

    def test_single_hour_of_data(self, mock_yfinance: MagicMock) -> None:
        """
        Test handling when only one hour of data is available.

        This can happen right after market open or during low liquidity periods.

        Args:
            mock_yfinance: Mocked yfinance.Ticker class.
        """
        # Only one data point
        data: Dict[str, list[float]] = {
            "Open": [170.0],
            "High": [175.0],
            "Low": [168.0],
            "Close": [172.0],
            "Volume": [1000000],
        }
        mock_ticker_instance: MagicMock = mock_yfinance.return_value
        mock_ticker_instance.history.return_value = pd.DataFrame(data)

        # Should handle gracefully
        min_price, max_price, current_price = get_24h_range("AAPL")

        assert min_price == 168.0
        assert max_price == 175.0
        assert current_price == 172.0

    def test_data_with_splits_or_dividends(self, mock_yfinance: MagicMock) -> None:
        """
        Test handling of data that might include corporate actions.

        While the 24h period is unlikely to have splits, we should handle
        any unexpected data structures gracefully.

        Args:
            mock_yfinance: Mocked yfinance.Ticker class.
        """
        # DataFrame with extra columns (dividends, splits)
        data: Dict[str, Any] = {
            "Open": [170.0, 171.0],
            "High": [175.0, 176.0],
            "Low": [165.0, 168.0],
            "Close": [172.0, 173.0],
            "Volume": [1000000, 1100000],
            "Dividends": [0.0, 0.5],  # Unexpected column
            "Stock Splits": [0, 0],  # Unexpected column
        }
        mock_ticker_instance: MagicMock = mock_yfinance.return_value
        mock_ticker_instance.history.return_value = pd.DataFrame(data)

        # Should ignore extra columns and process successfully
        min_price, max_price, current_price = get_24h_range("AAPL")

        assert min_price == 165.0
        assert max_price == 176.0
        assert current_price == 173.0

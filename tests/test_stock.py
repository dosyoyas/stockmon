"""
StockMon Stock Service Tests.

This module tests the stock service functionality including YFinance integration,
data fetching, error handling, and market status detection.
"""

# pylint: disable=W0621,C0415,R0913

from typing import Any, Dict
from unittest.mock import MagicMock

import pandas as pd
import pytest

from app.services.stock import (InvalidTickerError, MarketClosedError,
                                StockDataTimeoutError, get_24h_range)


class TestGet24hRange:
    """Test suite for get_24h_range function."""

    def test_valid_ticker_returns_min_max_current(
        self, mock_yfinance: MagicMock
    ) -> None:
        """
        Test that a valid ticker returns correct min, max, and current prices.

        Args:
            mock_yfinance: Mocked yfinance.Ticker class.
        """
        # Configure mock to return data with clear min/max values
        data: Dict[str, list[float]] = {
            "Open": [170.0, 171.0, 169.0, 172.0],
            "High": [175.0, 176.0, 174.0, 177.0],
            "Low": [165.0, 168.0, 166.0, 170.0],
            "Close": [172.0, 173.0, 171.0, 174.5],
            "Volume": [1000000] * 4,
        }
        mock_ticker_instance: MagicMock = mock_yfinance.return_value
        mock_ticker_instance.history.return_value = pd.DataFrame(data)

        # Call the function
        min_price, max_price, current_price = get_24h_range("AAPL")

        # Verify results
        assert min_price == 165.0  # Lowest "Low" value
        assert max_price == 177.0  # Highest "High" value
        assert current_price == 174.5  # Last "Close" value

        # Verify yfinance was called with correct parameters
        mock_yfinance.assert_called_once_with("AAPL")
        mock_ticker_instance.history.assert_called_once_with(period="1d", interval="1h")

    def test_invalid_ticker_raises_error(self, mock_yfinance: MagicMock) -> None:
        """
        Test that an invalid ticker symbol raises InvalidTickerError.

        Args:
            mock_yfinance: Mocked yfinance.Ticker class.
        """
        # Configure mock to return empty DataFrame (typical for invalid tickers)
        mock_ticker_instance: MagicMock = mock_yfinance.return_value
        mock_ticker_instance.history.return_value = pd.DataFrame()

        # Verify that InvalidTickerError is raised
        with pytest.raises(InvalidTickerError) as exc_info:
            get_24h_range("INVALID")

        assert "INVALID" in str(exc_info.value)

    def test_market_closed_raises_error(self, mock_yfinance: MagicMock) -> None:
        """
        Test that empty data (market closed) raises MarketClosedError.

        Args:
            mock_yfinance: Mocked yfinance.Ticker class.
        """
        # Configure mock to return DataFrame with NaN values (market closed)
        data: Dict[str, list[Any]] = {
            "Open": [None, None],
            "High": [None, None],
            "Low": [None, None],
            "Close": [None, None],
            "Volume": [None, None],
        }
        mock_ticker_instance: MagicMock = mock_yfinance.return_value
        mock_ticker_instance.history.return_value = pd.DataFrame(data)

        # Verify that MarketClosedError is raised
        with pytest.raises(MarketClosedError) as exc_info:
            get_24h_range("AAPL")

        assert "AAPL" in str(exc_info.value)

    def test_timeout_raises_error(self, mock_yfinance: MagicMock) -> None:
        """
        Test that API timeout raises StockDataTimeoutError.

        Args:
            mock_yfinance: Mocked yfinance.Ticker class.
        """
        # Configure mock to raise a timeout exception
        mock_ticker_instance: MagicMock = mock_yfinance.return_value
        mock_ticker_instance.history.side_effect = TimeoutError("Connection timeout")

        # Verify that StockDataTimeoutError is raised
        with pytest.raises(StockDataTimeoutError) as exc_info:
            get_24h_range("AAPL")

        assert "AAPL" in str(exc_info.value)
        assert "timeout" in str(exc_info.value).lower()

    def test_network_error_raises_appropriate_error(
        self, mock_yfinance: MagicMock
    ) -> None:
        """
        Test that network errors are handled gracefully.

        Args:
            mock_yfinance: Mocked yfinance.Ticker class.
        """
        # Configure mock to raise a generic exception (network error)
        mock_ticker_instance: MagicMock = mock_yfinance.return_value
        mock_ticker_instance.history.side_effect = Exception("Network error")

        # Verify that a general exception is raised with context
        with pytest.raises(Exception) as exc_info:
            get_24h_range("AAPL")

        assert "AAPL" in str(exc_info.value) or "Network error" in str(exc_info.value)

    def test_single_data_point_uses_same_for_min_max(
        self, mock_yfinance: MagicMock
    ) -> None:
        """
        Test that a single data point correctly uses same value for min and max.

        Args:
            mock_yfinance: Mocked yfinance.Ticker class.
        """
        # Configure mock to return single data point
        data: Dict[str, list[float]] = {
            "Open": [170.0],
            "High": [175.0],
            "Low": [168.0],
            "Close": [172.0],
            "Volume": [1000000],
        }
        mock_ticker_instance: MagicMock = mock_yfinance.return_value
        mock_ticker_instance.history.return_value = pd.DataFrame(data)

        # Call the function
        min_price, max_price, current_price = get_24h_range("AAPL")

        # Verify results
        assert min_price == 168.0
        assert max_price == 175.0
        assert current_price == 172.0

    def test_multiple_tickers_independent(self, mock_yfinance: MagicMock) -> None:
        """
        Test that multiple ticker calls are independent.

        Args:
            mock_yfinance: Mocked yfinance.Ticker class.
        """
        # Configure mock to return different data for each call
        mock_ticker_instance: MagicMock = mock_yfinance.return_value

        # First call (AAPL)
        data_aapl: Dict[str, list[float]] = {
            "Open": [170.0],
            "High": [175.0],
            "Low": [168.0],
            "Close": [172.0],
            "Volume": [1000000],
        }
        # Second call (MSFT)
        data_msft: Dict[str, list[float]] = {
            "Open": [400.0],
            "High": [410.0],
            "Low": [395.0],
            "Close": [405.0],
            "Volume": [2000000],
        }

        mock_ticker_instance.history.side_effect = [
            pd.DataFrame(data_aapl),
            pd.DataFrame(data_msft),
        ]

        # Call for AAPL
        min_aapl, max_aapl, current_aapl = get_24h_range("AAPL")
        assert min_aapl == 168.0
        assert max_aapl == 175.0
        assert current_aapl == 172.0

        # Call for MSFT
        min_msft, max_msft, current_msft = get_24h_range("MSFT")
        assert min_msft == 395.0
        assert max_msft == 410.0
        assert current_msft == 405.0

        # Verify both tickers were called
        assert mock_yfinance.call_count == 2

    def test_handles_extreme_volatility(self, mock_yfinance: MagicMock) -> None:
        """
        Test handling of extreme price volatility in 24h period.

        Args:
            mock_yfinance: Mocked yfinance.Ticker class.
        """
        # Configure mock with extreme price swings
        data: Dict[str, list[float]] = {
            "Open": [100.0, 150.0, 50.0, 200.0],
            "High": [200.0, 180.0, 100.0, 250.0],
            "Low": [50.0, 60.0, 30.0, 150.0],
            "Close": [150.0, 80.0, 90.0, 220.0],
            "Volume": [5000000] * 4,
        }
        mock_ticker_instance: MagicMock = mock_yfinance.return_value
        mock_ticker_instance.history.return_value = pd.DataFrame(data)

        # Call the function
        min_price, max_price, current_price = get_24h_range("VOLATILE")

        # Verify results capture the extremes
        assert min_price == 30.0  # Absolute minimum across all periods
        assert max_price == 250.0  # Absolute maximum across all periods
        assert current_price == 220.0  # Last close price

    def test_ticker_symbol_case_sensitivity(self, mock_yfinance: MagicMock) -> None:
        """
        Test that ticker symbols are passed as-is to yfinance.

        Args:
            mock_yfinance: Mocked yfinance.Ticker class.
        """
        # Configure mock to return valid data
        data: Dict[str, list[float]] = {
            "Open": [170.0],
            "High": [175.0],
            "Low": [168.0],
            "Close": [172.0],
            "Volume": [1000000],
        }
        mock_ticker_instance: MagicMock = mock_yfinance.return_value
        mock_ticker_instance.history.return_value = pd.DataFrame(data)

        # Test lowercase ticker (yfinance typically accepts this)
        get_24h_range("aapl")

        # Verify yfinance was called with lowercase
        mock_yfinance.assert_called_with("aapl")

    def test_empty_dataframe_columns_raises_invalid_ticker(
        self, mock_yfinance: MagicMock
    ) -> None:
        """
        Test that a DataFrame without required columns raises InvalidTickerError.

        Args:
            mock_yfinance: Mocked yfinance.Ticker class.
        """
        # Configure mock to return DataFrame with wrong columns
        data: Dict[str, list[float]] = {
            "SomeColumn": [1.0, 2.0, 3.0],
        }
        mock_ticker_instance: MagicMock = mock_yfinance.return_value
        mock_ticker_instance.history.return_value = pd.DataFrame(data)

        # Verify that InvalidTickerError is raised (missing required columns)
        with pytest.raises(InvalidTickerError) as exc_info:
            get_24h_range("BADDATA")

        # Verify error message mentions missing columns
        assert "Missing required data columns" in str(exc_info.value)

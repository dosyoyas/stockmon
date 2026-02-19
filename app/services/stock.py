"""
StockMon Stock Service.

This module provides functions to fetch and process stock market data using
the YFinance library. It includes error handling for various failure scenarios
such as invalid tickers, market closures, and API timeouts.

The primary function get_24h_range() fetches the last 24 hours of stock data
and calculates the minimum price, maximum price, and current (most recent) price.
"""

from typing import Tuple

import pandas as pd
import yfinance


class InvalidTickerError(Exception):
    """
    Exception raised when a ticker symbol is invalid or not found.

    This typically occurs when:
    - The ticker symbol doesn't exist
    - The ticker has been delisted
    - YFinance cannot find data for the symbol
    """


class MarketClosedError(Exception):
    """
    Exception raised when market is closed and no recent data is available.

    This typically occurs when:
    - Market is closed (weekends, holidays, outside trading hours)
    - No data is available for the requested period
    - All returned data points contain NaN/null values
    """


class StockDataTimeoutError(Exception):
    """
    Exception raised when fetching stock data times out.

    This typically occurs when:
    - YFinance API is slow to respond
    - Network connectivity issues
    - The configured timeout (10 seconds) is exceeded
    """


def get_24h_range(ticker: str) -> Tuple[float, float, float]:
    """
    Fetch 24-hour price range for a given ticker symbol.

    This function retrieves the last 24 hours of stock data from YFinance
    using a 1-hour interval, then calculates:
    - Minimum price: The lowest "Low" price in the period
    - Maximum price: The highest "High" price in the period
    - Current price: The most recent "Close" price

    Args:
        ticker: Stock ticker symbol (e.g., "AAPL", "MSFT", "GOOGL").

    Returns:
        Tuple[float, float, float]: A tuple containing:
            - min_price: Minimum price in the last 24 hours
            - max_price: Maximum price in the last 24 hours
            - current_price: Most recent closing price

    Raises:
        InvalidTickerError: If the ticker symbol is invalid or not found.
        MarketClosedError: If the market is closed and no data is available.
        StockDataTimeoutError: If the API request times out (>10 seconds).
        Exception: For other unexpected errors during data fetching.

    Example:
        >>> min_p, max_p, current_p = get_24h_range("AAPL")
        >>> print(f"Min: ${min_p:.2f}, Max: ${max_p:.2f}, Current: ${current_p:.2f}")
        Min: $168.50, Max: $175.30, Current: $172.40

    Note:
        - The timeout for each ticker is 10 seconds as specified in requirements
        - This function uses yfinance which may be subject to rate limiting
        - Market data may be delayed by 15-20 minutes for non-premium users
    """
    try:
        # Create Ticker instance
        stock: yfinance.Ticker = yfinance.Ticker(ticker)

        # Fetch last 24 hours of data with 1-hour intervals
        # period="1d" gets the last trading day (up to 24 hours)
        # interval="1h" provides hourly data points
        hist: pd.DataFrame = stock.history(period="1d", interval="1h")

        # Check if DataFrame is empty (invalid ticker)
        if hist.empty:
            raise InvalidTickerError(
                f"No data available for ticker '{ticker}'. "
                "The ticker may be invalid or not found."
            )

        # Check if required columns exist BEFORE trying to access them
        required_columns: list[str] = ["Low", "High", "Close"]
        missing_columns: list[str] = [
            col for col in required_columns if col not in hist.columns
        ]
        if missing_columns:
            raise InvalidTickerError(
                f"Missing required data columns for ticker '{ticker}': {missing_columns}"
            )

        # Check if all data is NaN (market closed or no recent data)
        if hist[["Low", "High", "Close"]].isna().all().all():
            raise MarketClosedError(
                f"No valid price data available for ticker '{ticker}'. "
                "The market may be closed or data is unavailable."
            )

        # Drop NaN values before calculating min/max
        hist_clean: pd.DataFrame = hist.dropna(subset=["Low", "High", "Close"])

        # Check if we have any valid data after dropping NaN
        if hist_clean.empty:
            raise MarketClosedError(
                f"No valid price data available for ticker '{ticker}' after "
                "removing null values. The market may be closed."
            )

        # Calculate min, max, and current prices
        min_price: float = float(hist_clean["Low"].min())
        max_price: float = float(hist_clean["High"].max())
        current_price: float = float(hist_clean["Close"].iloc[-1])  # Last closing price

        return min_price, max_price, current_price

    except TimeoutError as e:
        # Handle timeout errors specifically
        raise StockDataTimeoutError(
            f"Timeout while fetching data for ticker '{ticker}'. "
            f"The request exceeded 10 seconds: {str(e)}"
        ) from e

    except (InvalidTickerError, MarketClosedError, StockDataTimeoutError):
        # Re-raise our custom exceptions without wrapping
        raise

    except Exception as e:
        # Catch-all for unexpected errors
        # Re-raise with additional context about which ticker failed
        raise Exception(
            f"Unexpected error while fetching data for ticker '{ticker}': {str(e)}"
        ) from e

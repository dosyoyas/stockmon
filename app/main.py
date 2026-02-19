"""
StockMon API - Main Application.

This module provides the FastAPI application for the StockMon API.
It implements endpoints for checking stock price alerts and health monitoring.

Endpoints:
    POST /check-alerts - Check stock alerts with authentication
    GET /health - Health check without authentication
    GET / - API information
"""

from datetime import datetime, timezone
from typing import Dict, List

import pytz
from fastapi import Depends, FastAPI

from app.auth import require_api_key
from app.models import Alert, AlertRequest, AlertResponse, ErrorDetail
from app.services.stock import (InvalidTickerError, MarketClosedError,
                                StockDataTimeoutError, get_24h_range)

# Create FastAPI application
app: FastAPI = FastAPI(
    title="StockMon API",
    description="Stock price monitoring API with threshold alerts",
    version="1.0.0",
)


def is_market_open(check_time: datetime) -> bool:
    """
    Determine if the NYSE market is currently open.

    Market hours: Monday-Friday, 9:30 AM - 4:00 PM ET (excluding holidays).

    This function checks:
    1. Day of week (Monday=0 to Friday=4)
    2. Time within trading hours (9:30 AM - 4:00 PM ET)

    Note: This does NOT check for market holidays (e.g., Thanksgiving, Christmas).
    A production system would need a holiday calendar.

    Args:
        check_time: The datetime to check (should be timezone-aware).

    Returns:
        bool: True if market is open, False otherwise.

    Example:
        >>> from datetime import datetime
        >>> import pytz
        >>> # Tuesday at 2:00 PM ET
        >>> dt = datetime(2024, 2, 6, 14, 0, 0, tzinfo=pytz.timezone('US/Eastern'))
        >>> is_market_open(dt)
        True
        >>> # Saturday at 2:00 PM ET
        >>> dt = datetime(2024, 2, 10, 14, 0, 0, tzinfo=pytz.timezone('US/Eastern'))
        >>> is_market_open(dt)
        False
    """
    # Convert to Eastern Time
    eastern: pytz.BaseTzInfo = pytz.timezone("US/Eastern")
    et_time: datetime = check_time.astimezone(eastern)

    # Check day of week (Monday=0, Sunday=6)
    weekday: int = et_time.weekday()
    if weekday > 4:  # Saturday or Sunday
        return False

    # Check time (9:30 AM - 4:00 PM ET)
    hour: int = et_time.hour
    minute: int = et_time.minute

    # Before 9:30 AM
    if hour < 9 or (hour == 9 and minute < 30):
        return False

    # After 4:00 PM
    if hour >= 16:
        return False

    return True


@app.get("/")
async def root() -> Dict[str, str]:
    """
    API information endpoint.

    Returns:
        Dict[str, str]: Basic API information.

    Example:
        >>> response = await root()
        >>> assert "name" in response
        >>> assert "version" in response
    """
    return {
        "name": "StockMon API",
        "version": "1.0.0",
        "description": "Stock price monitoring API with threshold alerts",
    }


@app.get("/health")
async def health() -> Dict[str, str]:
    """
    Health check endpoint (no authentication required).

    This endpoint is used by hosting providers (e.g., Railway) to verify
    the service is running. It does not require authentication.

    Returns:
        Dict[str, str]: Health status.

    Example:
        >>> response = await health()
        >>> assert response == {"status": "ok"}
    """
    return {"status": "ok"}


@app.post("/check-alerts")
async def check_alerts(
    request: AlertRequest,
    _api_key: str = Depends(require_api_key),
) -> AlertResponse:
    """
    Check stock price alerts for given tickers and thresholds.

    This endpoint accepts a dictionary of ticker symbols with buy/sell thresholds,
    fetches 24-hour price data from YFinance, and returns alerts when thresholds
    are breached.

    Authentication:
        Requires X-API-Key header with valid API key.

    Request Body:
        Dictionary mapping ticker symbols to threshold configurations.
        Maximum 20 tickers per request.

    Response:
        - alerts: List of triggered alerts (buy/sell)
        - errors: List of errors for tickers that failed to process
        - market_open: Whether NYSE is currently open
        - service_degraded: True if ALL tickers failed
        - checked_at: ISO 8601 timestamp of the check

    Alert Logic:
        For each ticker with 24h data (min, max, current):
        - Buy alert: Triggered if min <= buy_threshold (reached=min)
        - Sell alert: Triggered if max >= sell_threshold (reached=max)
        - A ticker can generate both alerts if highly volatile

    Error Handling:
        - Errors are collected per ticker and included in response
        - Processing continues for other tickers after individual failures
        - Common errors: InvalidTickerError, MarketClosedError, StockDataTimeoutError

    Args:
        request: AlertRequest with ticker symbols and thresholds.
        _api_key: Validated API key from authentication dependency (unused in function body).

    Returns:
        AlertResponse: Alerts, errors, market status, and timestamp.

    Raises:
        ValidationError: 422 if request validation fails (e.g., >20 tickers).

    Example:
        >>> from app.models import ThresholdDict
        >>> request = AlertRequest(root={
        ...     "AAPL": ThresholdDict(buy=170.0, sell=190.0),
        ...     "MSFT": ThresholdDict(buy=400.0)
        ... })
        >>> response = await check_alerts(request, "valid-api-key")
        >>> assert isinstance(response.alerts, list)
        >>> assert isinstance(response.market_open, bool)
    """
    # Mark _api_key as intentionally unused (required for dependency injection)
    _ = _api_key

    # Get current timestamp
    checked_at: datetime = datetime.now(timezone.utc)

    # Determine market status
    market_open: bool = is_market_open(checked_at)

    # Initialize response lists
    alerts: List[Alert] = []
    errors: List[ErrorDetail] = []

    # Track successful data fetches for service_degraded calculation
    successful_fetches: int = 0
    total_tickers: int = len(request.root)

    # Process each ticker
    for ticker_symbol, thresholds in request.root.items():
        try:
            # Fetch 24-hour price range
            min_price, max_price, current_price = get_24h_range(ticker_symbol)

            # Successfully fetched data
            successful_fetches += 1

            # Check buy threshold (alert if price dropped to or below threshold)
            if thresholds.buy is not None and min_price <= thresholds.buy:
                buy_alert: Alert = Alert(
                    ticker=ticker_symbol,
                    type="buy",
                    threshold=thresholds.buy,
                    reached=min_price,
                    current=current_price,
                )
                alerts.append(buy_alert)

            # Check sell threshold (alert if price rose to or above threshold)
            if thresholds.sell is not None and max_price >= thresholds.sell:
                sell_alert: Alert = Alert(
                    ticker=ticker_symbol,
                    type="sell",
                    threshold=thresholds.sell,
                    reached=max_price,
                    current=current_price,
                )
                alerts.append(sell_alert)

        except InvalidTickerError as e:
            # Ticker not found or invalid
            error: ErrorDetail = ErrorDetail(
                ticker=ticker_symbol,
                error=f"Invalid ticker: {str(e)}",
            )
            errors.append(error)

        except MarketClosedError as e:
            # Market closed or no data available
            error = ErrorDetail(
                ticker=ticker_symbol,
                error=f"Market closed: {str(e)}",
            )
            errors.append(error)

        except StockDataTimeoutError as e:
            # Timeout fetching data
            error = ErrorDetail(
                ticker=ticker_symbol,
                error=f"Timeout: {str(e)}",
            )
            errors.append(error)

        except Exception as e:  # pylint: disable=W0718
            # Catch-all for unexpected errors
            error = ErrorDetail(
                ticker=ticker_symbol,
                error=f"Unexpected error: {str(e)}",
            )
            errors.append(error)

    # Calculate service_degraded status
    # True if ALL tickers failed (no successful data fetches)
    service_degraded: bool = (
        total_tickers > 0 and successful_fetches == 0 and len(errors) == total_tickers
    )

    # Build response
    response: AlertResponse = AlertResponse(
        alerts=alerts,
        errors=errors,
        market_open=market_open,
        service_degraded=service_degraded,
        checked_at=checked_at,
    )

    return response

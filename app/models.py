"""
StockMon API - Pydantic Models.

This module defines the Pydantic schemas for request and response validation
in the StockMon API. All models use Pydantic v2 syntax.
"""

from datetime import datetime
from typing import Dict, Literal, Optional

from pydantic import BaseModel, Field, RootModel, field_validator


class ThresholdDict(BaseModel):
    """
    Threshold configuration for a single ticker.

    Both buy and sell thresholds are optional - a request can specify one,
    both, or neither (though neither would be pointless).

    Attributes:
        buy: Optional buy threshold. Alert triggers if price drops to or below this value.
        sell: Optional sell threshold. Alert triggers if price rises to or above this value.

    Example:
        # Both thresholds
        {"buy": 170.0, "sell": 190.0}

        # Only buy threshold
        {"buy": 170.0}

        # Only sell threshold
        {"sell": 190.0}
    """

    buy: Optional[float] = Field(
        None,
        description="Buy threshold - alert if price drops to or below this value",
    )
    sell: Optional[float] = Field(
        None,
        description="Sell threshold - alert if price rises to or above this value",
    )

    @field_validator("buy", "sell")
    @classmethod
    def validate_positive(cls, value: Optional[float]) -> Optional[float]:
        """
        Validate that threshold values are positive when provided.

        Args:
            value: The threshold value to validate.

        Returns:
            Optional[float]: The validated threshold value.

        Raises:
            ValueError: If the threshold is not positive (must be > 0).
        """
        if value is not None and value <= 0:
            raise ValueError("Threshold must be greater than 0")
        return value


class AlertRequest(RootModel[Dict[str, ThresholdDict]]):  # pylint: disable=R0903
    """
    Request body for the /check-alerts endpoint.

    A dictionary mapping ticker symbols to their threshold configurations.
    Maximum of 20 tickers per request.

    Type hint explanation:
    - Uses RootModel for direct dictionary validation in Pydantic v2
    - Access the dictionary via .root attribute

    Example:
        {
            "AAPL": {"buy": 170.0, "sell": 190.0},
            "MSFT": {"buy": 400.0},
            "GOOGL": {"sell": 160.0}
        }
    """

    root: Dict[str, ThresholdDict] = Field(
        ...,
        description="Dictionary of ticker symbols to threshold configurations",
    )

    @field_validator("root")
    @classmethod
    def validate_max_tickers(
        cls, value: Dict[str, ThresholdDict]
    ) -> Dict[str, ThresholdDict]:
        """
        Validate that the request contains at most 20 tickers.

        Args:
            value: The dictionary of ticker symbols to thresholds.

        Returns:
            Dict[str, ThresholdDict]: The validated dictionary.

        Raises:
            ValueError: If more than 20 tickers are provided.
        """
        if len(value) > 20:
            raise ValueError(
                f"Maximum 20 tickers allowed per request. Received {len(value)} tickers."
            )
        return value


class Ticker(BaseModel):
    """
    Alternative model for individual ticker in request (not used in main API).

    This model is provided for potential future use or alternative endpoints.
    The main /check-alerts endpoint uses AlertRequest with RootModel dict pattern.

    Attributes:
        symbol: Ticker symbol (e.g., "AAPL", "MSFT").
        thresholds: Buy and sell threshold configuration.
    """

    symbol: str = Field(
        ...,
        description="Ticker symbol",
        min_length=1,
        max_length=10,
        pattern=r"^[A-Z0-9\.\-]+$",
    )
    thresholds: ThresholdDict = Field(..., description="Buy/sell thresholds")


class Alert(BaseModel):
    """
    Individual alert in the response.

    Represents a single threshold breach for a ticker. A ticker can generate
    multiple alerts if it breaches both buy and sell thresholds.

    Attributes:
        ticker: The ticker symbol that triggered the alert.
        type: Alert type - either "buy" or "sell".
        threshold: The threshold value that was configured.
        reached: The actual price that breached the threshold (min for buy, max for sell).
        current: The most recent price for this ticker.

    Example:
        {
            "ticker": "AAPL",
            "type": "buy",
            "threshold": 170.0,
            "reached": 168.50,
            "current": 172.30
        }
    """

    ticker: str = Field(..., description="Ticker symbol that triggered the alert")
    type: Literal["buy", "sell"] = Field(
        ..., description="Alert type - 'buy' or 'sell'"
    )
    threshold: float = Field(..., description="The threshold value that was configured")
    reached: float = Field(
        ...,
        description="The price that breached the threshold (min for buy, max for sell)",
    )
    current: float = Field(..., description="The most recent price for this ticker")

    @field_validator("threshold", "reached", "current")
    @classmethod
    def validate_positive(cls, value: float) -> float:
        """
        Validate that numeric values are positive.

        Args:
            value: The numeric value to validate.

        Returns:
            float: The validated numeric value.

        Raises:
            ValueError: If the value is not positive (must be > 0).
        """
        if value <= 0:
            raise ValueError("Value must be greater than 0")
        return value


class ErrorDetail(BaseModel):
    """
    Error detail for a ticker that failed to process.

    When a ticker fails (invalid symbol, API timeout, etc.), it's included
    in the errors list rather than failing the entire request.

    Attributes:
        ticker: The ticker symbol that failed.
        error: Human-readable error message describing the failure.

    Example:
        {
            "ticker": "INVALID",
            "error": "Ticker not found"
        }
    """

    ticker: str = Field(..., description="Ticker symbol that failed")
    error: str = Field(..., description="Error message describing the failure")


class AlertResponse(BaseModel):
    """
    Response body for the /check-alerts endpoint.

    Contains alerts, errors, market status, service health, and timestamp.

    Attributes:
        alerts: List of alerts for tickers that breached thresholds.
        errors: List of errors for tickers that failed to process.
        market_open: Whether the market is currently open (NYSE hours).
        service_degraded: True if all tickers failed (likely YFinance API issue).
        checked_at: ISO 8601 timestamp when the check was performed.

    Example:
        {
            "alerts": [
                {
                    "ticker": "AAPL",
                    "type": "buy",
                    "threshold": 170.0,
                    "reached": 168.50,
                    "current": 172.30
                }
            ],
            "errors": [
                {"ticker": "INVALID", "error": "Ticker not found"}
            ],
            "market_open": true,
            "service_degraded": false,
            "checked_at": "2024-02-06T14:30:00Z"
        }
    """

    alerts: list[Alert] = Field(
        default_factory=list, description="List of triggered alerts"
    )
    errors: list[ErrorDetail] = Field(
        default_factory=list, description="List of errors for failed tickers"
    )
    market_open: bool = Field(
        ..., description="Whether the market is currently open (NYSE hours)"
    )
    service_degraded: bool = Field(
        ...,
        description="True if all tickers failed (likely YFinance API issue)",
    )
    checked_at: datetime = Field(
        ..., description="ISO 8601 timestamp when the check was performed"
    )

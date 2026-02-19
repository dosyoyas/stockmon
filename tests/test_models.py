"""
StockMon API - Models Unit Tests.

This module tests the Pydantic models for proper validation, serialization,
and deserialization. Tests cover both valid and invalid inputs.
"""

# pylint: disable=E1101

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.models import (Alert, AlertRequest, AlertResponse, ErrorDetail,
                        ThresholdDict, Ticker)


class TestThresholdDict:
    """Test ThresholdDict validation."""

    def test_both_thresholds_valid(self) -> None:
        """Test ThresholdDict with both buy and sell thresholds."""
        threshold: ThresholdDict = ThresholdDict(buy=170.0, sell=190.0)
        assert threshold.buy == 170.0
        assert threshold.sell == 190.0

    def test_only_buy_threshold_valid(self) -> None:
        """Test ThresholdDict with only buy threshold."""
        threshold: ThresholdDict = ThresholdDict(buy=170.0, sell=None)
        assert threshold.buy == 170.0
        assert threshold.sell is None

    def test_only_sell_threshold_valid(self) -> None:
        """Test ThresholdDict with only sell threshold."""
        threshold: ThresholdDict = ThresholdDict(buy=None, sell=190.0)
        assert threshold.buy is None
        assert threshold.sell == 190.0

    def test_no_thresholds_valid(self) -> None:
        """Test ThresholdDict with no thresholds (edge case)."""
        threshold: ThresholdDict = ThresholdDict(buy=None, sell=None)
        assert threshold.buy is None
        assert threshold.sell is None

    def test_negative_buy_threshold_invalid(self) -> None:
        """Test that negative buy threshold is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ThresholdDict(buy=-10.0, sell=None)
        assert "greater than 0" in str(exc_info.value).lower()

    def test_zero_buy_threshold_invalid(self) -> None:
        """Test that zero buy threshold is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ThresholdDict(buy=0.0, sell=None)
        assert "greater than 0" in str(exc_info.value).lower()

    def test_negative_sell_threshold_invalid(self) -> None:
        """Test that negative sell threshold is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ThresholdDict(buy=None, sell=-10.0)
        assert "greater than 0" in str(exc_info.value).lower()

    def test_zero_sell_threshold_invalid(self) -> None:
        """Test that zero sell threshold is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ThresholdDict(buy=None, sell=0.0)
        assert "greater than 0" in str(exc_info.value).lower()

    def test_from_dict(self) -> None:
        """Test creating ThresholdDict from dictionary."""
        data: dict[str, float] = {"buy": 170.0, "sell": 190.0}
        threshold: ThresholdDict = ThresholdDict(**data)
        assert threshold.buy == 170.0
        assert threshold.sell == 190.0


class TestAlertRequest:
    """Test AlertRequest validation."""

    def test_valid_single_ticker(self) -> None:
        """Test AlertRequest with single ticker."""
        data: dict[str, ThresholdDict] = {"AAPL": ThresholdDict(buy=170.0, sell=190.0)}
        request: AlertRequest = AlertRequest(data)
        assert "AAPL" in request.root
        assert request.root["AAPL"].buy == 170.0
        assert request.root["AAPL"].sell == 190.0

    def test_valid_multiple_tickers(self) -> None:
        """Test AlertRequest with multiple tickers."""
        data: dict[str, ThresholdDict] = {
            "AAPL": ThresholdDict(buy=170.0, sell=190.0),
            "MSFT": ThresholdDict(buy=400.0, sell=None),
            "GOOGL": ThresholdDict(buy=None, sell=160.0),
        }
        request: AlertRequest = AlertRequest(data)
        assert len(request.root) == 3
        assert "AAPL" in request.root
        assert "MSFT" in request.root
        assert "GOOGL" in request.root

    def test_valid_twenty_tickers(self) -> None:
        """Test AlertRequest with exactly 20 tickers (maximum allowed)."""
        data: dict[str, ThresholdDict] = {
            f"TICK{i:02d}": ThresholdDict(buy=100.0 + i, sell=None) for i in range(20)
        }
        request: AlertRequest = AlertRequest(data)
        assert len(request.root) == 20

    def test_invalid_twenty_one_tickers(self) -> None:
        """Test that AlertRequest rejects more than 20 tickers."""
        data: dict[str, ThresholdDict] = {
            f"TICK{i:02d}": ThresholdDict(buy=100.0 + i, sell=None) for i in range(21)
        }
        with pytest.raises(ValidationError) as exc_info:
            AlertRequest(data)
        error_msg: str = str(exc_info.value).lower()
        assert "maximum 20 tickers" in error_msg or "20 tickers allowed" in error_msg

    def test_invalid_fifty_tickers(self) -> None:
        """Test that AlertRequest rejects way too many tickers."""
        data: dict[str, ThresholdDict] = {
            f"TICK{i:03d}": ThresholdDict(buy=100.0 + i, sell=None) for i in range(50)
        }
        with pytest.raises(ValidationError) as exc_info:
            AlertRequest(data)
        assert (
            "maximum 20 tickers" in str(exc_info.value).lower()
            or "20 tickers allowed" in str(exc_info.value).lower()
        )

    def test_empty_request_valid(self) -> None:
        """Test AlertRequest with no tickers (edge case, but technically valid)."""
        data: dict[str, ThresholdDict] = {}
        request: AlertRequest = AlertRequest(data)
        assert len(request.root) == 0


class TestTicker:
    """Test Ticker validation."""

    def test_valid_ticker(self) -> None:
        """Test Ticker with valid symbol and thresholds."""
        ticker: Ticker = Ticker(
            symbol="AAPL", thresholds=ThresholdDict(buy=170.0, sell=190.0)
        )
        assert ticker.symbol == "AAPL"
        assert ticker.thresholds.buy == 170.0
        assert ticker.thresholds.sell == 190.0

    def test_valid_ticker_with_dot(self) -> None:
        """Test Ticker with symbol containing dot (e.g., BRK.B)."""
        ticker: Ticker = Ticker(
            symbol="BRK.B", thresholds=ThresholdDict(buy=300.0, sell=None)
        )
        assert ticker.symbol == "BRK.B"

    def test_valid_ticker_with_dash(self) -> None:
        """Test Ticker with symbol containing dash."""
        ticker: Ticker = Ticker(
            symbol="BTC-USD", thresholds=ThresholdDict(buy=40000.0, sell=None)
        )
        assert ticker.symbol == "BTC-USD"

    def test_invalid_ticker_empty_symbol(self) -> None:
        """Test that empty symbol is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            Ticker(symbol="", thresholds=ThresholdDict(buy=170.0, sell=None))
        assert (
            "at least 1 character" in str(exc_info.value).lower()
            or "min_length" in str(exc_info.value).lower()
        )

    def test_invalid_ticker_too_long_symbol(self) -> None:
        """Test that symbol longer than 10 characters is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            Ticker(
                symbol="VERYLONGTICKER", thresholds=ThresholdDict(buy=170.0, sell=None)
            )
        assert (
            "at most 10 character" in str(exc_info.value).lower()
            or "max_length" in str(exc_info.value).lower()
        )

    def test_invalid_ticker_lowercase_symbol(self) -> None:
        """Test that lowercase symbol is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            Ticker(symbol="aapl", thresholds=ThresholdDict(buy=170.0, sell=None))
        assert (
            "string does not match regex" in str(exc_info.value).lower()
            or "pattern" in str(exc_info.value).lower()
        )

    def test_invalid_ticker_special_chars_symbol(self) -> None:
        """Test that symbol with invalid special characters is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            Ticker(symbol="AAPL@", thresholds=ThresholdDict(buy=170.0, sell=None))
        assert (
            "string does not match regex" in str(exc_info.value).lower()
            or "pattern" in str(exc_info.value).lower()
        )


class TestAlert:
    """Test Alert validation."""

    def test_valid_buy_alert(self) -> None:
        """Test Alert with type='buy'."""
        alert: Alert = Alert(
            ticker="AAPL", type="buy", threshold=170.0, reached=168.5, current=172.3
        )
        assert alert.ticker == "AAPL"
        assert alert.type == "buy"
        assert alert.threshold == 170.0
        assert alert.reached == 168.5
        assert alert.current == 172.3

    def test_valid_sell_alert(self) -> None:
        """Test Alert with type='sell'."""
        alert: Alert = Alert(
            ticker="MSFT", type="sell", threshold=420.0, reached=425.8, current=423.1
        )
        assert alert.ticker == "MSFT"
        assert alert.type == "sell"
        assert alert.threshold == 420.0
        assert alert.reached == 425.8
        assert alert.current == 423.1

    def test_invalid_alert_type(self) -> None:
        """Test that invalid alert type is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            Alert(
                ticker="AAPL",
                type="hold",  # type: ignore[arg-type]
                threshold=170.0,
                reached=168.5,
                current=172.3,
            )
        assert (
            "input should be 'buy' or 'sell'" in str(exc_info.value).lower()
            or "literal" in str(exc_info.value).lower()
        )

    def test_invalid_alert_negative_threshold(self) -> None:
        """Test that negative threshold is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            Alert(
                ticker="AAPL",
                type="buy",
                threshold=-170.0,
                reached=168.5,
                current=172.3,
            )
        assert "greater than 0" in str(exc_info.value).lower()

    def test_invalid_alert_zero_threshold(self) -> None:
        """Test that zero threshold is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            Alert(
                ticker="AAPL", type="buy", threshold=0.0, reached=168.5, current=172.3
            )
        assert "greater than 0" in str(exc_info.value).lower()

    def test_invalid_alert_negative_reached(self) -> None:
        """Test that negative reached price is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            Alert(
                ticker="AAPL",
                type="buy",
                threshold=170.0,
                reached=-168.5,
                current=172.3,
            )
        assert "greater than 0" in str(exc_info.value).lower()

    def test_invalid_alert_negative_current(self) -> None:
        """Test that negative current price is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            Alert(
                ticker="AAPL",
                type="buy",
                threshold=170.0,
                reached=168.5,
                current=-172.3,
            )
        assert "greater than 0" in str(exc_info.value).lower()


class TestErrorDetail:
    """Test ErrorDetail validation."""

    def test_valid_error_detail(self) -> None:
        """Test ErrorDetail with valid data."""
        error: ErrorDetail = ErrorDetail(ticker="INVALID", error="Ticker not found")
        assert error.ticker == "INVALID"
        assert error.error == "Ticker not found"

    def test_error_detail_from_dict(self) -> None:
        """Test creating ErrorDetail from dictionary."""
        data: dict[str, str] = {
            "ticker": "BADTICK",
            "error": "API timeout after 10 seconds",
        }
        error: ErrorDetail = ErrorDetail(**data)
        assert error.ticker == "BADTICK"
        assert error.error == "API timeout after 10 seconds"


class TestAlertResponse:
    """Test AlertResponse validation."""

    def test_valid_response_with_alerts(self) -> None:
        """Test AlertResponse with alerts and no errors."""
        response: AlertResponse = AlertResponse(
            alerts=[
                Alert(
                    ticker="AAPL",
                    type="buy",
                    threshold=170.0,
                    reached=168.5,
                    current=172.3,
                )
            ],
            errors=[],
            market_open=True,
            service_degraded=False,
            checked_at=datetime.now(timezone.utc),
        )
        assert len(response.alerts) == 1
        assert len(response.errors) == 0
        assert response.market_open is True
        assert response.service_degraded is False
        assert response.alerts[0].ticker == "AAPL"

    def test_valid_response_with_errors(self) -> None:
        """Test AlertResponse with errors and no alerts."""
        response: AlertResponse = AlertResponse(
            alerts=[],
            errors=[ErrorDetail(ticker="INVALID", error="Ticker not found")],
            market_open=True,
            service_degraded=False,
            checked_at=datetime.now(timezone.utc),
        )
        assert len(response.alerts) == 0
        assert len(response.errors) == 1
        assert response.errors[0].ticker == "INVALID"

    def test_valid_response_with_both_alerts_and_errors(self) -> None:
        """Test AlertResponse with both alerts and errors."""
        response: AlertResponse = AlertResponse(
            alerts=[
                Alert(
                    ticker="AAPL",
                    type="buy",
                    threshold=170.0,
                    reached=168.5,
                    current=172.3,
                )
            ],
            errors=[ErrorDetail(ticker="INVALID", error="Ticker not found")],
            market_open=True,
            service_degraded=False,
            checked_at=datetime.now(timezone.utc),
        )
        assert len(response.alerts) == 1
        assert len(response.errors) == 1

    def test_valid_response_empty_lists(self) -> None:
        """Test AlertResponse with empty alerts and errors (market closed scenario)."""
        response: AlertResponse = AlertResponse(
            alerts=[],
            errors=[],
            market_open=False,
            service_degraded=False,
            checked_at=datetime.now(timezone.utc),
        )
        assert len(response.alerts) == 0
        assert len(response.errors) == 0
        assert response.market_open is False

    def test_valid_response_service_degraded(self) -> None:
        """Test AlertResponse with service_degraded=True."""
        response: AlertResponse = AlertResponse(
            alerts=[],
            errors=[
                ErrorDetail(ticker="AAPL", error="YFinance API failure"),
                ErrorDetail(ticker="MSFT", error="YFinance API failure"),
            ],
            market_open=True,
            service_degraded=True,
            checked_at=datetime.now(timezone.utc),
        )
        assert response.service_degraded is True
        assert len(response.errors) == 2

    def test_valid_response_multiple_alerts_same_ticker(self) -> None:
        """Test AlertResponse with multiple alerts for same ticker (buy and sell)."""
        response: AlertResponse = AlertResponse(
            alerts=[
                Alert(
                    ticker="AAPL",
                    type="buy",
                    threshold=170.0,
                    reached=168.5,
                    current=172.3,
                ),
                Alert(
                    ticker="AAPL",
                    type="sell",
                    threshold=190.0,
                    reached=192.1,
                    current=172.3,
                ),
            ],
            errors=[],
            market_open=True,
            service_degraded=False,
            checked_at=datetime.now(timezone.utc),
        )
        assert len(response.alerts) == 2
        assert response.alerts[0].ticker == "AAPL"
        assert response.alerts[1].ticker == "AAPL"
        assert response.alerts[0].type == "buy"
        assert response.alerts[1].type == "sell"

    def test_response_from_dict(self) -> None:
        """Test creating AlertResponse from dictionary (API response simulation)."""
        alerts_list: list[dict[str, object]] = [
            {
                "ticker": "AAPL",
                "type": "buy",
                "threshold": 170.0,
                "reached": 168.5,
                "current": 172.3,
            }
        ]
        errors_list: list[dict[str, str]] = [
            {"ticker": "INVALID", "error": "Ticker not found"}
        ]
        response: AlertResponse = AlertResponse(
            alerts=[Alert(**a) for a in alerts_list],  # type: ignore[arg-type]
            errors=[ErrorDetail(**e) for e in errors_list],
            market_open=True,
            service_degraded=False,
            checked_at=datetime.fromisoformat("2024-02-06T14:30:00+00:00"),
        )
        assert len(response.alerts) == 1
        assert len(response.errors) == 1
        assert response.market_open is True
        assert response.service_degraded is False
        assert response.alerts[0].ticker == "AAPL"
        assert response.errors[0].ticker == "INVALID"

    def test_response_serialization(self) -> None:
        """Test that AlertResponse can be serialized to dict."""
        response: AlertResponse = AlertResponse(
            alerts=[
                Alert(
                    ticker="AAPL",
                    type="buy",
                    threshold=170.0,
                    reached=168.5,
                    current=172.3,
                )
            ],
            errors=[],
            market_open=True,
            service_degraded=False,
            checked_at=datetime(2024, 2, 6, 14, 30, 0, tzinfo=timezone.utc),
        )
        data: dict[str, object] = response.model_dump()
        assert "alerts" in data
        assert "errors" in data
        assert "market_open" in data
        assert "service_degraded" in data
        assert "checked_at" in data
        assert data["market_open"] is True
        assert len(data["alerts"]) == 1  # type: ignore[arg-type]

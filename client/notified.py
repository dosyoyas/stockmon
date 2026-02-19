"""
StockMon Client - Notification tracking and deduplication.

This module provides functionality to track which alerts have been sent
and prevents sending duplicate notifications within a configured silence period.
"""

import json
import time
from pathlib import Path
from typing import Any, Dict, List


def get_notification_key(ticker: str, alert_type: str) -> str:
    """
    Generate a unique key for a ticker and alert type combination.

    Args:
        ticker: Stock ticker symbol (e.g., "AAPL").
        alert_type: Type of alert ("buy" or "sell").

    Returns:
        str: Unique key in format "ticker:type" (e.g., "AAPL:buy").

    Example:
        key = get_notification_key("AAPL", "buy")
        # Returns: "AAPL:buy"
    """
    return f"{ticker}:{alert_type}"


def load_notified_data() -> Dict[str, float]:
    """
    Load notification tracking data from notified.json.

    The file stores a dictionary mapping notification keys to timestamps
    (Unix epoch seconds) when the notification was last sent.

    Returns:
        Dict[str, float]: Dictionary mapping notification keys to timestamps.
            Returns empty dict if file doesn't exist or contains invalid JSON.

    Example:
        data = load_notified_data()
        # Returns: {"AAPL:buy": 1708300000.0, "MSFT:sell": 1708310000.0}
    """
    client_dir: Path = Path(__file__).parent.resolve()
    notified_path: Path = client_dir / "notified.json"

    if not notified_path.exists():
        return {}

    try:
        with open(notified_path, "r", encoding="utf-8") as notified_file:
            content: str = notified_file.read().strip()

            # Handle empty file
            if not content:
                return {}

            data: Dict[str, float] = json.loads(content)
            return data

    except json.JSONDecodeError:
        # Log warning but don't crash - return empty dict
        print(
            f"WARNING: Invalid JSON in {notified_path}. Starting with empty notification history."
        )
        return {}

    except Exception as exc:  # pylint: disable=W0703
        # Catch any other file-related errors
        print(
            f"WARNING: Error reading {notified_path}: {exc}. Starting with empty notification history."
        )
        return {}


def save_notified_data(data: Dict[str, float]) -> None:
    """
    Save notification tracking data to notified.json.

    Args:
        data: Dictionary mapping notification keys to timestamps.

    Example:
        data = {"AAPL:buy": time.time(), "MSFT:sell": time.time()}
        save_notified_data(data)
    """
    client_dir: Path = Path(__file__).parent.resolve()
    notified_path: Path = client_dir / "notified.json"

    with open(notified_path, "w", encoding="utf-8") as notified_file:
        json.dump(data, notified_file, indent=2)


def clean_old_entries(data: Dict[str, float], silence_hours: int) -> Dict[str, float]:
    """
    Remove notification entries older than silence_hours.

    This cleanup prevents the notified.json file from growing indefinitely
    by removing entries that have expired beyond the silence period.

    Args:
        data: Dictionary of notification keys to timestamps.
        silence_hours: Number of hours for the silence period.

    Returns:
        Dict[str, float]: Cleaned dictionary with only recent entries.

    Example:
        current_time = time.time()
        data = {
            "AAPL:buy": current_time - (50 * 3600),  # 50 hours ago
            "MSFT:sell": current_time - (24 * 3600),  # 24 hours ago
        }
        cleaned = clean_old_entries(data, 48)
        # Returns: {"MSFT:sell": ...} - only the 24-hour-old entry
    """
    current_time: float = time.time()
    silence_seconds: float = silence_hours * 3600

    cleaned: Dict[str, float] = {
        key: timestamp
        for key, timestamp in data.items()
        if (current_time - timestamp) < silence_seconds
    }

    return cleaned


def filter_already_notified(
    alerts: List[Dict[str, Any]],
    notified_data: Dict[str, float],
    silence_hours: int,
) -> List[Dict[str, Any]]:
    """
    Filter out alerts that were recently notified within silence_hours.

    Args:
        alerts: List of alert dictionaries with 'ticker' and 'type' keys.
        notified_data: Dictionary of notification keys to timestamps.
        silence_hours: Number of hours for the silence period.

    Returns:
        List[Dict[str, Any]]: Filtered list of alerts that should be sent.

    Example:
        alerts = [
            {"ticker": "AAPL", "type": "buy"},
            {"ticker": "MSFT", "type": "sell"}
        ]
        notified_data = {"AAPL:buy": time.time() - (10 * 3600)}  # 10 hours ago
        filtered = filter_already_notified(alerts, notified_data, 48)
        # Returns: [{"ticker": "MSFT", "type": "sell"}] - AAPL filtered out
    """
    current_time: float = time.time()
    silence_seconds: float = silence_hours * 3600

    filtered_alerts: List[Dict[str, Any]] = []

    for alert in alerts:
        ticker: str = alert["ticker"]
        alert_type: str = alert["type"]
        key: str = get_notification_key(ticker, alert_type)

        # Check if this alert was recently notified
        if key in notified_data:
            last_notified: float = notified_data[key]
            time_since_notification: float = current_time - last_notified

            # Skip if within silence period
            if time_since_notification < silence_seconds:
                continue

        # Include alert (either never notified or silence period expired)
        filtered_alerts.append(alert)

    return filtered_alerts


class NotificationTracker:
    """
    Manage notification tracking with automatic persistence.

    This class provides a high-level interface for tracking notifications,
    filtering alerts, and cleaning up old entries.

    Attributes:
        silence_hours: Number of hours to wait before re-notifying same alert.
        _data: Internal dictionary mapping notification keys to timestamps.

    Example:
        tracker = NotificationTracker(silence_hours=48)

        # Filter alerts before sending
        alerts = [{"ticker": "AAPL", "type": "buy"}]
        new_alerts = tracker.filter_alerts(alerts)

        # Mark alerts as notified after sending
        for alert in new_alerts:
            tracker.mark_notified(alert["ticker"], alert["type"])

        # Periodic cleanup
        tracker.cleanup()
    """

    def __init__(self, silence_hours: int) -> None:
        """
        Initialize notification tracker.

        Args:
            silence_hours: Number of hours for the silence period.
        """
        self.silence_hours: int = silence_hours
        self._data: Dict[str, float] = load_notified_data()

    def mark_notified(self, ticker: str, alert_type: str) -> None:
        """
        Mark an alert as notified with current timestamp.

        Args:
            ticker: Stock ticker symbol.
            alert_type: Type of alert ("buy" or "sell").

        Example:
            tracker.mark_notified("AAPL", "buy")
        """
        key: str = get_notification_key(ticker, alert_type)
        self._data[key] = time.time()
        save_notified_data(self._data)

    def filter_alerts(self, alerts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filter alerts to remove recently notified ones.

        Args:
            alerts: List of alert dictionaries with 'ticker' and 'type' keys.

        Returns:
            List[Dict[str, Any]]: Filtered alerts that should be sent.

        Example:
            alerts = [
                {"ticker": "AAPL", "type": "buy"},
                {"ticker": "MSFT", "type": "sell"}
            ]
            new_alerts = tracker.filter_alerts(alerts)
        """
        return filter_already_notified(alerts, self._data, self.silence_hours)

    def cleanup(self) -> None:
        """
        Remove expired notification entries older than silence_hours.

        This should be called periodically to prevent unbounded growth
        of the notified.json file.

        Example:
            tracker.cleanup()
        """
        self._data = clean_old_entries(self._data, self.silence_hours)
        save_notified_data(self._data)

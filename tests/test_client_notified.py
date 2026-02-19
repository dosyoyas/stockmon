"""
Unit tests for StockMon client notification tracking.

These tests verify notification deduplication, tracking, and cleanup
functionality to prevent alert spam.
"""

import json
import time
import unittest
from typing import Any, Dict, List
from unittest.mock import MagicMock, mock_open, patch

from client.notified import (NotificationTracker, clean_old_entries,
                             filter_already_notified, get_notification_key,
                             load_notified_data, save_notified_data)


class TestGetNotificationKey(unittest.TestCase):
    """Test notification key generation."""

    def test_get_notification_key_buy(self) -> None:
        """Test key generation for buy alert."""
        key: str = get_notification_key("AAPL", "buy")
        self.assertEqual(key, "AAPL:buy")

    def test_get_notification_key_sell(self) -> None:
        """Test key generation for sell alert."""
        key: str = get_notification_key("MSFT", "sell")
        self.assertEqual(key, "MSFT:sell")

    def test_get_notification_key_case_sensitive(self) -> None:
        """Test that keys are case-sensitive."""
        key1: str = get_notification_key("AAPL", "buy")
        key2: str = get_notification_key("aapl", "buy")
        self.assertNotEqual(key1, key2)


class TestLoadNotifiedData(unittest.TestCase):
    """Test loading notification tracking data."""

    @patch("pathlib.Path.exists")
    @patch("builtins.open", new_callable=mock_open)
    def test_load_notified_data_success(
        self, mock_file: MagicMock, mock_exists: MagicMock
    ) -> None:
        """Test successful loading of notified.json."""
        mock_exists.return_value = True
        test_data: Dict[str, float] = {
            "AAPL:buy": 1708300000.0,
            "MSFT:sell": 1708310000.0,
        }
        mock_file.return_value.read.return_value = json.dumps(test_data)

        data: Dict[str, float] = load_notified_data()

        self.assertEqual(data["AAPL:buy"], 1708300000.0)
        self.assertEqual(data["MSFT:sell"], 1708310000.0)

    @patch("pathlib.Path.exists")
    def test_load_notified_data_file_not_found(self, mock_exists: MagicMock) -> None:
        """Test loading when notified.json does not exist."""
        mock_exists.return_value = False

        data: Dict[str, float] = load_notified_data()

        # Should return empty dict when file doesn't exist
        self.assertEqual(data, {})

    @patch("pathlib.Path.exists")
    @patch("builtins.open", new_callable=mock_open)
    def test_load_notified_data_invalid_json(
        self, mock_file: MagicMock, mock_exists: MagicMock
    ) -> None:
        """Test loading when notified.json contains invalid JSON."""
        mock_exists.return_value = True
        mock_file.return_value.read.return_value = "{invalid json"

        # Should return empty dict and log warning on invalid JSON
        data: Dict[str, float] = load_notified_data()
        self.assertEqual(data, {})

    @patch("pathlib.Path.exists")
    @patch("builtins.open", new_callable=mock_open)
    def test_load_notified_data_empty_file(
        self, mock_file: MagicMock, mock_exists: MagicMock
    ) -> None:
        """Test loading when notified.json is empty."""
        mock_exists.return_value = True
        mock_file.return_value.read.return_value = ""

        data: Dict[str, float] = load_notified_data()

        # Empty file should return empty dict
        self.assertEqual(data, {})

    @patch("pathlib.Path.exists")
    @patch("builtins.open", new_callable=mock_open)
    def test_load_notified_data_empty_object(
        self, mock_file: MagicMock, mock_exists: MagicMock
    ) -> None:
        """Test loading when notified.json contains empty object."""
        mock_exists.return_value = True
        mock_file.return_value.read.return_value = "{}"

        data: Dict[str, float] = load_notified_data()

        self.assertEqual(data, {})


class TestSaveNotifiedData(unittest.TestCase):
    """Test saving notification tracking data."""

    @patch("builtins.open", new_callable=mock_open)
    def test_save_notified_data_success(self, mock_file: MagicMock) -> None:
        """Test successful saving of notified.json."""
        test_data: Dict[str, float] = {
            "AAPL:buy": 1708300000.0,
            "MSFT:sell": 1708310000.0,
        }

        save_notified_data(test_data)

        # Verify file was opened for writing
        mock_file.assert_called_once()
        # Get the path from the call
        call_args = mock_file.call_args
        file_path = call_args[0][0]
        self.assertTrue(str(file_path).endswith("notified.json"))

        # Verify JSON was written with proper formatting
        handle = mock_file()
        written_data = "".join(call.args[0] for call in handle.write.call_args_list)
        parsed_data = json.loads(written_data)
        self.assertEqual(parsed_data, test_data)

    @patch("builtins.open", new_callable=mock_open)
    def test_save_notified_data_empty_dict(self, mock_file: MagicMock) -> None:
        """Test saving empty dictionary."""
        save_notified_data({})

        # Verify empty dict was written
        handle = mock_file()
        written_data = "".join(call.args[0] for call in handle.write.call_args_list)
        parsed_data = json.loads(written_data)
        self.assertEqual(parsed_data, {})


class TestCleanOldEntries(unittest.TestCase):
    """Test cleanup of old notification entries."""

    def test_clean_old_entries_removes_expired(self) -> None:
        """Test that expired entries are removed."""
        current_time: float = time.time()
        silence_hours: int = 48

        # Create data with old and recent entries
        data: Dict[str, float] = {
            "AAPL:buy": current_time - (50 * 3600),  # 50 hours ago (expired)
            "MSFT:sell": current_time - (24 * 3600),  # 24 hours ago (not expired)
            "GOOGL:buy": current_time - (100 * 3600),  # 100 hours ago (expired)
        }

        cleaned: Dict[str, float] = clean_old_entries(data, silence_hours)

        # Only MSFT:sell should remain
        self.assertEqual(len(cleaned), 1)
        self.assertIn("MSFT:sell", cleaned)
        self.assertNotIn("AAPL:buy", cleaned)
        self.assertNotIn("GOOGL:buy", cleaned)

    def test_clean_old_entries_keeps_all_recent(self) -> None:
        """Test that all recent entries are kept."""
        current_time: float = time.time()
        silence_hours: int = 48

        # All entries are recent
        data: Dict[str, float] = {
            "AAPL:buy": current_time - (10 * 3600),  # 10 hours ago
            "MSFT:sell": current_time - (20 * 3600),  # 20 hours ago
            "GOOGL:buy": current_time - (30 * 3600),  # 30 hours ago
        }

        cleaned: Dict[str, float] = clean_old_entries(data, silence_hours)

        # All should remain
        self.assertEqual(len(cleaned), 3)
        self.assertEqual(cleaned, data)

    def test_clean_old_entries_empty_dict(self) -> None:
        """Test cleanup with empty dictionary."""
        cleaned: Dict[str, float] = clean_old_entries({}, 48)
        self.assertEqual(cleaned, {})

    def test_clean_old_entries_removes_all_expired(self) -> None:
        """Test that all entries can be removed if expired."""
        current_time: float = time.time()
        silence_hours: int = 48

        # All entries are expired
        data: Dict[str, float] = {
            "AAPL:buy": current_time - (100 * 3600),
            "MSFT:sell": current_time - (200 * 3600),
        }

        cleaned: Dict[str, float] = clean_old_entries(data, silence_hours)

        self.assertEqual(cleaned, {})


class TestFilterAlreadyNotified(unittest.TestCase):
    """Test filtering of already notified alerts."""

    def test_filter_already_notified_removes_recent(self) -> None:
        """Test that recently notified alerts are filtered out."""
        current_time: float = time.time()

        alerts: List[Dict[str, Any]] = [
            {"ticker": "AAPL", "type": "buy"},
            {"ticker": "MSFT", "type": "sell"},
            {"ticker": "GOOGL", "type": "buy"},
        ]

        notified_data: Dict[str, float] = {
            "AAPL:buy": current_time - (10 * 3600),  # 10 hours ago
            "GOOGL:buy": current_time - (5 * 3600),  # 5 hours ago
        }

        silence_hours: int = 48

        filtered: List[Dict[str, Any]] = filter_already_notified(
            alerts, notified_data, silence_hours
        )

        # Only MSFT:sell should remain (not in notified_data)
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]["ticker"], "MSFT")
        self.assertEqual(filtered[0]["type"], "sell")

    def test_filter_already_notified_includes_expired(self) -> None:
        """Test that expired notifications are included again."""
        current_time: float = time.time()

        alerts: List[Dict[str, Any]] = [
            {"ticker": "AAPL", "type": "buy"},
            {"ticker": "MSFT", "type": "sell"},
        ]

        notified_data: Dict[str, float] = {
            "AAPL:buy": current_time - (50 * 3600),  # 50 hours ago (expired)
            "MSFT:sell": current_time - (10 * 3600),  # 10 hours ago (recent)
        }

        silence_hours: int = 48

        filtered: List[Dict[str, Any]] = filter_already_notified(
            alerts, notified_data, silence_hours
        )

        # AAPL should be included (expired), MSFT filtered (recent)
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]["ticker"], "AAPL")
        self.assertEqual(filtered[0]["type"], "buy")

    def test_filter_already_notified_empty_alerts(self) -> None:
        """Test filtering with empty alerts list."""
        filtered: List[Dict[str, Any]] = filter_already_notified([], {}, 48)
        self.assertEqual(filtered, [])

    def test_filter_already_notified_empty_notified_data(self) -> None:
        """Test filtering with empty notified data."""
        alerts: List[Dict[str, Any]] = [
            {"ticker": "AAPL", "type": "buy"},
            {"ticker": "MSFT", "type": "sell"},
        ]

        filtered: List[Dict[str, Any]] = filter_already_notified(alerts, {}, 48)

        # All alerts should remain when no notification history
        self.assertEqual(len(filtered), 2)
        self.assertEqual(filtered, alerts)

    def test_filter_already_notified_all_recent(self) -> None:
        """Test filtering when all alerts were recently notified."""
        current_time: float = time.time()

        alerts: List[Dict[str, Any]] = [
            {"ticker": "AAPL", "type": "buy"},
            {"ticker": "MSFT", "type": "sell"},
        ]

        notified_data: Dict[str, float] = {
            "AAPL:buy": current_time - (10 * 3600),
            "MSFT:sell": current_time - (20 * 3600),
        }

        silence_hours: int = 48

        filtered: List[Dict[str, Any]] = filter_already_notified(
            alerts, notified_data, silence_hours
        )

        # All should be filtered
        self.assertEqual(filtered, [])


class TestNotificationTracker(unittest.TestCase):
    """Test NotificationTracker class."""

    @patch("client.notified.load_notified_data")
    def test_tracker_initialization(self, mock_load: MagicMock) -> None:
        """Test tracker initialization loads data."""
        mock_load.return_value = {"AAPL:buy": 1708300000.0}

        tracker: NotificationTracker = NotificationTracker(silence_hours=48)

        mock_load.assert_called_once()
        self.assertEqual(tracker.silence_hours, 48)

    @patch("client.notified.load_notified_data")
    @patch("client.notified.save_notified_data")
    def test_tracker_mark_notified(
        self, mock_save: MagicMock, mock_load: MagicMock
    ) -> None:
        """Test marking an alert as notified."""
        mock_load.return_value = {}

        tracker: NotificationTracker = NotificationTracker(silence_hours=48)
        current_time: float = time.time()

        with patch("time.time", return_value=current_time):
            tracker.mark_notified("AAPL", "buy")

        # Verify save was called with updated data
        mock_save.assert_called_once()
        saved_data: Dict[str, float] = mock_save.call_args[0][0]
        self.assertIn("AAPL:buy", saved_data)
        self.assertAlmostEqual(saved_data["AAPL:buy"], current_time, delta=1.0)

    @patch("client.notified.load_notified_data")
    @patch("client.notified.save_notified_data")
    def test_tracker_mark_multiple_notified(
        self, mock_save: MagicMock, mock_load: MagicMock
    ) -> None:
        """Test marking multiple alerts as notified."""
        mock_load.return_value = {}

        tracker: NotificationTracker = NotificationTracker(silence_hours=48)

        tracker.mark_notified("AAPL", "buy")
        tracker.mark_notified("MSFT", "sell")

        # Should have called save twice
        self.assertEqual(mock_save.call_count, 2)

        # Check final state has both entries
        final_data: Dict[str, float] = mock_save.call_args[0][0]
        self.assertIn("AAPL:buy", final_data)
        self.assertIn("MSFT:sell", final_data)

    @patch("client.notified.load_notified_data")
    def test_tracker_filter_alerts(self, mock_load: MagicMock) -> None:
        """Test filtering alerts through tracker."""
        current_time: float = time.time()
        mock_load.return_value = {
            "AAPL:buy": current_time - (10 * 3600),  # Recent
        }

        tracker: NotificationTracker = NotificationTracker(silence_hours=48)

        alerts: List[Dict[str, Any]] = [
            {"ticker": "AAPL", "type": "buy"},
            {"ticker": "MSFT", "type": "sell"},
        ]

        filtered: List[Dict[str, Any]] = tracker.filter_alerts(alerts)

        # Only MSFT should remain
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]["ticker"], "MSFT")

    @patch("client.notified.load_notified_data")
    @patch("client.notified.save_notified_data")
    def test_tracker_cleanup(self, mock_save: MagicMock, mock_load: MagicMock) -> None:
        """Test cleanup of old entries."""
        current_time: float = time.time()
        mock_load.return_value = {
            "AAPL:buy": current_time - (100 * 3600),  # Expired
            "MSFT:sell": current_time - (10 * 3600),  # Recent
        }

        tracker: NotificationTracker = NotificationTracker(silence_hours=48)
        tracker.cleanup()

        # Verify save was called
        mock_save.assert_called_once()

        # Verify old entry was removed
        saved_data: Dict[str, float] = mock_save.call_args[0][0]
        self.assertNotIn("AAPL:buy", saved_data)
        self.assertIn("MSFT:sell", saved_data)

    @patch("client.notified.load_notified_data")
    @patch("client.notified.save_notified_data")
    def test_tracker_mark_notified_updates_existing(
        self, mock_save: MagicMock, mock_load: MagicMock
    ) -> None:
        """Test that marking already-notified alert updates timestamp."""
        old_time: float = time.time() - (100 * 3600)
        mock_load.return_value = {"AAPL:buy": old_time}

        tracker: NotificationTracker = NotificationTracker(silence_hours=48)
        new_time: float = time.time()

        with patch("time.time", return_value=new_time):
            tracker.mark_notified("AAPL", "buy")

        # Verify timestamp was updated
        saved_data: Dict[str, float] = mock_save.call_args[0][0]
        self.assertGreater(saved_data["AAPL:buy"], old_time)


if __name__ == "__main__":
    unittest.main()  # type: ignore[misc]

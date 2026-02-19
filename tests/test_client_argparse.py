"""
Unit tests for StockMon client command-line argument parsing.

These tests verify that the client correctly parses the --dry-run flag
and handles invalid arguments.
"""

import unittest
from io import StringIO
from typing import List
from unittest.mock import patch

from client.main import parse_arguments


class TestParseArguments(unittest.TestCase):
    """Test suite for parse_arguments function."""

    def test_parse_arguments_no_flags(self) -> None:
        """Test parsing with no command-line flags."""
        args: List[str] = []
        parsed = parse_arguments(args)

        self.assertFalse(parsed.dry_run)

    def test_parse_arguments_dry_run_flag(self) -> None:
        """Test parsing with --dry-run flag."""
        args: List[str] = ["--dry-run"]
        parsed = parse_arguments(args)

        self.assertTrue(parsed.dry_run)

    def test_parse_arguments_default_behavior(self) -> None:
        """Test that dry_run defaults to False when not specified."""
        args: List[str] = []
        parsed = parse_arguments(args)

        # Verify default is False (production mode)
        self.assertFalse(parsed.dry_run)

    def test_parse_arguments_help_exits(self) -> None:
        """Test that --help flag triggers exit."""
        args: List[str] = ["--help"]

        # argparse prints help and exits with code 0
        with self.assertRaises(SystemExit) as context:
            with patch("sys.stdout", new=StringIO()):
                parse_arguments(args)

        self.assertEqual(context.exception.code, 0)

    def test_parse_arguments_invalid_flag(self) -> None:
        """Test that invalid flags cause error and exit."""
        args: List[str] = ["--invalid-flag"]

        # argparse prints error and exits with code 2
        with self.assertRaises(SystemExit) as context:
            with patch("sys.stderr", new=StringIO()):
                parse_arguments(args)

        self.assertEqual(context.exception.code, 2)


if __name__ == "__main__":
    unittest.main()  # type: ignore[misc]

"""
StockMon Client - Main script for Raspberry Pi monitoring.

This module implements the client-side logic for StockMon, which:
- Loads configuration from config.json
- Calls the StockMon API periodically
- Manages alert notifications via email
- Tracks notified alerts to prevent spam
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional


def load_config() -> Dict[str, Any]:
    """
    Load configuration from client/config.json.

    The configuration includes:
    - api_url: URL of the StockMon API endpoint
    - silence_hours: Hours to wait before re-notifying same alert
    - tickers: Dictionary of ticker symbols with buy/sell thresholds

    Returns:
        Dict[str, Any]: Configuration dictionary with api_url, silence_hours, tickers.

    Raises:
        FileNotFoundError: If config.json does not exist.
        json.JSONDecodeError: If config.json is not valid JSON.
        KeyError: If required configuration keys are missing.
    """
    # Get the directory where this script is located
    client_dir: Path = Path(__file__).parent.resolve()
    config_path: Path = client_dir / "config.json"

    if not config_path.exists():
        raise FileNotFoundError(
            f"Configuration file not found: {config_path}\n"
            "Please create client/config.json with required settings."
        )

    try:
        with open(config_path, "r", encoding="utf-8") as config_file:
            config: Dict[str, Any] = json.load(config_file)
    except json.JSONDecodeError as exc:
        raise json.JSONDecodeError(
            f"Invalid JSON in {config_path}: {exc.msg}",
            exc.doc,
            exc.pos,
        ) from exc

    # Validate required keys
    required_keys: list[str] = ["api_url", "silence_hours", "tickers"]
    missing_keys: list[str] = [key for key in required_keys if key not in config]

    if missing_keys:
        raise KeyError(
            f"Missing required configuration keys in {config_path}: {', '.join(missing_keys)}\n"
            f"Required keys: {', '.join(required_keys)}"
        )

    # Validate tickers structure
    if not isinstance(config["tickers"], dict):
        raise TypeError(
            f"Invalid 'tickers' configuration in {config_path}. "
            "Expected dictionary of ticker symbols with buy/sell thresholds."
        )

    return config


def get_api_url(config: Dict[str, Any]) -> str:
    """
    Get the API URL, preferring environment variable over config file.

    The API_URL environment variable takes precedence over the api_url
    specified in config.json. This allows for easy override during local
    testing without modifying the configuration file.

    Args:
        config: Configuration dictionary loaded from config.json.

    Returns:
        str: API URL to use for requests.

    Example:
        # Use config.json value
        url = get_api_url(config)

        # Override with environment variable
        os.environ["API_URL"] = "http://localhost:8000/check-alerts"
        url = get_api_url(config)  # Returns the override value
    """
    env_url: Optional[str] = os.environ.get("API_URL")

    if env_url:
        return env_url

    return config["api_url"]


def parse_arguments(args: Optional[List[str]] = None) -> argparse.Namespace:
    """
    Parse command-line arguments for the StockMon client.

    Args:
        args: List of command-line arguments. If None, uses sys.argv[1:].
              This parameter allows for testing without modifying sys.argv.

    Returns:
        argparse.Namespace: Parsed arguments with the following attributes:
            - dry_run (bool): If True, print to stdout instead of sending emails
              and don't update notified.json.

    Example:
        # Normal execution (production mode)
        parsed = parse_arguments()
        if parsed.dry_run:
            print("Running in dry-run mode")

        # Dry-run mode for testing
        parsed = parse_arguments(["--dry-run"])
        assert parsed.dry_run is True
    """
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        description="StockMon Client - Monitor stock alerts and send email notifications",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Normal execution (production mode)
  python -m client.main

  # Dry-run mode (print to stdout, don't send emails, don't update notified.json)
  python -m client.main --dry-run

  # Test against local API
  API_URL=http://localhost:8000/check-alerts python -m client.main --dry-run
        """,
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        dest="dry_run",
        help="Dry-run mode: print notifications to stdout instead of sending emails, "
        "and don't update notified.json",
    )

    return parser.parse_args(args)


def main() -> int:
    """
    Main entry point for StockMon client.

    This function orchestrates the client workflow:
    1. Parse command-line arguments
    2. Load configuration from config.json
    3. Get API URL (with optional environment variable override)
    4. Display loaded configuration
    5. (Future) Call API, process alerts, send notifications

    Returns:
        int: Exit code (0 for success, 1 for error).
    """
    try:
        # Parse command-line arguments
        args: argparse.Namespace = parse_arguments()

        # Load configuration
        config: Dict[str, Any] = load_config()
        api_url: str = get_api_url(config)

        # Display loaded configuration
        print("StockMon Client Configuration:")
        print(f"  API URL: {api_url}")
        print(f"  Silence Hours: {config['silence_hours']}")
        print(f"  Tickers: {len(config['tickers'])} configured")
        print(
            f"  Mode: {'DRY-RUN (no emails, no notified.json updates)' if args.dry_run else 'PRODUCTION'}"
        )
        print()

        # Display ticker configuration
        print("Configured Tickers:")
        for symbol, thresholds in config["tickers"].items():
            buy_threshold: float = thresholds.get("buy", 0.0)
            sell_threshold: float = thresholds.get("sell", 0.0)
            print(f"  {symbol}: buy=${buy_threshold:.2f}, sell=${sell_threshold:.2f}")

        return 0

    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    except json.JSONDecodeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    except KeyError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    except Exception as exc:  # pylint: disable=W0703
        print(f"ERROR: Unexpected error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

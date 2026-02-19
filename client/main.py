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

import requests


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


def call_api(config: Dict[str, Any]) -> Dict[str, Any]:  # pylint: disable=R0912
    """
    Call the StockMon API to check stock alerts.

    This function sends a POST request to the /check-alerts endpoint with
    ticker thresholds, handles authentication, and implements retry logic
    for transient failures.

    The API call includes:
    - Authentication via X-API-Key header (from API_KEY environment variable)
    - 60 second timeout
    - 1 retry on timeout or connection errors (2 attempts total)
    - Graceful handling of 401, timeout, and connection errors

    Args:
        config: Configuration dictionary containing api_url, silence_hours,
                and tickers with buy/sell thresholds.

    Returns:
        Dict[str, Any]: API response with alerts, errors, market_open,
                        service_degraded, and checked_at fields.

    Raises:
        ValueError: If API_KEY environment variable is missing or empty.
        requests.exceptions.HTTPError: If API returns non-retryable HTTP error (e.g., 401).
        requests.exceptions.Timeout: If request times out after all retries.
        requests.exceptions.ConnectionError: If connection fails after all retries.
        requests.exceptions.RequestException: For other request-related errors.

    Example:
        config = {
            "api_url": "https://stockmon.up.railway.app/check-alerts",
            "tickers": {"AAPL": {"buy": 170.0, "sell": 190.0}}
        }
        response = call_api(config)
        for alert in response["alerts"]:
            print(f"Alert: {alert['ticker']} {alert['type']} at {alert['current']}")
    """
    # Validate API key is present
    api_key: Optional[str] = os.environ.get("API_KEY")
    if not api_key:
        raise ValueError(
            "API_KEY environment variable is required but not set. "
            "Please set API_KEY with your StockMon API authentication key."
        )

    # Get API URL (may be overridden by environment variable)
    api_url: str = get_api_url(config)

    # Prepare request payload from tickers configuration
    # Convert config tickers to API request format
    payload: Dict[str, Dict[str, float]] = config["tickers"]

    # Prepare headers with authentication
    headers: Dict[str, str] = {
        "X-API-Key": api_key,
        "Content-Type": "application/json",
    }

    # Configure timeout (60 seconds as per requirements)
    timeout: int = 60

    # Maximum attempts: initial request + 1 retry = 2 total
    max_attempts: int = 2
    attempt: int = 0

    last_exception: Optional[Exception] = None

    while attempt < max_attempts:
        attempt += 1

        try:
            # Make the API request
            response: requests.Response = requests.post(
                api_url, json=payload, headers=headers, timeout=timeout
            )

            # Handle HTTP errors
            # Note: response.status_code should always be set after a request,
            # but we check for None to satisfy type safety requirements
            if response.status_code is None:
                raise RuntimeError("API response has no status code")

            if response.status_code == 401:
                # Authentication error - don't retry, raise immediately
                response.raise_for_status()

            if response.status_code >= 500:
                # Server error - may be transient, allow retry
                if attempt < max_attempts:
                    continue
                response.raise_for_status()

            if response.status_code >= 400:
                # Other client errors (4xx) - don't retry
                response.raise_for_status()

            # Success - return parsed JSON response
            return response.json()

        except requests.exceptions.Timeout as exc:
            # Timeout - retry once
            last_exception = exc
            if attempt >= max_attempts:
                raise

        except requests.exceptions.ConnectionError as exc:
            # Connection error - retry once
            last_exception = exc
            if attempt >= max_attempts:
                raise

        except requests.exceptions.HTTPError:
            # HTTP error (401, 4xx, 5xx after retries) - don't retry, raise immediately
            raise

        except requests.exceptions.RequestException:  # pylint: disable=W0706
            # Other request exceptions - don't retry, raise immediately
            # W0706 disabled: This explicit handling is intentional to distinguish
            # between retryable errors (Timeout, ConnectionError) and non-retryable
            # RequestException subclasses. The code clarity is worth the verbosity.
            raise

    # Should never reach here, but if we do, raise the last exception
    if last_exception:
        raise last_exception

    # Fallback (should never reach here)
    raise RuntimeError("API call failed with no exception recorded")


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


def main() -> int:  # pylint: disable=R0911,R0912,R0915
    """
    Main entry point for StockMon client.

    This function orchestrates the client workflow:
    1. Parse command-line arguments
    2. Load configuration from config.json
    3. Get API URL (with optional environment variable override)
    4. Display loaded configuration
    5. Call API to check stock alerts
    6. Display API response (alerts, errors, market status)
    7. (Future) Process alerts, send notifications, track notified alerts

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
        print()

        # Call API to check alerts
        print("Calling StockMon API...")
        response: Dict[str, Any] = call_api(config)

        # Display API response
        print(f"API Response received at: {response['checked_at']}")
        print(f"Market Open: {response['market_open']}")
        print(f"Service Degraded: {response['service_degraded']}")
        print()

        # Display alerts
        if response["alerts"]:
            print(f"Alerts ({len(response['alerts'])}):")
            for alert in response["alerts"]:
                alert_type: str = alert["type"].upper()
                print(
                    f"  {alert['ticker']} - {alert_type} alert: "
                    f"threshold=${alert['threshold']:.2f}, "
                    f"reached=${alert['reached']:.2f}, "
                    f"current=${alert['current']:.2f}"
                )
        else:
            print("No alerts triggered.")
        print()

        # Display errors
        if response["errors"]:
            print(f"Errors ({len(response['errors'])}):")
            for error in response["errors"]:
                print(f"  {error['ticker']}: {error['error']}")
            print()

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

    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    except requests.exceptions.HTTPError as exc:
        print(f"ERROR: API request failed with HTTP error: {exc}", file=sys.stderr)
        return 1

    except requests.exceptions.Timeout:
        print(
            "ERROR: API request timed out after 60 seconds (tried 2 times). "
            "Please check your network connection and try again.",
            file=sys.stderr,
        )
        return 1

    except requests.exceptions.ConnectionError as exc:
        print(
            f"ERROR: Failed to connect to API after 2 attempts: {exc}",
            file=sys.stderr,
        )
        return 1

    except requests.exceptions.RequestException as exc:
        print(f"ERROR: API request failed: {exc}", file=sys.stderr)
        return 1

    except Exception as exc:  # pylint: disable=W0703
        print(f"ERROR: Unexpected error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

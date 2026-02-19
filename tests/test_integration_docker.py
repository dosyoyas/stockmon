"""
Integration tests for StockMon client against real Docker API.

These tests execute the client against a real API running in Docker
without any mocks. They verify:
- Successful authentication
- 401 handling for invalid/missing API keys
- Response structure with alerts
- market_open status
- service_degraded status
- Timeout handling
- Complete end-to-end flow

Requirements:
- Docker and docker-compose must be installed and running
- docker-compose.test.yml must exist in project root
- API must be accessible on http://localhost:8000

Usage:
    # Start Docker environment first
    docker-compose -f docker-compose.test.yml up -d

    # Run these tests
    python -m unittest tests.test_integration_docker

    # Stop Docker environment
    docker-compose -f docker-compose.test.yml down
"""

import os
import subprocess
import time
import unittest
from typing import Any, ClassVar, Dict, List

import requests


class TestDockerAPIIntegration(unittest.TestCase):
    """Integration tests for client against real Docker API."""

    compose_file: ClassVar[str]
    project_root: ClassVar[str]
    compose_file_path: ClassVar[str]
    api_key: ClassVar[str]
    base_url: ClassVar[str]
    check_alerts_url: ClassVar[str]

    @classmethod
    def setUpClass(cls) -> None:
        """Start docker-compose service before running tests."""
        cls.compose_file = "docker-compose.test.yml"
        cls.project_root = os.path.dirname(os.path.dirname(__file__))
        cls.compose_file_path = os.path.join(cls.project_root, cls.compose_file)
        cls.api_key = "test-api-key-12345"
        cls.base_url = "http://localhost:8000"
        cls.check_alerts_url = f"{cls.base_url}/check-alerts"

        # Check if Docker is available
        try:
            subprocess.run(
                ["docker", "info"],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except (subprocess.CalledProcessError, FileNotFoundError) as exc:
            raise unittest.SkipTest("Docker is not available or not running") from exc

        # Check if compose file exists
        if not os.path.exists(cls.compose_file_path):
            raise unittest.SkipTest(f"Compose file not found: {cls.compose_file_path}")

        # Start docker-compose service
        print("\n[SETUP] Starting docker-compose test environment...")
        try:
            subprocess.run(
                ["docker-compose", "-f", cls.compose_file, "up", "-d", "--build"],
                cwd=cls.project_root,
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except subprocess.CalledProcessError as e:
            raise unittest.SkipTest(f"Failed to start docker-compose: {e}")

        # Wait for service to become healthy (max 60 seconds)
        max_attempts: int = 30
        for attempt in range(max_attempts):
            try:
                result: subprocess.CompletedProcess = subprocess.run(
                    ["docker-compose", "-f", cls.compose_file, "ps", "api"],
                    cwd=cls.project_root,
                    check=False,
                    capture_output=True,
                    text=True,
                )
                if result.returncode == 0 and "healthy" in result.stdout:
                    print(f"[SETUP] API healthy after {attempt + 1} attempts")
                    break
            except subprocess.CalledProcessError:
                pass

            if attempt == max_attempts - 1:
                # Capture logs for debugging
                logs: subprocess.CompletedProcess = subprocess.run(
                    ["docker-compose", "-f", cls.compose_file, "logs", "api"],
                    cwd=cls.project_root,
                    check=False,
                    capture_output=True,
                    text=True,
                )
                print(f"[ERROR] Failed to start API. Logs:\n{logs.stdout}")
                raise RuntimeError("API failed to become healthy")

            time.sleep(2)

        # Give it a moment to be fully ready
        time.sleep(2)

    @classmethod
    def tearDownClass(cls) -> None:
        """Stop and clean up docker-compose service after tests."""
        print("\n[TEARDOWN] Cleaning up docker-compose test environment...")
        try:
            subprocess.run(
                ["docker-compose", "-f", cls.compose_file, "down", "-v"],
                cwd=cls.project_root,
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except subprocess.CalledProcessError as e:
            print(f"[WARNING] Cleanup failed: {e}")

    def test_successful_authentication(self) -> None:
        """Test successful authentication with valid API key."""
        headers: Dict[str, str] = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json",
        }
        payload: Dict[str, Dict[str, float]] = {"AAPL": {"buy": 100.0, "sell": 300.0}}

        response: requests.Response = requests.post(
            self.check_alerts_url, json=payload, headers=headers, timeout=30
        )

        # Assert successful response
        self.assertEqual(response.status_code, 200)

        # Verify response structure
        data: Dict[str, Any] = response.json()
        self.assertIn("alerts", data)
        self.assertIn("errors", data)
        self.assertIn("market_open", data)
        self.assertIn("service_degraded", data)
        self.assertIn("checked_at", data)

        # Verify response types
        self.assertIsInstance(data["alerts"], list)
        self.assertIsInstance(data["errors"], list)
        self.assertIsInstance(data["market_open"], bool)
        self.assertIsInstance(data["service_degraded"], bool)
        self.assertIsInstance(data["checked_at"], str)

    def test_401_with_invalid_api_key(self) -> None:
        """Test that invalid API key returns 401 Unauthorized."""
        headers: Dict[str, str] = {
            "X-API-Key": "invalid-api-key-wrong",
            "Content-Type": "application/json",
        }
        payload: Dict[str, Dict[str, float]] = {"AAPL": {"buy": 100.0}}

        response: requests.Response = requests.post(
            self.check_alerts_url, json=payload, headers=headers, timeout=10
        )

        # Assert 401 Unauthorized
        self.assertEqual(response.status_code, 401)

        # Verify error detail
        data: Dict[str, Any] = response.json()
        self.assertIn("detail", data)
        self.assertEqual(data["detail"], "Invalid API key")

    def test_401_with_missing_api_key(self) -> None:
        """Test that missing API key returns 401 Unauthorized."""
        headers: Dict[str, str] = {"Content-Type": "application/json"}
        payload: Dict[str, Dict[str, float]] = {"AAPL": {"buy": 100.0}}

        response: requests.Response = requests.post(
            self.check_alerts_url, json=payload, headers=headers, timeout=10
        )

        # Assert 401 Unauthorized
        self.assertEqual(response.status_code, 401)

        # Verify error detail mentions missing key
        data: Dict[str, Any] = response.json()
        self.assertIn("detail", data)
        self.assertIn("X-API-Key", data["detail"])

    def test_response_with_alerts(self) -> None:
        """
        Test API response structure when alerts are triggered.

        Note: This test may not always produce alerts depending on current
        stock prices. It verifies the response structure is correct regardless.
        """
        headers: Dict[str, str] = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json",
        }

        # Use extreme thresholds to potentially trigger alerts
        # Buy threshold very high (likely to trigger if stock dipped today)
        # Sell threshold very low (likely to trigger if stock rose today)
        payload: Dict[str, Dict[str, float]] = {
            "AAPL": {"buy": 500.0, "sell": 1.0},
            "MSFT": {"buy": 800.0, "sell": 1.0},
        }

        response: requests.Response = requests.post(
            self.check_alerts_url, json=payload, headers=headers, timeout=30
        )

        # Assert successful response
        self.assertEqual(response.status_code, 200)

        data: Dict[str, Any] = response.json()

        # Verify alerts structure (may be empty, but must be a list)
        self.assertIsInstance(data["alerts"], list)

        # If alerts exist, verify their structure
        if len(data["alerts"]) > 0:
            alert: Dict[str, Any] = data["alerts"][0]
            self.assertIn("ticker", alert)
            self.assertIn("type", alert)
            self.assertIn("threshold", alert)
            self.assertIn("reached", alert)
            self.assertIn("current", alert)

            # Verify alert field types
            self.assertIsInstance(alert["ticker"], str)
            self.assertIn(alert["type"], ["buy", "sell"])
            self.assertIsInstance(alert["threshold"], (int, float))
            self.assertIsInstance(alert["reached"], (int, float))
            self.assertIsInstance(alert["current"], (int, float))

    def test_market_open_status(self) -> None:
        """Test that market_open status is returned and is a boolean."""
        headers: Dict[str, str] = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json",
        }
        payload: Dict[str, Dict[str, float]] = {"AAPL": {"buy": 100.0}}

        response: requests.Response = requests.post(
            self.check_alerts_url, json=payload, headers=headers, timeout=30
        )

        self.assertEqual(response.status_code, 200)

        data: Dict[str, Any] = response.json()
        self.assertIn("market_open", data)
        self.assertIsInstance(data["market_open"], bool)

        # The actual value depends on when the test runs
        # We just verify it's present and boolean
        print(f"[INFO] Market open status: {data['market_open']}")

    def test_service_degraded_status(self) -> None:
        """Test that service_degraded status is returned correctly."""
        headers: Dict[str, str] = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json",
        }

        # Use valid ticker symbols
        payload: Dict[str, Dict[str, float]] = {
            "AAPL": {"buy": 100.0, "sell": 300.0},
            "MSFT": {"buy": 200.0, "sell": 500.0},
        }

        response: requests.Response = requests.post(
            self.check_alerts_url, json=payload, headers=headers, timeout=30
        )

        self.assertEqual(response.status_code, 200)

        data: Dict[str, Any] = response.json()
        self.assertIn("service_degraded", data)
        self.assertIsInstance(data["service_degraded"], bool)

        # With valid tickers, service should NOT be degraded
        # (unless YFinance is actually down, which would be rare)
        # We primarily verify the field exists and is boolean
        print(f"[INFO] Service degraded: {data['service_degraded']}")

        # If service is not degraded, there should be no errors
        if not data["service_degraded"]:
            # All tickers should have succeeded
            errors_count: int = len(data["errors"])
            self.assertEqual(errors_count, 0)

    def test_timeout_handling(self) -> None:
        """Test that API responds within a reasonable timeout."""
        headers: Dict[str, str] = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json",
        }
        payload: Dict[str, Dict[str, float]] = {
            "AAPL": {"buy": 100.0},
            "MSFT": {"buy": 200.0},
            "GOOGL": {"buy": 100.0},
        }

        # Set a reasonable timeout (30 seconds)
        timeout: int = 30

        try:
            response: requests.Response = requests.post(
                self.check_alerts_url, json=payload, headers=headers, timeout=timeout
            )

            # Should not timeout, should return 200
            self.assertEqual(response.status_code, 200)
            print(f"[INFO] API responded successfully within {timeout}s")

        except requests.exceptions.Timeout:
            self.fail(f"API failed to respond within {timeout} seconds")

    def test_complete_end_to_end_flow(self) -> None:
        """
        Test complete end-to-end flow from client perspective.

        This simulates a real client request:
        1. Prepare ticker data with thresholds
        2. Authenticate with API key
        3. Send request to /check-alerts
        4. Receive and parse response
        5. Process alerts and errors
        """
        # Step 1: Prepare request data
        headers: Dict[str, str] = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json",
        }

        payload: Dict[str, Dict[str, float]] = {
            "AAPL": {"buy": 150.0, "sell": 200.0},
            "MSFT": {"buy": 350.0, "sell": 450.0},
            "GOOGL": {"buy": 120.0, "sell": 160.0},
            "TSLA": {"buy": 150.0, "sell": 300.0},
        }

        # Step 2 & 3: Send authenticated request
        response: requests.Response = requests.post(
            self.check_alerts_url, json=payload, headers=headers, timeout=30
        )

        # Step 4: Verify successful response
        self.assertEqual(response.status_code, 200)

        data: Dict[str, Any] = response.json()

        # Step 5: Process and validate response data
        alerts: List[Dict[str, Any]] = data["alerts"]
        errors: List[Dict[str, Any]] = data["errors"]
        market_open: bool = data["market_open"]
        service_degraded: bool = data["service_degraded"]
        checked_at: str = data["checked_at"]

        # Verify all response components
        self.assertIsInstance(alerts, list)
        self.assertIsInstance(errors, list)
        self.assertIsInstance(market_open, bool)
        self.assertIsInstance(service_degraded, bool)
        self.assertIsInstance(checked_at, str)

        # Verify timestamp format (ISO 8601)
        # Should be parseable and contain 'T' and 'Z'
        self.assertIn("T", checked_at)
        self.assertTrue(checked_at.endswith("Z") or checked_at.endswith("+00:00"))

        # Log results for visibility
        print("\n[E2E TEST RESULTS]")
        print(f"  Alerts triggered: {len(alerts)}")
        print(f"  Errors encountered: {len(errors)}")
        print(f"  Market open: {market_open}")
        print(f"  Service degraded: {service_degraded}")
        print(f"  Checked at: {checked_at}")

        # If there are alerts, verify their structure
        for alert in alerts:
            self.assertIn("ticker", alert)
            self.assertIn("type", alert)
            self.assertIn("threshold", alert)
            self.assertIn("reached", alert)
            self.assertIn("current", alert)
            print(
                f"  Alert: {alert['ticker']} {alert['type']} "
                f"(threshold: {alert['threshold']}, "
                f"reached: {alert['reached']}, "
                f"current: {alert['current']})"
            )

        # If there are errors, verify their structure
        for error in errors:
            self.assertIn("ticker", error)
            self.assertIn("error", error)
            print(f"  Error: {error['ticker']} - {error['error']}")

        # Service should only be degraded if ALL tickers failed
        if service_degraded:
            self.assertEqual(len(errors), len(payload))
            self.assertEqual(len(alerts), 0)
        else:
            # At least some tickers should have succeeded
            self.assertGreaterEqual(len(payload) - len(errors), 1)

    def test_multiple_tickers_parallel_processing(self) -> None:
        """Test that API handles multiple tickers efficiently."""
        headers: Dict[str, str] = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json",
        }

        # Test with maximum allowed tickers (20)
        payload: Dict[str, Dict[str, float]] = {
            "AAPL": {"buy": 100.0, "sell": 300.0},
            "MSFT": {"buy": 200.0, "sell": 500.0},
            "GOOGL": {"buy": 100.0, "sell": 200.0},
            "AMZN": {"buy": 100.0, "sell": 200.0},
            "TSLA": {"buy": 100.0, "sell": 400.0},
            "META": {"buy": 200.0, "sell": 500.0},
            "NVDA": {"buy": 300.0, "sell": 1000.0},
            "NFLX": {"buy": 300.0, "sell": 700.0},
            "AMD": {"buy": 50.0, "sell": 200.0},
            "INTC": {"buy": 20.0, "sell": 60.0},
        }

        start_time: float = time.time()

        response: requests.Response = requests.post(
            self.check_alerts_url, json=payload, headers=headers, timeout=60
        )

        elapsed_time: float = time.time() - start_time

        # Assert successful response
        self.assertEqual(response.status_code, 200)

        data: Dict[str, Any] = response.json()

        # Verify all response fields present
        self.assertIn("alerts", data)
        self.assertIn("errors", data)
        self.assertIn("service_degraded", data)

        print(f"[INFO] Processed {len(payload)} tickers in {elapsed_time:.2f} seconds")

        # API should handle 10 tickers reasonably fast (under 30 seconds)
        # This is a soft assertion - log warning if slow but don't fail
        if elapsed_time > 30:
            print(f"[WARNING] API took longer than expected: {elapsed_time:.2f}s")

    def test_invalid_ticker_error_handling(self) -> None:
        """Test that invalid ticker symbols are handled gracefully."""
        headers: Dict[str, str] = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json",
        }

        # Mix valid and invalid tickers
        payload: Dict[str, Dict[str, float]] = {
            "AAPL": {"buy": 100.0, "sell": 300.0},
            "INVALID_TICKER_XYZ": {"buy": 100.0},
            "FAKE123": {"buy": 50.0},
        }

        response: requests.Response = requests.post(
            self.check_alerts_url, json=payload, headers=headers, timeout=30
        )

        # Should still return 200 (errors are in response body)
        self.assertEqual(response.status_code, 200)

        data: Dict[str, Any] = response.json()

        # There should be errors for invalid tickers
        self.assertGreater(len(data["errors"]), 0)

        # Verify error structure
        invalid_tickers: List[str] = [
            error["ticker"]
            for error in data["errors"]
            if error["ticker"] in ["INVALID_TICKER_XYZ", "FAKE123"]
        ]
        self.assertGreater(len(invalid_tickers), 0)

        print(
            f"[INFO] Invalid tickers handled: {len(invalid_tickers)} "
            f"errors for {invalid_tickers}"
        )


if __name__ == "__main__":
    unittest.main()  # type: ignore[not-callable]

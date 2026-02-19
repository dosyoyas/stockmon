"""
Integration tests for docker-compose.test.yml setup.

These tests verify that the docker-compose test environment:
- Starts successfully
- Becomes healthy
- Responds to API requests
- Handles authentication correctly
- Cleans up properly

Note: These tests require Docker and docker-compose to be installed.
"""

import os
import subprocess
import time
import unittest

import requests


class TestDockerComposeIntegration(unittest.TestCase):
    """Integration tests for docker-compose test environment."""

    @classmethod
    def setUpClass(cls) -> None:
        """Start docker-compose service before running tests."""
        compose_file: str = "docker-compose.test.yml"
        project_root: str = os.path.dirname(os.path.dirname(__file__))
        cls.compose_file_path: str = os.path.join(project_root, compose_file)
        cls.api_key: str = "test-api-key-12345"
        cls.base_url: str = "http://localhost:8000"

        # Check if Docker is available
        try:
            subprocess.run(
                ["docker", "info"],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise unittest.SkipTest("Docker is not available or not running")

        # Check if compose file exists
        if not os.path.exists(cls.compose_file_path):
            raise unittest.SkipTest(f"Compose file not found: {cls.compose_file_path}")

        # Start docker-compose service
        print("\nStarting docker-compose test environment...")
        subprocess.run(
            ["docker-compose", "-f", compose_file, "up", "-d", "--build"],
            cwd=project_root,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        # Wait for service to become healthy (max 60 seconds)
        max_attempts: int = 30
        for attempt in range(max_attempts):
            try:
                result: subprocess.CompletedProcess = subprocess.run(
                    ["docker-compose", "-f", compose_file, "ps", "api"],
                    cwd=project_root,
                    check=True,
                    capture_output=True,
                    text=True,
                )
                if "healthy" in result.stdout:
                    print(f"API healthy after {attempt + 1} attempts")
                    break
            except subprocess.CalledProcessError:
                pass

            if attempt == max_attempts - 1:
                # Capture logs for debugging
                logs: subprocess.CompletedProcess = subprocess.run(
                    ["docker-compose", "-f", compose_file, "logs", "api"],
                    cwd=project_root,
                    capture_output=True,
                    text=True,
                )
                print(f"Failed to start API. Logs:\n{logs.stdout}")
                raise RuntimeError("API failed to become healthy")

            time.sleep(2)

        # Give it a moment to be fully ready
        time.sleep(2)

    @classmethod
    def tearDownClass(cls) -> None:
        """Stop and clean up docker-compose service after tests."""
        compose_file: str = "docker-compose.test.yml"
        project_root: str = os.path.dirname(os.path.dirname(__file__))

        print("\nCleaning up docker-compose test environment...")
        try:
            subprocess.run(
                ["docker-compose", "-f", compose_file, "down", "-v"],
                cwd=project_root,
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except subprocess.CalledProcessError as e:
            print(f"Warning: Cleanup failed: {e}")

    def test_health_endpoint(self) -> None:
        """Test that /health endpoint returns 200 OK."""
        response: requests.Response = requests.get(f"{self.base_url}/health", timeout=5)

        self.assertEqual(response.status_code, 200)
        data: dict = response.json()
        self.assertEqual(data["status"], "ok")

    def test_root_endpoint(self) -> None:
        """Test that root endpoint returns API information."""
        response: requests.Response = requests.get(f"{self.base_url}/", timeout=5)

        self.assertEqual(response.status_code, 200)
        data: dict = response.json()
        self.assertIn("name", data)
        self.assertIn("StockMon", data["name"])
        self.assertIn("version", data)
        self.assertIn("description", data)

    def test_authenticated_endpoint_success(self) -> None:
        """Test that authenticated endpoint works with correct API key."""
        headers: dict = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json",
        }
        payload: dict = {"AAPL": {"buy": 100.0, "sell": 300.0}}

        response: requests.Response = requests.post(
            f"{self.base_url}/check-alerts", json=payload, headers=headers, timeout=30
        )

        self.assertEqual(response.status_code, 200)
        data: dict = response.json()
        self.assertIn("alerts", data)
        self.assertIn("errors", data)
        self.assertIn("market_open", data)
        self.assertIn("service_degraded", data)
        self.assertIn("checked_at", data)

    def test_authenticated_endpoint_failure(self) -> None:
        """Test that authenticated endpoint rejects invalid API key."""
        headers: dict = {
            "X-API-Key": "wrong-api-key",
            "Content-Type": "application/json",
        }
        payload: dict = {"AAPL": {"buy": 100.0}}

        response: requests.Response = requests.post(
            f"{self.base_url}/check-alerts", json=payload, headers=headers, timeout=5
        )

        self.assertEqual(response.status_code, 401)
        data: dict = response.json()
        self.assertIn("detail", data)
        self.assertEqual(data["detail"], "Invalid API key")

    def test_authenticated_endpoint_missing_key(self) -> None:
        """Test that authenticated endpoint rejects requests without API key."""
        headers: dict = {"Content-Type": "application/json"}
        payload: dict = {"AAPL": {"buy": 100.0}}

        response: requests.Response = requests.post(
            f"{self.base_url}/check-alerts", json=payload, headers=headers, timeout=5
        )

        self.assertEqual(response.status_code, 401)
        data: dict = response.json()
        self.assertIn("detail", data)
        # API returns full error message explaining the requirement
        self.assertIn("X-API-Key", data["detail"])
        self.assertIn("header", data["detail"].lower())

    def test_container_health_check(self) -> None:
        """Test that container health check is functioning."""
        project_root: str = os.path.dirname(os.path.dirname(__file__))

        result: subprocess.CompletedProcess = subprocess.run(
            ["docker-compose", "-f", "docker-compose.test.yml", "ps", "api"],
            cwd=project_root,
            check=True,
            capture_output=True,
            text=True,
        )

        self.assertIn("healthy", result.stdout.lower())

    def test_port_mapping(self) -> None:
        """Test that port 8000 is correctly mapped."""
        project_root: str = os.path.dirname(os.path.dirname(__file__))

        result: subprocess.CompletedProcess = subprocess.run(
            [
                "docker",
                "ps",
                "--filter",
                "name=stockmon-test-api",
                "--format",
                "{{.Ports}}",
            ],
            cwd=project_root,
            check=True,
            capture_output=True,
            text=True,
        )

        ports: str = result.stdout.strip()
        self.assertIn("8000", ports)
        self.assertIn("0.0.0.0", ports)


if __name__ == "__main__":
    unittest.main()

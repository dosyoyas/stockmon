"""
Unit tests for docker-compose.test.yml configuration.

Tests verify:
- Service definition exists and is correctly configured
- Environment variables are properly set
- Health check is configured correctly
- Port mapping is correct
- Build context and Dockerfile are correct
"""

import os
import unittest
from typing import Any, Dict

import yaml


class TestDockerComposeConfig(unittest.TestCase):
    """Test docker-compose.test.yml configuration."""

    def setUp(self) -> None:
        """Load docker-compose.test.yml file."""
        compose_file: str = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "docker-compose.test.yml"
        )
        self.assertTrue(
            os.path.exists(compose_file),
            f"docker-compose.test.yml not found at {compose_file}",
        )

        with open(compose_file, "r", encoding="utf-8") as f:
            self.compose_config: Dict[str, Any] = yaml.safe_load(f)

    def test_compose_version(self) -> None:
        """Test that docker-compose version is specified."""
        self.assertIn("version", self.compose_config)
        version: str = self.compose_config["version"]
        self.assertIn(version, ["3.8", "3.9", "3"])

    def test_services_exist(self) -> None:
        """Test that services section exists."""
        self.assertIn("services", self.compose_config)
        services: Dict[str, Any] = self.compose_config["services"]
        self.assertIsInstance(services, dict)

    def test_api_service_exists(self) -> None:
        """Test that 'api' service is defined."""
        services: Dict[str, Any] = self.compose_config["services"]
        self.assertIn("api", services)

    def test_api_service_build_config(self) -> None:
        """Test that api service has correct build configuration."""
        api_service: Dict[str, Any] = self.compose_config["services"]["api"]

        # Verify build section exists
        self.assertIn("build", api_service)
        build_config: Dict[str, Any] = api_service["build"]

        # Verify context is current directory
        self.assertIn("context", build_config)
        self.assertEqual(build_config["context"], ".")

        # Verify Dockerfile.test is used
        self.assertIn("dockerfile", build_config)
        self.assertEqual(build_config["dockerfile"], "Dockerfile.test")

    def test_api_service_port_mapping(self) -> None:
        """Test that port 8000 is correctly mapped."""
        api_service: Dict[str, Any] = self.compose_config["services"]["api"]

        self.assertIn("ports", api_service)
        ports: list = api_service["ports"]
        self.assertIsInstance(ports, list)
        self.assertGreater(len(ports), 0)

        # Check for 8000:8000 mapping
        port_mapping: str = ports[0]
        self.assertIn("8000:8000", port_mapping)

    def test_api_service_environment_variables(self) -> None:
        """Test that required environment variables are configured."""
        api_service: Dict[str, Any] = self.compose_config["services"]["api"]

        self.assertIn("environment", api_service)
        env_vars: list = api_service["environment"]
        self.assertIsInstance(env_vars, list)

        # Convert list to dict for easier testing
        env_dict: Dict[str, str] = {}
        for env_var in env_vars:
            if "=" in env_var:
                key, value = env_var.split("=", 1)
                env_dict[key] = value

        # Verify API_KEY is present
        self.assertIn("API_KEY", env_dict)

        # Verify Python optimization variables
        self.assertIn("PYTHONUNBUFFERED", env_dict)
        self.assertEqual(env_dict["PYTHONUNBUFFERED"], "1")

        self.assertIn("PYTHONDONTWRITEBYTECODE", env_dict)
        self.assertEqual(env_dict["PYTHONDONTWRITEBYTECODE"], "1")

    def test_api_service_health_check(self) -> None:
        """Test that health check is properly configured."""
        api_service: Dict[str, Any] = self.compose_config["services"]["api"]

        self.assertIn("healthcheck", api_service)
        healthcheck: Dict[str, Any] = api_service["healthcheck"]

        # Verify health check test command
        self.assertIn("test", healthcheck)
        test_cmd: list = healthcheck["test"]
        self.assertIsInstance(test_cmd, list)
        self.assertIn("curl", test_cmd)
        self.assertIn("http://localhost:8000/health", test_cmd)

        # Verify health check timing parameters
        self.assertIn("interval", healthcheck)
        self.assertIn("timeout", healthcheck)
        self.assertIn("retries", healthcheck)
        self.assertIn("start_period", healthcheck)

        # Verify reasonable values
        interval: str = healthcheck["interval"]
        self.assertTrue(interval.endswith("s"), "Interval should be in seconds")

        retries: int = healthcheck["retries"]
        self.assertGreater(retries, 0, "Should have at least 1 retry")

    def test_api_service_container_name(self) -> None:
        """Test that container has a meaningful name."""
        api_service: Dict[str, Any] = self.compose_config["services"]["api"]

        self.assertIn("container_name", api_service)
        container_name: str = api_service["container_name"]
        self.assertIsInstance(container_name, str)
        self.assertIn("stockmon", container_name.lower())
        self.assertIn("test", container_name.lower())

    def test_dockerfile_test_exists(self) -> None:
        """Test that Dockerfile.test exists in project root."""
        dockerfile: str = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "Dockerfile.test"
        )
        self.assertTrue(
            os.path.exists(dockerfile), f"Dockerfile.test not found at {dockerfile}"
        )


if __name__ == "__main__":
    unittest.main()

"""
StockMon API - Authentication Integration Tests.

This module provides integration tests for API key authentication,
verifying that the auth middleware works correctly with the main
FastAPI application when it exists.
"""

from typing import Generator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


class TestAuthIntegration:
    """Integration tests for authentication with the main FastAPI app."""

    @pytest.fixture
    def integration_app(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> Generator[FastAPI, None, None]:
        """
        Load the main FastAPI application if it exists.

        Args:
            monkeypatch: Pytest's monkeypatch fixture.

        Yields:
            FastAPI: The main application instance.
        """
        # Set API_KEY for the application
        monkeypatch.setenv("API_KEY", "integration-test-key-67890")

        try:
            # Try to import the main app
            from app.main import app  # type: ignore[import-not-found]

            yield app
        except ImportError:
            # If main app doesn't exist yet, skip these tests
            pytest.skip("Main FastAPI app not yet implemented (app.main)")

    @pytest.fixture
    def integration_client(
        self, integration_app: FastAPI
    ) -> Generator[TestClient, None, None]:
        """
        Create a test client for the main application.

        Args:
            integration_app: The main FastAPI application.

        Yields:
            TestClient: A test client for the application.
        """
        yield TestClient(integration_app)

    def test_main_app_requires_authentication(
        self, integration_client: TestClient
    ) -> None:
        """Test that the main app's endpoints require authentication."""
        # Try to access an endpoint without authentication
        # This assumes the main app has a /check-alerts endpoint
        response = integration_client.post("/check-alerts", json={"AAPL": {"buy": 170}})

        # Should return 401 Unauthorized
        assert response.status_code == 401
        json_response = response.json()
        assert "Missing API key" in json_response["detail"]

    def test_main_app_accepts_valid_api_key(
        self, integration_client: TestClient
    ) -> None:
        """Test that the main app accepts valid API keys."""
        # Make request with valid API key
        response = integration_client.post(
            "/check-alerts",
            json={"AAPL": {"buy": 170}},
            headers={"X-API-Key": "integration-test-key-67890"},
        )

        # Should NOT return 401 (may return other codes based on implementation)
        assert response.status_code != 401

        # If it's a validation error (422), that's fine - auth passed
        # If it's 200, that's also fine - request succeeded
        # If it's 500, that might be a different issue but auth passed
        assert response.status_code in [200, 422, 500, 503]

    def test_main_app_rejects_invalid_api_key(
        self, integration_client: TestClient
    ) -> None:
        """Test that the main app rejects invalid API keys."""
        # Make request with invalid API key
        response = integration_client.post(
            "/check-alerts",
            json={"AAPL": {"buy": 170}},
            headers={"X-API-Key": "invalid-key-wrong"},
        )

        # Should return 401 Unauthorized
        assert response.status_code == 401
        json_response = response.json()
        assert "Invalid API key" in json_response["detail"]

    def test_health_endpoint_public_if_exists(
        self, integration_client: TestClient
    ) -> None:
        """Test that health check endpoint is public (if it exists)."""
        # Try to access health endpoint without authentication
        response = integration_client.get("/health")

        # Health endpoint should be public (200) or not exist (404)
        # Should NOT return 401 Unauthorized
        assert response.status_code in [200, 404]

    def test_docs_endpoint_public(self, integration_client: TestClient) -> None:
        """Test that API documentation endpoints remain public."""
        # FastAPI provides /docs and /openapi.json by default
        # These should be public (not require auth)
        docs_response = integration_client.get("/docs")
        assert docs_response.status_code == 200

        openapi_response = integration_client.get("/openapi.json")
        assert openapi_response.status_code == 200

    def test_authentication_with_real_endpoints(
        self, integration_client: TestClient
    ) -> None:
        """
        Test authentication with real endpoint logic.

        This test verifies that authentication works correctly with
        the actual endpoint implementation, not just test stubs.

        Args:
            integration_client: Test client for the main app.
        """
        # Valid request with authentication
        response = integration_client.post(
            "/check-alerts",
            json={"AAPL": {"buy": 170.0, "sell": 190.0}},
            headers={"X-API-Key": "integration-test-key-67890"},
        )

        # Should succeed (200) or return a valid error (not 401)
        assert response.status_code != 401

        # If we get 200, validate the response structure
        if response.status_code == 200:
            json_response = response.json()
            assert "alerts" in json_response
            assert "errors" in json_response
            assert "market_open" in json_response
            assert "service_degraded" in json_response
            assert "checked_at" in json_response

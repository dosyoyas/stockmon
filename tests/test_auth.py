"""
StockMon API - Authentication Unit Tests.

This module tests the API key authentication middleware for the StockMon API.
Tests cover various authentication scenarios including valid keys, missing keys,
invalid keys, and edge cases.
"""

from typing import Generator

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.auth import require_api_key


class TestRequireApiKey:
    """Test the require_api_key authentication dependency."""

    @pytest.fixture
    def test_app(self) -> FastAPI:
        """
        Create a minimal FastAPI app for testing authentication.

        Returns:
            FastAPI: A test FastAPI application with protected endpoint.
        """
        app: FastAPI = FastAPI()

        @app.get("/protected")
        async def protected_endpoint(
            api_key: str = Depends(require_api_key),
        ) -> dict[str, str]:
            """Protected endpoint that requires authentication."""
            return {"message": "success", "api_key_received": api_key}

        @app.get("/public")
        async def public_endpoint() -> dict[str, str]:
            """Public endpoint that does not require authentication."""
            return {"message": "public"}

        return app

    @pytest.fixture
    def test_client(
        self, test_app: FastAPI, monkeypatch: pytest.MonkeyPatch
    ) -> Generator[TestClient, None, None]:
        """
        Create a test client with API_KEY environment variable set.

        Args:
            test_app: The test FastAPI application.
            monkeypatch: Pytest's monkeypatch fixture.

        Yields:
            TestClient: A configured test client.
        """
        # Set API_KEY environment variable
        monkeypatch.setenv("API_KEY", "test-secret-key-12345")
        yield TestClient(test_app)

    def test_valid_api_key_grants_access(self, test_client: TestClient) -> None:
        """Test that valid API key in X-API-Key header grants access."""
        response = test_client.get(
            "/protected", headers={"X-API-Key": "test-secret-key-12345"}
        )
        assert response.status_code == 200
        assert response.json()["message"] == "success"

    def test_missing_api_key_header_returns_401(self, test_client: TestClient) -> None:
        """Test that missing X-API-Key header returns 401 Unauthorized."""
        response = test_client.get("/protected")
        assert response.status_code == 401
        json_response = response.json()
        assert "Missing API key" in json_response["detail"]
        assert "X-API-Key" in json_response["detail"]

    def test_invalid_api_key_returns_401(self, test_client: TestClient) -> None:
        """Test that invalid API key returns 401 Unauthorized."""
        response = test_client.get("/protected", headers={"X-API-Key": "wrong-key"})
        assert response.status_code == 401
        json_response = response.json()
        assert json_response["detail"] == "Invalid API key"

    def test_empty_api_key_header_returns_401(self, test_client: TestClient) -> None:
        """Test that empty X-API-Key header returns 401 Unauthorized."""
        response = test_client.get("/protected", headers={"X-API-Key": ""})
        assert response.status_code == 401
        json_response = response.json()
        assert json_response["detail"] == "Invalid API key"

    def test_whitespace_only_api_key_returns_401(self, test_client: TestClient) -> None:
        """Test that whitespace-only API key returns 401 Unauthorized."""
        response = test_client.get("/protected", headers={"X-API-Key": "   "})
        assert response.status_code == 401
        json_response = response.json()
        assert json_response["detail"] == "Invalid API key"

    def test_case_sensitive_api_key(self, test_client: TestClient) -> None:
        """Test that API key comparison is case-sensitive."""
        response = test_client.get(
            "/protected", headers={"X-API-Key": "TEST-SECRET-KEY-12345"}
        )
        assert response.status_code == 401
        json_response = response.json()
        assert json_response["detail"] == "Invalid API key"

    def test_public_endpoint_accessible_without_auth(
        self, test_client: TestClient
    ) -> None:
        """Test that public endpoints remain accessible without authentication."""
        response = test_client.get("/public")
        assert response.status_code == 200
        assert response.json()["message"] == "public"

    def test_missing_api_key_env_var_raises_error(
        self, test_app: FastAPI, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that missing API_KEY environment variable returns 500 error."""
        # Remove API_KEY environment variable
        monkeypatch.delenv("API_KEY", raising=False)

        # When API_KEY is missing, the dependency should return 500 Internal Server Error
        client: TestClient = TestClient(test_app)
        response = client.get("/protected", headers={"X-API-Key": "any-key"})
        assert response.status_code == 500
        json_response = response.json()
        assert "API_KEY environment variable not set" in json_response["detail"]

    def test_header_name_is_case_insensitive(self, test_client: TestClient) -> None:
        """Test that HTTP header names are case-insensitive (HTTP spec)."""
        # HTTP headers are case-insensitive per RFC 7230
        response = test_client.get(
            "/protected", headers={"x-api-key": "test-secret-key-12345"}
        )
        assert response.status_code == 200
        assert response.json()["message"] == "success"

    def test_multiple_api_key_headers_uses_first(self, test_client: TestClient) -> None:
        """Test behavior when multiple X-API-Key headers are sent."""
        # FastAPI/Starlette uses the first occurrence of duplicate headers
        response = test_client.get(
            "/protected",
            headers=[
                ("X-API-Key", "test-secret-key-12345"),
                ("X-API-Key", "wrong-key"),
            ],
        )
        # Should succeed using the first (valid) key
        assert response.status_code == 200

    def test_api_key_with_special_characters(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that API keys with special characters work correctly."""
        # Set API key with special characters
        special_key: str = "key-with-special_chars!@#$%^&*()+={}[]|:;<>?,./~`"
        monkeypatch.setenv("API_KEY", special_key)

        app: FastAPI = FastAPI()

        @app.get("/test")
        async def test_endpoint(
            _api_key: str = Depends(require_api_key),
        ) -> dict[str, str]:
            """Test endpoint."""
            return {"message": "success"}

        client: TestClient = TestClient(app)
        response = client.get("/test", headers={"X-API-Key": special_key})
        assert response.status_code == 200

    def test_api_key_dependency_returns_key_value(
        self, test_client: TestClient
    ) -> None:
        """Test that the dependency returns the API key value when valid."""
        response = test_client.get(
            "/protected", headers={"X-API-Key": "test-secret-key-12345"}
        )
        assert response.status_code == 200
        json_response = response.json()
        # The endpoint returns the received API key
        assert json_response["api_key_received"] == "test-secret-key-12345"

    def test_very_long_api_key(self, test_client: TestClient) -> None:
        """Test that very long API keys are handled correctly."""
        # Test with a very long but invalid key
        long_key: str = "a" * 10000
        response = test_client.get("/protected", headers={"X-API-Key": long_key})
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid API key"

    def test_api_key_with_unicode_characters(self, test_client: TestClient) -> None:
        """Test that API keys with unicode characters cause HTTP errors."""
        # Unicode characters in HTTP headers violate HTTP spec (must be ASCII)
        # This will fail at the HTTP client level, not at auth validation level
        unicode_key: str = "test-key-with-émojis-😀"
        with pytest.raises(UnicodeEncodeError):
            # This should fail when trying to encode the header
            test_client.get("/protected", headers={"X-API-Key": unicode_key})

    def test_null_byte_in_api_key(self, test_client: TestClient) -> None:
        """Test that API keys containing null bytes are rejected."""
        malicious_key: str = "test-key\x00-with-null"
        response = test_client.get("/protected", headers={"X-API-Key": malicious_key})
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid API key"

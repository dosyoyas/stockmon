"""
StockMon API - Authentication Module.

This module provides API key authentication for the StockMon API using FastAPI
security dependencies. The API key is validated against the API_KEY environment
variable and must be provided in the X-API-Key HTTP header.

Security Design:
- API key stored securely in environment variable (not hardcoded)
- Constant-time comparison to prevent timing attacks
- Clear 401 Unauthorized responses for authentication failures
- Works as a FastAPI dependency for easy integration

Usage:
    from app.auth import require_api_key
    from fastapi import FastAPI, Depends

    app = FastAPI()

    @app.get("/protected")
    async def protected_route(api_key: str = Depends(require_api_key)):
        return {"message": "Access granted"}
"""

import os
import secrets
from typing import Optional

from fastapi import Header, HTTPException, status


def get_api_key_from_env() -> str:
    """
    Retrieve the API key from environment variables.

    This function reads the API_KEY environment variable and validates that it exists.
    It should be called once at module import time or application startup.

    Returns:
        str: The API key from the environment.

    Raises:
        ValueError: If API_KEY environment variable is not set or is empty.

    Example:
        >>> os.environ["API_KEY"] = "my-secret-key"
        >>> key = get_api_key_from_env()
        >>> assert key == "my-secret-key"
    """
    api_key: Optional[str] = os.getenv("API_KEY")

    if not api_key or not api_key.strip():
        raise ValueError(
            "API_KEY environment variable not set. "
            "Please set API_KEY in your .env file or environment."
        )

    return api_key.strip()


def require_api_key(x_api_key: Optional[str] = Header(None, alias="X-API-Key")) -> str:
    """
    FastAPI dependency for API key authentication.

    This function validates the X-API-Key header against the API_KEY environment
    variable. It uses constant-time comparison to prevent timing attacks.

    Args:
        x_api_key: The API key from the X-API-Key HTTP header.
                   FastAPI automatically extracts this from the request headers.

    Returns:
        str: The validated API key if authentication succeeds.

    Raises:
        HTTPException: 401 Unauthorized if the API key is missing or invalid.

    Security Notes:
        - Uses secrets.compare_digest() for constant-time comparison
        - Prevents timing attacks that could reveal valid key length or content
        - HTTP headers are case-insensitive per RFC 7230 (handled by FastAPI)

    Example:
        @app.get("/alerts")
        async def get_alerts(api_key: str = Depends(require_api_key)):
            # This endpoint is now protected by API key authentication
            return {"data": "protected content"}

        # Valid request:
        # curl -H "X-API-Key: valid-key" http://localhost:8000/alerts

        # Invalid request (missing header):
        # curl http://localhost:8000/alerts
        # Response: 401 {"detail": "Missing API key"}

        # Invalid request (wrong key):
        # curl -H "X-API-Key: wrong-key" http://localhost:8000/alerts
        # Response: 401 {"detail": "Invalid API key"}
    """
    # Get the expected API key from environment
    try:
        expected_key: str = get_api_key_from_env()
    except ValueError as e:
        # Re-raise as HTTPException so FastAPI can handle it properly
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from e

    # Check if API key header is missing
    if x_api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Please provide X-API-Key header.",
        )

    # Normalize the provided key (strip whitespace)
    provided_key: str = x_api_key.strip()

    # Check if API key is empty after stripping whitespace
    if not provided_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )

    # Use constant-time comparison to prevent timing attacks
    # secrets.compare_digest returns True only if both strings are equal
    # and takes constant time regardless of where the difference is
    if not secrets.compare_digest(provided_key, expected_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )

    # Authentication successful - return the validated key
    return provided_key

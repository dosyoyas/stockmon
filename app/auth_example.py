"""
StockMon API - Authentication Usage Example.

This file demonstrates how to use the API key authentication middleware
in FastAPI endpoints. This is a reference implementation showing the
recommended patterns for protecting endpoints.

DO NOT run this file directly - it's for documentation purposes only.
The actual application should be in app/main.py.
"""

from typing import Dict

from fastapi import Depends, FastAPI

from app.auth import require_api_key
from app.models import AlertRequest, AlertResponse

# Create FastAPI application instance
app: FastAPI = FastAPI(
    title="StockMon API",
    description="Stock price monitoring API with threshold alerts",
    version="1.0.0",
)


# Example 1: Public endpoint (no authentication required)
@app.get("/health")
async def health_check() -> Dict[str, str]:
    """
    Public health check endpoint.

    This endpoint does not require authentication and can be accessed
    by anyone. Useful for monitoring, load balancers, and health checks.

    Returns:
        Dict[str, str]: Health status.
    """
    return {"status": "healthy", "service": "stockmon-api"}


# Example 2: Protected endpoint (authentication required)
@app.post("/check-alerts", response_model=AlertResponse)
async def check_alerts(
    request: AlertRequest,
    api_key: str = Depends(require_api_key),
) -> AlertResponse:
    """
    Check stock prices against thresholds and return alerts.

    This endpoint requires authentication via the X-API-Key header.
    The api_key parameter is automatically validated by the require_api_key
    dependency. If authentication fails, FastAPI will return 401 before
    this function is called.

    Args:
        request: Alert request with ticker symbols and thresholds.
        api_key: Validated API key (automatically injected by FastAPI).

    Returns:
        AlertResponse: Alert response with triggered alerts and errors.

    Example Request:
        curl -X POST http://localhost:8000/check-alerts \\
             -H "Content-Type: application/json" \\
             -H "X-API-Key: your-secret-api-key" \\
             -d '{"AAPL": {"buy": 170.0, "sell": 190.0}}'

    Example Response:
        {
            "alerts": [
                {
                    "ticker": "AAPL",
                    "type": "buy",
                    "threshold": 170.0,
                    "reached": 168.5,
                    "current": 172.3
                }
            ],
            "errors": [],
            "market_open": true,
            "service_degraded": false,
            "checked_at": "2024-02-06T14:30:00Z"
        }
    """
    # Note: We don't use api_key in the function body, but it's validated
    # by the dependency before this function is called. If you need to log
    # or track which API key was used, you can access it here.

    # Actual implementation would go here
    # For now, this is just an example skeleton
    raise NotImplementedError("Endpoint implementation goes in app/main.py")


# Example 3: Alternative pattern - manual validation (NOT RECOMMENDED)
# This shows what NOT to do. Always use Depends(require_api_key) instead.
#
# ❌ DON'T DO THIS - Manual header extraction is error-prone:
# from fastapi import Header
#
# @app.post("/bad-example")
# async def bad_authentication_pattern(x_api_key: str = Header(...)) -> dict:
#     # Manual validation is:
#     # - Less secure (may forget constant-time comparison)
#     # - More code to maintain
#     # - Easy to get wrong
#     # - Not reusable across endpoints
#     expected_key = os.getenv("API_KEY")
#     if x_api_key != expected_key:  # ⚠️ Timing attack vulnerability!
#         raise HTTPException(status_code=401, detail="Invalid API key")
#     return {"message": "Don't use this pattern!"}
#
# ✅ DO THIS INSTEAD - Use the dependency:
# @app.post("/good-example")
# async def good_authentication_pattern(
#     api_key: str = Depends(require_api_key)
# ) -> dict:
#     # Authentication is handled automatically
#     # Secure, tested, reusable
#     return {"message": "This is the correct way!"}


# Example 4: Multiple dependencies (auth + other validations)
@app.get("/admin/stats")
async def admin_stats(
    _api_key: str = Depends(require_api_key),
    # You can add more dependencies here:
    # user_role: str = Depends(check_admin_role),
    # rate_limit: None = Depends(rate_limiter),
) -> Dict[str, int]:
    """
    Admin-only endpoint showing service statistics.

    This demonstrates how authentication can be combined with other
    FastAPI dependencies for role-based access control, rate limiting, etc.

    Args:
        api_key: Validated API key.

    Returns:
        Dict[str, int]: Service statistics.
    """
    # Implementation would check if this API key has admin privileges
    # and return statistics
    return {
        "total_requests": 12345,
        "active_users": 42,
        "cache_hits": 98765,
    }


if __name__ == "__main__":
    # This example file should not be run directly
    # Use app/main.py for the actual application
    print("This is an example file for documentation purposes.")
    print("Do not run it directly. See app/main.py for the actual app.")

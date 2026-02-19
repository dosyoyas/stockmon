# StockMon

A stock price monitoring system with threshold-based alerts. StockMon consists of a FastAPI backend service that monitors stock prices against configurable buy/sell thresholds, and a Python client for Raspberry Pi that sends email notifications when alerts are triggered.

## Features

- **Real-time Stock Monitoring**: Tracks 24-hour price ranges (min, max, current) for configured ticker symbols
- **Threshold-Based Alerts**: Configurable buy and sell price thresholds per ticker
- **Email Notifications**: Automatic email alerts when thresholds are breached
- **Market Hours Detection**: Identifies NYSE trading hours (Monday-Friday, 9:30 AM - 4:00 PM ET)
- **Alert Deduplication**: Silence period prevents notification spam for the same alert
- **API Authentication**: Secure API key-based authentication via X-API-Key header
- **Service Health Monitoring**: Tracks API availability and YFinance data service status
- **Batch Processing**: Supports up to 20 tickers per API request
- **Graceful Error Handling**: Individual ticker failures don't prevent processing of other tickers

## Tech Stack

### Backend (API)
- **FastAPI**: Modern, fast web framework for building APIs
- **Uvicorn**: ASGI server with production-ready performance
- **YFinance**: Real-time stock market data from Yahoo Finance
- **Pydantic**: Data validation and settings management
- **PyTZ**: Timezone-aware datetime handling for market hours

### Client (Raspberry Pi)
- **Requests**: HTTP client for API communication
- **SMTP**: Email delivery via configurable SMTP server (Gmail, etc.)
- **JSON**: Configuration management for tickers and thresholds

### Development
- **Pytest**: Testing framework with fixtures and parametrization
- **Coverage**: Code coverage analysis
- **Black**: Code formatting
- **isort**: Import sorting
- **Pylint**: Code linting
- **Flake8**: Style checking

## Project Structure

```
stockmon/
├── app/                          # FastAPI backend application
│   ├── main.py                  # FastAPI app, endpoints, market hours logic
│   ├── models.py                # Pydantic models for validation
│   ├── auth.py                  # API key authentication
│   └── services/
│       └── stock.py             # YFinance integration, stock data fetching
├── client/                       # Raspberry Pi client application
│   ├── main.py                  # Client orchestration, API calls
│   ├── email.py                 # Email notification sending
│   ├── notified.py              # Alert deduplication tracking
│   ├── config.json              # Client configuration (tickers, thresholds)
│   └── notified.json            # Tracked alert state (auto-generated)
├── tests/                        # Comprehensive test suite
│   ├── conftest.py              # Pytest fixtures and configuration
│   ├── test_*.py                # Unit tests
│   └── test_*_integration.py    # Integration tests
├── .env.example                  # Environment variables template
├── requirements.txt              # Production dependencies
├── requirements-dev.txt          # Development dependencies
├── Procfile                      # Railway deployment configuration
└── DEPLOYMENT_RAILWAY.md         # Railway deployment guide

```

## Development Setup

### Prerequisites

- Python 3.11 or higher
- pip (Python package manager)
- Git

### 1. Clone the Repository

```bash
git clone https://github.com/dosyoyas/stockmon.git
cd stockmon
```

### 2. Create Virtual Environment

```bash
python -m venv venv
```

### 3. Activate Virtual Environment

**macOS/Linux:**
```bash
source venv/bin/activate
```

**Windows:**
```bash
venv\Scripts\activate
```

### 4. Install Dependencies

**Production dependencies:**
```bash
pip install -r requirements.txt
```

**Development dependencies (includes testing tools):**
```bash
pip install -r requirements-dev.txt
```

### 5. Configure Environment Variables

Copy the example environment file and configure your settings:

```bash
cp .env.example .env
```

Edit `.env` and configure the following:

```bash
# API Key for authentication (generate with: python -c "import secrets; print(secrets.token_urlsafe(32))")
API_KEY=your-secret-api-key-here

# SMTP Configuration (for client email notifications)
SMTP_HOST=smtp.gmail.com
SMTP_USER=your-email@gmail.com
SMTP_PASS=your-app-password-here
NOTIFY_EMAIL=recipient@example.com

# API URL Override (optional, for local testing)
# API_URL=http://localhost:8000/check-alerts
```

**Note**: For Gmail SMTP, you need to:
1. Enable 2FA on your Google account
2. Generate an App Password at https://myaccount.google.com/apppasswords
3. Use the 16-character app password (not your regular password)

### 6. Configure Client Tickers (for Client Usage)

Edit `client/config.json` to configure your stock monitoring thresholds:

```json
{
  "api_url": "https://stockmon.up.railway.app/check-alerts",
  "silence_hours": 48,
  "tickers": {
    "AAPL": {
      "buy": 170,
      "sell": 190
    },
    "MSFT": {
      "buy": 400,
      "sell": 420
    }
  }
}
```

- `api_url`: Your deployed API endpoint (or `http://localhost:8000/check-alerts` for local testing)
- `silence_hours`: Hours to wait before re-notifying for the same alert (prevents spam)
- `tickers`: Dictionary of ticker symbols with buy/sell thresholds

### 7. Run the API Server

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at:
- API: http://localhost:8000
- Interactive docs: http://localhost:8000/docs
- Alternative docs: http://localhost:8000/redoc

### 8. Run the Client

**Production mode (sends emails, updates notified.json):**
```bash
python -m client.main
```

**Dry-run mode (prints to stdout, no emails, no state updates):**
```bash
python -m client.main --dry-run
```

**Test against local API:**
```bash
API_URL=http://localhost:8000/check-alerts python -m client.main --dry-run
```

## Testing

### Run All Tests

```bash
pytest
```

### Run with Coverage Report

```bash
pytest --cov=app --cov=client --cov-report=html --cov-report=term
```

View HTML coverage report:
```bash
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

### Run Specific Test Categories

**Unit tests only:**
```bash
pytest tests/ -k "not integration"
```

**Integration tests only:**
```bash
pytest tests/ -k "integration"
```

**Specific test file:**
```bash
pytest tests/test_main.py -v
```

### Test Structure

- **Unit Tests**: Test individual functions and classes in isolation
  - `tests/test_*.py` (without `_integration` suffix)
  - Mock external dependencies (YFinance, SMTP, API calls)
  - Fast execution (suitable for TDD)

- **Integration Tests**: Test component interactions and external services
  - `tests/test_*_integration.py`
  - Use real or simulated external services
  - Validate end-to-end workflows

## API Endpoints

### POST /check-alerts

Check stock price alerts for configured tickers.

**Authentication**: Required (X-API-Key header)

**Request Body**:
```json
{
  "AAPL": {"buy": 170.0, "sell": 190.0},
  "MSFT": {"buy": 400.0}
}
```

**Response**:
```json
{
  "alerts": [
    {
      "ticker": "AAPL",
      "type": "buy",
      "threshold": 170.0,
      "reached": 168.50,
      "current": 172.30
    }
  ],
  "errors": [],
  "market_open": true,
  "service_degraded": false,
  "checked_at": "2024-02-06T14:30:00Z"
}
```

**Alert Logic**:
- **Buy Alert**: Triggered if 24h minimum price <= buy threshold
- **Sell Alert**: Triggered if 24h maximum price >= sell threshold
- A ticker can trigger both alerts if highly volatile

**Error Handling**:
- Individual ticker failures don't fail the entire request
- Errors are returned in the `errors` array
- `service_degraded: true` if ALL tickers fail (likely YFinance API issue)

### GET /health

Health check endpoint (no authentication required).

**Response**:
```json
{"status": "ok"}
```

Used by hosting providers (e.g., Railway) to monitor service availability.

### GET /

API information endpoint.

**Response**:
```json
{
  "name": "StockMon API",
  "version": "1.0.0",
  "description": "Stock price monitoring API with threshold alerts"
}
```

## Deployment

### Railway Deployment

See [DEPLOYMENT_RAILWAY.md](./DEPLOYMENT_RAILWAY.md) for detailed instructions on deploying the API to Railway.

**Quick Summary**:
1. Create a Railway project and connect your GitHub repository
2. Set the `API_KEY` environment variable in Railway
3. Railway automatically deploys using the `Procfile`
4. Access your API at `https://your-app.railway.app`

**Environment Variables**:
- `API_KEY`: Secret key for authentication (required)
- `PORT`: Automatically set by Railway (do not override)

### Raspberry Pi Client Setup

1. Install Python 3.11+ on your Raspberry Pi
2. Clone the repository and install dependencies
3. Configure `.env` with SMTP credentials
4. Edit `client/config.json` with your tickers and thresholds
5. Set up a cron job to run the client periodically:

```bash
# Run every 15 minutes
*/15 * * * * cd /path/to/stockmon && /path/to/venv/bin/python -m client.main
```

## Configuration Files

### .env (Environment Variables)

Contains sensitive credentials and configuration:
- `API_KEY`: Authentication key for API access
- `SMTP_*`: Email server configuration
- `NOTIFY_EMAIL`: Recipient for alert emails
- `API_URL`: Optional API endpoint override

**Security**: Never commit `.env` to version control (already in `.gitignore`)

### client/config.json (Client Configuration)

Contains client behavior and ticker configuration:
- `api_url`: API endpoint URL
- `silence_hours`: Cooldown period before re-notifying same alert
- `tickers`: Dictionary of ticker symbols with buy/sell thresholds

### client/notified.json (Alert State)

Auto-generated file tracking already-notified alerts:
- Prevents duplicate notifications during silence period
- Automatically created and updated by the client
- Can be deleted to reset notification state

## Architecture

### Alert Processing Flow

1. **Client** periodically calls API with configured tickers
2. **API** fetches 24-hour price data from YFinance for each ticker
3. **API** checks if price breached buy/sell thresholds
4. **API** returns alerts and errors to client
5. **Client** checks if alerts were recently notified (via `notified.json`)
6. **Client** sends email notifications for new alerts
7. **Client** updates `notified.json` to prevent re-notification

### Market Hours Detection

- NYSE trading hours: Monday-Friday, 9:30 AM - 4:00 PM Eastern Time
- Excludes weekends (automatically detected)
- Does NOT check market holidays (production system would need holiday calendar)
- Timezone-aware using PyTZ

### Error Handling Strategy

- **API Level**: Individual ticker failures don't fail the entire request
- **Client Level**: Retry logic for transient failures (timeout, connection errors)
- **Service Degradation**: `service_degraded` flag when ALL tickers fail
- **Authentication**: 401 errors are not retried
- **Timeouts**: 10 seconds per ticker (YFinance), 60 seconds for API request

## Contributing

### Code Quality Standards

This project enforces strict code quality standards:

- **Type Hints**: Required on all functions, methods, and variables
- **Black**: Code formatting (line length: 88)
- **isort**: Import sorting (Black-compatible profile)
- **Pylint**: Linting with project-specific disable flags
- **Flake8**: Style checking with project-specific ignore flags
- **100% Test Coverage Goal**: Comprehensive unit and integration tests

### Development Workflow

1. Create a feature branch from `main`
2. Implement feature with tests (TDD approach)
3. Run tests and ensure they pass: `pytest`
4. Run coverage check: `pytest --cov=app --cov=client`
5. Format code: `black . && isort .`
6. Lint code: `pylint app/ client/ tests/`
7. Commit changes with descriptive message
8. Create pull request to `main`

## License

This project is private. All rights reserved.

## Support

For issues, questions, or feature requests, please open an issue on GitHub or contact the project maintainers.

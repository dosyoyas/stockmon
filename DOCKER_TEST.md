# Dockerfile.test Documentation

## Overview

The `Dockerfile.test` provides a containerized environment for running the StockMon API during integration testing. It creates a production-like Docker image with all necessary dependencies for testing the API endpoints.

## Image Specifications

- **Base Image**: `python:3.11-slim`
- **Working Directory**: `/app`
- **Exposed Port**: `8000`
- **User**: Non-root user `stockmon` (UID 1000)
- **Health Check**: Automated health monitoring via `/health` endpoint

## Features

### Security Best Practices

1. **Non-root User**: Runs as `stockmon` user (UID 1000) for security
2. **Minimal Base Image**: Uses `python:3.11-slim` to reduce attack surface
3. **No Cache**: Prevents storing sensitive data in image layers

### Performance Optimizations

1. **Layer Caching**: Requirements copied before application code for efficient rebuilds
2. **Minimal System Dependencies**: Only installs necessary packages (curl for health checks)
3. **Cleanup**: Removes apt lists to reduce image size

### Docker Best Practices

1. **Multi-stage Optimization**: Requirements installed before code copy
2. **Health Check**: Built-in health monitoring
3. **Environment Variables**: Prevents Python bytecode and enables unbuffered output

## Usage

### Building the Image

```bash
docker build -f Dockerfile.test -t stockmon-api-test:latest .
```

### Running the Container

```bash
# Start the API container
docker run -d --name stockmon-test -p 8000:8000 stockmon-api-test:latest

# Check container logs
docker logs stockmon-test

# Verify health
curl http://localhost:8000/health
```

### Using in Integration Tests

```bash
# Start container in background
docker run -d --name stockmon-test -p 8000:8000 stockmon-api-test:latest

# Wait for startup
sleep 5

# Run integration tests
pytest tests/test_*_integration.py

# Cleanup
docker stop stockmon-test
docker rm stockmon-test
```

### Example Test Script

See `docker-test-example.sh` for a complete example of building, running, and testing the containerized API.

```bash
./docker-test-example.sh
```

## Environment Variables

The following environment variables are set in the container:

- `PYTHONUNBUFFERED=1`: Ensures Python output is sent directly to stdout/stderr
- `PYTHONDONTWRITEBYTECODE=1`: Prevents Python from writing .pyc files

### Additional Environment Variables (Optional)

You can override these at runtime using `-e` flag:

```bash
docker run -d --name stockmon-test \
  -p 8000:8000 \
  -e API_KEY_SECRET=test-key \
  -e LOG_LEVEL=DEBUG \
  stockmon-api-test:latest
```

## Health Checks

The container includes an automated health check that:

- Runs every 30 seconds
- Times out after 10 seconds
- Waits 5 seconds before starting checks
- Retries 3 times before marking unhealthy
- Tests the `/health` endpoint

Check container health status:

```bash
docker inspect --format='{{.State.Health.Status}}' stockmon-test
```

## Troubleshooting

### Container Won't Start

```bash
# Check container logs
docker logs stockmon-test

# Check if port is already in use
lsof -i :8000
```

### API Not Responding

```bash
# Verify container is running
docker ps | grep stockmon-test

# Check health status
docker inspect --format='{{.State.Health.Status}}' stockmon-test

# View detailed logs
docker logs -f stockmon-test
```

### Permission Issues

The container runs as non-root user `stockmon` (UID 1000). If you encounter permission issues when mounting volumes:

```bash
# Run with correct user
docker run -d --name stockmon-test \
  -p 8000:8000 \
  --user 1000:1000 \
  stockmon-api-test:latest
```

## Image Size

The image is approximately 400MB and includes:

- Python 3.11 runtime
- FastAPI and uvicorn
- YFinance and dependencies
- Minimal system utilities (curl)

## Cleanup

```bash
# Stop and remove container
docker stop stockmon-test
docker rm stockmon-test

# Remove image
docker rmi stockmon-api-test:latest

# Clean up all stopped containers and unused images
docker system prune -a
```

## Integration with CI/CD

Example GitHub Actions workflow:

```yaml
name: Integration Tests

on: [push, pull_request]

jobs:
  integration-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Build test image
        run: docker build -f Dockerfile.test -t stockmon-api-test:latest .

      - name: Start API container
        run: docker run -d --name stockmon-test -p 8000:8000 stockmon-api-test:latest

      - name: Wait for API
        run: sleep 5

      - name: Run integration tests
        run: |
          pip install pytest requests
          pytest tests/test_*_integration.py

      - name: Cleanup
        if: always()
        run: |
          docker stop stockmon-test || true
          docker rm stockmon-test || true
```

## Dependencies

All dependencies are installed from `requirements.txt`:

- `fastapi>=0.129.0,<1.0.0` - Web framework
- `uvicorn[standard]>=0.41.0,<1.0.0` - ASGI server
- `yfinance>=1.2.0,<2.0.0` - Stock market data
- `requests>=2.32.5,<3.0.0` - HTTP requests
- `python-dotenv>=1.2.1,<2.0.0` - Configuration management
- `pydantic>=2.12.5,<3.0.0` - Data validation
- `pytz>=2024.2` - Timezone support

## Notes

- The Dockerfile.test is designed specifically for integration testing
- Production deployments should use a separate production Dockerfile with additional security hardening
- The container does not include development dependencies from `requirements-dev.txt`
- API authentication requires setting appropriate environment variables for production use

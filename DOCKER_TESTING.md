# Docker-Based Integration Testing Guide

This guide explains how to use `docker-compose.test.yml` for running integration tests against a containerized StockMon API.

## Overview

The `docker-compose.test.yml` file provides a complete testing environment that:

1. Builds the StockMon API using `Dockerfile.test`
2. Starts the API service with test-specific configuration
3. Provides health checks to ensure API readiness
4. Exposes the API on port 8000 for test execution
5. Allows running integration tests against the live API

## Quick Start

### Automated Testing (Recommended)

Use the provided script for automated test execution:

```bash
# Run all integration tests
./run-integration-tests.sh

# Use custom API key
API_KEY=my-custom-key ./run-integration-tests.sh
```

The script will:
- Start the API service
- Wait for health check to pass
- Run integration tests
- Clean up containers automatically

### Manual Testing

For manual control over the test environment:

```bash
# Step 1: Start the API service
docker-compose -f docker-compose.test.yml up -d --build

# Step 2: Wait for health check (check status)
docker-compose -f docker-compose.test.yml ps

# Step 3: Verify API is healthy
curl http://localhost:8000/health

# Step 4: Run integration tests
export API_KEY=test-api-key-12345
export API_URL=http://localhost:8000/check-alerts
pytest tests/test_*_integration.py -v

# Step 5: Clean up
docker-compose -f docker-compose.test.yml down -v
```

## Configuration

### Environment Variables

The `docker-compose.test.yml` supports the following environment variables:

| Variable | Default Value | Description |
|----------|---------------|-------------|
| `API_KEY` | `test-api-key-12345` | API authentication key for tests |
| `PYTHONUNBUFFERED` | `1` | Disable Python output buffering |
| `PYTHONDONTWRITEBYTECODE` | `1` | Prevent `.pyc` file generation |

#### Overriding Environment Variables

You can override environment variables in multiple ways:

**1. Environment variable at runtime:**
```bash
API_KEY=custom-key docker-compose -f docker-compose.test.yml up -d
```

**2. .env file:**
Create a `.env` file in the project root:
```bash
API_KEY=custom-key
```

**3. Docker Compose CLI:**
```bash
docker-compose -f docker-compose.test.yml up -d --env API_KEY=custom-key
```

### Health Check

The API service includes a health check that:

- **Test Command**: `curl -f http://localhost:8000/health`
- **Interval**: 10 seconds
- **Timeout**: 5 seconds
- **Retries**: 5 attempts
- **Start Period**: 10 seconds grace period

The service is considered healthy when the `/health` endpoint returns HTTP 200.

### Port Mapping

- **Host Port**: 8000
- **Container Port**: 8000
- **Access**: `http://localhost:8000`

If port 8000 is already in use, modify the port mapping:

```yaml
ports:
  - "8001:8000"  # Maps host port 8001 to container port 8000
```

Then access the API at `http://localhost:8001`.

## Integration Test Workflow

### 1. Service Startup

```bash
docker-compose -f docker-compose.test.yml up -d --build
```

This command:
- Builds the image from `Dockerfile.test`
- Starts the `api` service in detached mode
- Configures environment variables
- Begins health check monitoring

### 2. Health Check Verification

Wait for the service to become healthy:

```bash
# Check service status
docker-compose -f docker-compose.test.yml ps

# Expected output when healthy:
# NAME                 STATUS
# stockmon-test-api    Up (healthy)
```

You can also watch the logs during startup:

```bash
docker-compose -f docker-compose.test.yml logs -f api
```

### 3. Run Integration Tests

Once the API is healthy, run your integration tests:

```bash
# Run all integration tests
pytest tests/test_*_integration.py -v

# Run specific integration test
pytest tests/test_client_api_integration.py -v

# Run with coverage
pytest tests/test_*_integration.py --cov=app --cov-report=html
```

### 4. Cleanup

Always clean up containers after testing:

```bash
# Stop and remove containers
docker-compose -f docker-compose.test.yml down

# Remove containers and volumes
docker-compose -f docker-compose.test.yml down -v
```

## Troubleshooting

### API Not Starting

**Problem**: Container starts but health check never passes.

**Solutions**:

1. Check container logs:
   ```bash
   docker-compose -f docker-compose.test.yml logs api
   ```

2. Verify Dockerfile.test exists:
   ```bash
   ls -l Dockerfile.test
   ```

3. Check port availability:
   ```bash
   lsof -i :8000  # macOS/Linux
   ```

### Health Check Failures

**Problem**: Health check repeatedly fails.

**Solutions**:

1. Test health endpoint manually:
   ```bash
   docker exec stockmon-test-api curl http://localhost:8000/health
   ```

2. Check if uvicorn is running:
   ```bash
   docker exec stockmon-test-api ps aux | grep uvicorn
   ```

3. Increase health check timing:
   ```yaml
   healthcheck:
     interval: 15s
     timeout: 10s
     retries: 10
     start_period: 20s
   ```

### Port Already in Use

**Problem**: Port 8000 is already bound.

**Solutions**:

1. Find and stop the conflicting process:
   ```bash
   lsof -ti:8000 | xargs kill -9  # macOS/Linux
   ```

2. Use a different port:
   ```yaml
   ports:
     - "8001:8000"
   ```

### Integration Tests Fail to Connect

**Problem**: Tests can't reach the API at `http://localhost:8000`.

**Solutions**:

1. Verify container is running and healthy:
   ```bash
   docker-compose -f docker-compose.test.yml ps
   ```

2. Test connectivity:
   ```bash
   curl -v http://localhost:8000/health
   ```

3. Ensure `API_URL` environment variable is set:
   ```bash
   export API_URL=http://localhost:8000/check-alerts
   pytest tests/test_*_integration.py -v
   ```

## Advanced Usage

### Running Tests Inside Container

You can also run tests inside the container:

```bash
# Start API service
docker-compose -f docker-compose.test.yml up -d

# Run tests inside container
docker exec stockmon-test-api pytest tests/test_*_integration.py -v

# Cleanup
docker-compose -f docker-compose.test.yml down
```

### Debugging Failed Tests

```bash
# Start API in foreground (shows logs)
docker-compose -f docker-compose.test.yml up

# In another terminal, run tests
pytest tests/test_*_integration.py -v -s

# Logs will appear in the first terminal
```

### Continuous Integration

Example GitHub Actions workflow:

```yaml
name: Integration Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install -r requirements-dev.txt

      - name: Start API service
        run: docker-compose -f docker-compose.test.yml up -d --build

      - name: Wait for API health
        run: |
          for i in {1..30}; do
            if docker-compose -f docker-compose.test.yml ps api | grep -q "healthy"; then
              echo "API is healthy"
              break
            fi
            echo "Waiting for API health check... ($i/30)"
            sleep 2
          done

      - name: Run integration tests
        env:
          API_KEY: test-api-key-12345
          API_URL: http://localhost:8000/check-alerts
        run: pytest tests/test_*_integration.py -v

      - name: Cleanup
        if: always()
        run: docker-compose -f docker-compose.test.yml down -v
```

## Best Practices

1. **Always clean up**: Use `docker-compose down -v` to remove containers and volumes
2. **Use the automation script**: `run-integration-tests.sh` handles setup and cleanup automatically
3. **Wait for health check**: Don't run tests until the service is healthy
4. **Set environment variables**: Ensure `API_KEY` and `API_URL` are properly configured
5. **Check logs on failure**: Use `docker-compose logs api` to diagnose issues
6. **Isolate test runs**: Run one test suite at a time to avoid port conflicts
7. **Use meaningful API keys**: Generate secure keys for different environments

## Related Files

- `Dockerfile.test` - Container image definition for test environment
- `docker-compose.test.yml` - Service orchestration configuration
- `run-integration-tests.sh` - Automated test execution script
- `tests/test_*_integration.py` - Integration test suite
- `tests/test_docker_compose.py` - Configuration validation tests

## Additional Resources

- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Docker Health Checks](https://docs.docker.com/engine/reference/builder/#healthcheck)
- [FastAPI Testing Guide](https://fastapi.tiangolo.com/tutorial/testing/)
- [Pytest Documentation](https://docs.pytest.org/)

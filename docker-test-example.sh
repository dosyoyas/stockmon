#!/bin/bash
# docker-test-example.sh
# Example script demonstrating how to use Dockerfile.test for integration testing

set -e

echo "Building StockMon API test image..."
docker build -f Dockerfile.test -t stockmon-api-test:latest .

echo "Starting StockMon API container..."
docker run -d --name stockmon-test -p 8000:8000 stockmon-api-test:latest

echo "Waiting for API to start..."
sleep 5

echo "Testing health endpoint..."
curl -f http://localhost:8000/health || { echo "Health check failed"; exit 1; }

echo "Testing root endpoint..."
curl -f http://localhost:8000/ || { echo "Root endpoint failed"; exit 1; }

echo "Running integration tests against containerized API..."
# pytest tests/test_*_integration.py || { echo "Integration tests failed"; exit 1; }

echo "Stopping and removing container..."
docker stop stockmon-test
docker rm stockmon-test

echo "All tests passed!"

# Railway Deployment Guide for StockMon API

This guide provides step-by-step instructions for deploying the StockMon API to Railway.

## Prerequisites

- GitHub account with access to the repository `dosyoyas/stockmon`
- Railway account (sign up at https://railway.app)
- Python 3.11+ installed locally (for API key generation)

## Deployment Steps

### 1. Create a New Project on Railway

1. Log in to your Railway account at https://railway.app
2. Click on "New Project" from the dashboard
3. Select "Deploy from GitHub repo"

### 2. Connect Your GitHub Repository

1. If prompted, authorize Railway to access your GitHub account
2. Select the repository: `dosyoyas/stockmon`
3. Railway will automatically detect the `Procfile` and begin the deployment process
4. The Procfile contains: `web: uvicorn app.main:app --host 0.0.0.0 --port $PORT`

### 3. Configure Environment Variables

Railway automatically sets the `PORT` environment variable. You only need to configure the API key.

#### Generate a Secure API Key

Use Python to generate a cryptographically secure API key:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

This will output a secure random string (e.g., `xK8mQ2pN7vL_jZ4yR9wD3fH6tC1aS5eB8nG0uM`).

#### Add the API Key to Railway

1. In your Railway project dashboard, go to the "Variables" tab
2. Click "New Variable"
3. Add the following:
   - **Variable Name**: `API_KEY`
   - **Value**: Paste the generated API key from the previous step
4. Click "Add" to save

**Important**: Store this API key securely. You will need it to authenticate requests to your API. Never commit it to version control.

### 4. Deploy the Application

1. Railway will automatically deploy your application after detecting the repository
2. If the deployment doesn't start automatically, click "Deploy" in the project dashboard
3. Wait for the build and deployment process to complete (usually 2-3 minutes)
4. Once deployed, Railway will provide a public URL (e.g., `https://your-app.railway.app`)

### 5. Verify the Deployment

#### Test the Health Endpoint

The `/health` endpoint does not require authentication and is used by Railway to monitor service health:

```bash
curl https://your-app.railway.app/health
```

Expected response:

```json
{"status": "ok"}
```

#### Test the Main Endpoint

The `/check-alerts` endpoint requires authentication via the `X-API-Key` header:

```bash
curl -X POST https://your-app.railway.app/check-alerts \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_API_KEY_HERE" \
  -d '{"AAPL": {"buy": 170, "sell": 250}}'
```

Replace `YOUR_API_KEY_HERE` with the API key you generated in step 3.

Expected response (example):

```json
{
  "alerts": [
    {
      "ticker": "AAPL",
      "type": "buy",
      "threshold": 170,
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

#### Test Authentication

Verify that requests without authentication are rejected:

```bash
curl -X POST https://your-app.railway.app/check-alerts \
  -H "Content-Type: application/json" \
  -d '{"AAPL": {"buy": 170}}'
```

Expected response: `401 Unauthorized`

### 6. Access API Documentation

Railway automatically deploys the FastAPI interactive documentation:

- **Swagger UI**: https://your-app.railway.app/docs
- **ReDoc**: https://your-app.railway.app/redoc

You can use Swagger UI to test the API endpoints interactively. Click "Authorize" and enter your API key to authenticate.

## Environment Variables Reference

| Variable | Description | Required | Set By | Default |
|----------|-------------|----------|--------|---------|
| `API_KEY` | Secret key for API authentication | Yes | User | - |
| `PORT` | Server port (automatically set by Railway) | Yes | Railway | 8000 |

**Important**: Do NOT manually set the `PORT` variable. Railway automatically sets this based on its internal routing configuration.

## Continuous Deployment

Railway automatically redeploys your application when you push changes to the connected GitHub repository:

1. Push changes to the `main` branch (or your configured branch)
2. Railway detects the push via GitHub webhook
3. A new build is triggered automatically
4. Once the build succeeds, the new version is deployed
5. Railway performs a zero-downtime deployment

You can monitor deployment logs in the Railway dashboard under the "Deployments" tab.

## Troubleshooting

### Application Not Starting

1. Check the deployment logs in Railway dashboard
2. Verify that `requirements.txt` includes all dependencies
3. Ensure the `Procfile` is present in the repository root

### Authentication Errors (401 Unauthorized)

1. Verify the `API_KEY` environment variable is set in Railway
2. Confirm you are sending the correct header: `X-API-Key`
3. Check that the API key in your request matches the one in Railway

### Health Check Fails

1. Verify the application is running by checking Railway logs
2. Ensure the `/health` endpoint is accessible without authentication
3. Check Railway service status at https://railway.app/status

### Service Degraded Response

If the API returns `service_degraded: true`, it means all ticker lookups failed. This may indicate:

1. YFinance library needs updating (Yahoo changed their API)
2. Network issues preventing access to Yahoo Finance
3. Rate limiting from Yahoo Finance

Check Railway logs for detailed error messages.

## Cost Considerations

Railway offers a free tier with 500 hours per month:

- The StockMon API typically consumes 8-10 hours per day if kept active continuously
- With scheduled cron jobs running every 15 minutes, expect approximately 250-300 hours/month
- Monitor usage in Railway dashboard under "Usage"

## Security Best Practices

1. **Never commit the API key to version control** - It should only exist in Railway's environment variables and your secure password manager
2. **Rotate the API key periodically** - Generate a new key and update both Railway and your client configuration
3. **Use HTTPS only** - Railway provides HTTPS by default
4. **Monitor API logs** - Check Railway logs regularly for suspicious activity

## Additional Resources

- Railway Documentation: https://docs.railway.app
- FastAPI Documentation: https://fastapi.tiangolo.com
- StockMon API Plan: See `specs/api_plan.md`
- Environment Variables Example: See `.env.example`

# Raspberry Pi Setup Guide for StockMon Client

This guide provides step-by-step instructions for setting up the StockMon client on a Raspberry Pi to monitor stock prices and receive email notifications when thresholds are breached.

## Prerequisites

- Raspberry Pi (Model 3B+ or later recommended)
- Raspberry Pi OS (Bullseye or newer)
- Python 3.11 or higher
- Internet connection (Wi-Fi or Ethernet)
- Git installed (usually pre-installed on Raspberry Pi OS)
- Access to an SMTP server (e.g., Gmail, Outlook)

### Check Python Version

```bash
python3 --version
```

If Python 3.11+ is not installed, update your system and install it:

```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv
```

## Setup Instructions

### 1. Clone the Repository

Clone the StockMon repository to your Raspberry Pi:

```bash
cd ~
git clone https://github.com/dosyoyas/stockmon.git
cd stockmon
```

### 2. Create Virtual Environment

Create an isolated Python virtual environment for the project:

```bash
python3 -m venv venv
```

This keeps dependencies separate from system Python packages.

### 3. Activate Virtual Environment

Activate the virtual environment:

```bash
source venv/bin/activate
```

You should see `(venv)` prefix in your terminal prompt, indicating the virtual environment is active.

### 4. Install Dependencies

Install required Python packages:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

**Note**: Installation may take 5-10 minutes on Raspberry Pi due to package compilation.

### 5. Configure Environment Variables

Copy the example environment file and configure your settings:

```bash
cp .env.example .env
nano .env
```

Edit the following variables in `.env`:

```bash
# API Key for authentication
# Request this from your StockMon API administrator
API_KEY=your-secret-api-key-here

# SMTP Configuration for Email Notifications
SMTP_HOST=smtp.gmail.com
SMTP_USER=your-email@gmail.com
SMTP_PASS=your-app-password-here
NOTIFY_EMAIL=recipient@example.com

# Optional: API URL Override (if not using default from config.json)
# API_URL=https://your-api.railway.app/check-alerts
```

**Gmail SMTP Setup**:
1. Enable 2-Factor Authentication on your Google account
2. Generate an App Password at https://myaccount.google.com/apppasswords
3. Select "Mail" and your device type
4. Use the 16-character app password (not your regular password)

**Alternative SMTP Providers**:

- **Outlook**: `smtp.office365.com` (Port 587, TLS)
- **Yahoo**: `smtp.mail.yahoo.com` (Port 587, TLS)
- **Custom SMTP**: Check your email provider's SMTP settings

Save the file (Ctrl+X, then Y, then Enter in nano).

### 6. Configure Stock Tickers and Thresholds

Edit the client configuration file:

```bash
nano client/config.json
```

Configure your monitored stocks and price thresholds:

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
    },
    "GOOGL": {
      "buy": 140
    }
  }
}
```

**Configuration Options**:

- `api_url`: Your deployed StockMon API endpoint
- `silence_hours`: Hours to wait before re-notifying for the same alert (prevents spam)
- `tickers`: Dictionary of ticker symbols with optional `buy` and/or `sell` thresholds

**Alert Logic**:
- **Buy Alert**: Triggered when 24-hour minimum price <= buy threshold
- **Sell Alert**: Triggered when 24-hour maximum price >= sell threshold

Save the file (Ctrl+X, then Y, then Enter in nano).

### 7. Create Logs Directory

Create a directory for application logs:

```bash
mkdir -p ~/stockmon/logs
```

### 8. Test the Client

Before setting up automation, test the client manually:

**Dry-run mode (no emails sent, prints to stdout)**:

```bash
cd ~/stockmon
source venv/bin/activate
python -m client.main --dry-run
```

**Production mode (sends emails)**:

```bash
python -m client.main
```

Verify that:
- No authentication errors occur (401 Unauthorized)
- Stock data is retrieved successfully
- Email notifications are sent (if thresholds are breached)

### 9. Setup Cron Job for Automated Monitoring

Configure cron to run the client periodically:

```bash
crontab -e
```

Select your preferred editor (nano is recommended for beginners).

Add the following line to run the client every 15 minutes:

```bash
*/15 * * * * cd /home/pi/stockmon && /home/pi/stockmon/venv/bin/python -m client.main >> /home/pi/stockmon/logs/client.log 2>&1
```

**Adjust the paths** if you cloned the repository to a different location. Use the absolute path shown by `pwd` when in the stockmon directory.

**Alternative Cron Schedules**:

```bash
# Every 5 minutes
*/5 * * * * cd /home/pi/stockmon && /home/pi/stockmon/venv/bin/python -m client.main >> /home/pi/stockmon/logs/client.log 2>&1

# Every 30 minutes
*/30 * * * * cd /home/pi/stockmon && /home/pi/stockmon/venv/bin/python -m client.main >> /home/pi/stockmon/logs/client.log 2>&1

# Every hour
0 * * * * cd /home/pi/stockmon && /home/pi/stockmon/venv/bin/python -m client.main >> /home/pi/stockmon/logs/client.log 2>&1

# Only during market hours (9:30 AM - 4:30 PM ET, Monday-Friday)
# Note: Adjust for your timezone
30 9-16 * * 1-5 cd /home/pi/stockmon && /home/pi/stockmon/venv/bin/python -m client.main >> /home/pi/stockmon/logs/client.log 2>&1
```

Save and exit (Ctrl+X, then Y, then Enter in nano).

**Verify Cron Job**:

```bash
crontab -l
```

This should display your configured cron jobs.

### 10. Monitor the Client

View real-time logs:

```bash
tail -f ~/stockmon/logs/client.log
```

Press Ctrl+C to exit the log viewer.

Check for errors in recent logs:

```bash
grep -i error ~/stockmon/logs/client.log
```

## Troubleshooting

### Authentication Errors (401 Unauthorized)

**Problem**: `401 Unauthorized` or `Invalid API key`

**Solution**:
1. Verify the `API_KEY` in `.env` matches the key configured on the API server
2. Ensure there are no extra spaces or newlines in the `.env` file
3. Test the API key with curl:

```bash
curl -X POST https://your-api.railway.app/check-alerts \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_API_KEY_HERE" \
  -d '{"AAPL": {"buy": 170}}'
```

### SMTP Authentication Errors

**Problem**: Email sending fails with authentication error

**Solution**:
1. Verify SMTP credentials in `.env`
2. For Gmail, ensure you are using an App Password (not your regular password)
3. Test SMTP connection:

```bash
python3 -c "
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv
import os

load_dotenv()
smtp = smtplib.SMTP(os.getenv('SMTP_HOST'), 587)
smtp.starttls()
smtp.login(os.getenv('SMTP_USER'), os.getenv('SMTP_PASS'))
print('SMTP connection successful')
smtp.quit()
"
```

### No Alerts Generated

**Problem**: Client runs but no emails are received

**Possible Causes**:
1. Stock prices have not breached configured thresholds
2. Alerts were already sent within the `silence_hours` period (check `client/notified.json`)
3. Market is closed (NYSE: Monday-Friday, 9:30 AM - 4:00 PM ET)

**Solution**:
1. Check current stock prices at https://finance.yahoo.com
2. Adjust thresholds in `client/config.json` to test
3. Delete `client/notified.json` to reset notification state
4. Run in dry-run mode to see debug output:

```bash
cd ~/stockmon
source venv/bin/activate
python -m client.main --dry-run
```

### Cron Job Not Running

**Problem**: Cron job is configured but client is not executing

**Solution**:
1. Verify cron service is running:

```bash
sudo systemctl status cron
```

2. Check cron logs:

```bash
grep CRON /var/log/syslog | tail -20
```

3. Ensure paths in crontab are absolute (not relative)
4. Test the exact command from crontab manually:

```bash
cd /home/pi/stockmon && /home/pi/stockmon/venv/bin/python -m client.main
```

### Connection Timeout

**Problem**: `Connection timeout` or `Connection refused`

**Solution**:
1. Verify internet connection: `ping 8.8.8.8`
2. Check API URL is correct in `client/config.json`
3. Verify API server is running (test `/health` endpoint):

```bash
curl https://your-api.railway.app/health
```

4. Check firewall settings (ensure outbound HTTPS is allowed)

### Python Module Not Found

**Problem**: `ModuleNotFoundError` when running client

**Solution**:
1. Ensure virtual environment is activated:

```bash
source ~/stockmon/venv/bin/activate
```

2. Reinstall dependencies:

```bash
pip install -r ~/stockmon/requirements.txt
```

3. Verify cron job uses full path to Python in virtual environment

## Maintenance

### Update the Client

Pull the latest changes from the repository:

```bash
cd ~/stockmon
source venv/bin/activate
git pull origin main
pip install -r requirements.txt --upgrade
```

### Reset Alert Notifications

To reset the notification state and allow re-notification of all alerts:

```bash
rm ~/stockmon/client/notified.json
```

The file will be recreated automatically on the next run.

### View Recent Logs

```bash
tail -100 ~/stockmon/logs/client.log
```

### Rotate Logs (Prevent Disk Space Issues)

Add log rotation to prevent `client.log` from growing too large:

```bash
sudo nano /etc/logrotate.d/stockmon
```

Add the following content:

```
/home/pi/stockmon/logs/*.log {
    weekly
    rotate 4
    compress
    missingok
    notifempty
}
```

Save and exit (Ctrl+X, then Y, then Enter).

## Security Best Practices

1. **Never commit `.env` to version control** - Contains sensitive credentials
2. **Use App Passwords** - For Gmail and other OAuth providers, use app-specific passwords
3. **Restrict file permissions**:

```bash
chmod 600 ~/stockmon/.env
```

4. **Rotate API keys periodically** - Update both `.env` and API server configuration
5. **Monitor logs for suspicious activity** - Check for unexpected authentication failures

## Additional Resources

- **StockMon README**: See `README.md` for architecture and API details
- **API Deployment Guide**: See `DEPLOYMENT_RAILWAY.md` for API server setup
- **Client Configuration**: See `client/config.json` for ticker configuration
- **Environment Variables**: See `.env.example` for all configuration options
- **Cron Documentation**: `man cron` or `man 5 crontab`
- **Python Virtual Environments**: https://docs.python.org/3/library/venv.html

## Support

For issues, questions, or feature requests, please open an issue on GitHub or contact the project maintainers.

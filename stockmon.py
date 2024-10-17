import yaml
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import pandas as pd
import yfinance as yf


# Read settings
with open("stockmon.yml", "r", encoding="utf-8") as f:
    conf = yaml.safe_load(f)

# Thresholds
period = conf["period"]
low_thresholds = conf["low_thresholds"] or {}
high_thresholds = conf["high_thresholds"] or {}

# Email setup (SMTP settings)
SMTP_SERVER = conf["email"]["server"]
SMTP_PORT = conf["email"]["port"]
SMTP_USERNAME = conf["email"]["user"]
SMTP_PASSWORD = conf["email"]["password"]
SENDER_EMAIL = conf["email"]["sender"]
RECIPIENT_EMAIL = conf["email"]["recipient"]


def send_email(subject, body, recipient=RECIPIENT_EMAIL):
    print(f"Sending email to {recipient}: {subject}")
    msg = MIMEText(body)
    msg["From"] = SENDER_EMAIL
    msg["To"] = recipient
    msg["Subject"] = subject

    # Connect to the SMTP server and send the email
    with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.sendmail(SENDER_EMAIL, recipient, msg.as_string())


def check_lows(prices):
    low_emails = []
    lows = prices.xs("Low", level="Price", axis=1)

    # Create a new DataFrame to store comparison results
    below_threshold = pd.DataFrame(index=lows.index)

    # Iterate over each ticker and compare Low prices against the corresponding threshold
    for ticker, threshold in low_thresholds.items():
        below_threshold[ticker] = lows[ticker] < threshold

    # Check which tickers are below the threshold and send emails
    for ticker, threshold in low_thresholds.items():
        # Find the dates where the price was below the threshold
        below_dates = below_threshold.index[below_threshold[ticker]]

        if not below_dates.empty:
            # Get the most recent date where the low was below the threshold
            latest_date = below_dates[-1].strftime("%Y-%m-%d")

            # Get the data for the ticker using .loc[]
            ticker_data = prices.loc[:, (slice(None), ticker)].dropna()
            ticker_data.index = ticker_data.index.strftime("%Y-%m-%d")

            # Create email
            low_emails.append(
                {
                    "subject": f"StockMon: {ticker} below {threshold} on {latest_date}",
                    "body": f"Ticker: {ticker}\nThreshold: {threshold}\n\nData:\n{ticker_data.to_string()}",
                }
            )
    return low_emails

def check_highs(prices):
    high_emails = []
    highs = prices.xs("High", level="Price", axis=1)

    # Create a new DataFrame to store comparison results
    above_threshold = pd.DataFrame(index=highs.index)

    # Iterate over each ticker and compare high prices against the corresponding threshold
    for ticker, threshold in high_thresholds.items():
        above_threshold[ticker] = highs[ticker] > threshold

    # Check which tickers are above the threshold and send emails
    for ticker, threshold in high_thresholds.items():
        # Find the dates where the price was above the threshold
        above_dates = above_threshold.index[above_threshold[ticker]]

        if not above_dates.empty:
            # Get the most recent date where the high was above the threshold
            latest_date = above_dates[-1].strftime("%Y-%m-%d")

            # Get the data for the ticker using .loc[]
            ticker_data = prices.loc[:, (slice(None), ticker)].dropna()
            ticker_data.index = ticker_data.index.strftime("%Y-%m-%d")

            # Create email
            high_emails.append(
                {
                    "subject": f"StockMon: {ticker} above {threshold} on {latest_date}",
                    "body": f"Ticker: {ticker}\nThreshold: {threshold}\n\nData:\n{ticker_data.to_string()}",
                }
            )
    return high_emails


if __name__ == "__main__":
    email_list = []
    # Fetch 5-day price data
    all_tickers = list(low_thresholds.keys()) + list(high_thresholds.keys())
    prices = yf.download(tickers=all_tickers, period=period)
    print(prices)

    # Get low price emails
    email_list += check_lows(prices)
    email_list += check_highs(prices)

    for email in email_list:
        send_email(email["subject"], email["body"])

    print("Done")

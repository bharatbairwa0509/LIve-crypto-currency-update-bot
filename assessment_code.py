import requests
import pandas as pd
import time
import schedule
import gspread
from google.oauth2.service_account import Credentials

# Google Sheets API Setup
SERVICE_ACCOUNT_FILE = "your_credentials.json"  # Replace with your service account JSON file
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
client = gspread.authorize(creds)

# Your Google Sheet ID
SHEET_ID = "1_2VZZ-vfFpc2U0W2KBJ1waHEWjbfRr-cFakZLjyiNUI"  # Replace with your Google Sheet ID
SHEET_NAME_DATA = "CryptoData"  # Sheet for raw crypto data
SHEET_NAME_ANALYSIS = "Analysis"  # Sheet for analysis

# API Constants
API_URL = "https://api.coingecko.com/api/v3/coins/markets"
PARAMS = {
    "vs_currency": "usd",
    "order": "market_cap_desc",
    "per_page": 50,  # Fetching top 50 coins
    "page": 1,
    "sparkline": False
}

def fetch_crypto_data():
    """Fetch cryptocurrency market data from CoinGecko API."""
    response = requests.get(API_URL, params=PARAMS)
    if response.status_code == 200:
        return response.json()
    else:
        print("Error fetching data:", response.status_code)
        return []

def analyze_data(data):
    """Perform data analysis on the fetched cryptocurrency data."""
    df = pd.DataFrame(data, columns=["name", "symbol", "current_price", "market_cap", "total_volume", "price_change_percentage_24h"])

    # Identify the top 5 cryptocurrencies by market cap
    top_5 = df.nlargest(5, "market_cap")[["name", "market_cap"]]

    # Calculate the average price of the top 50 cryptocurrencies
    avg_price = df["current_price"].mean()

    # Find the highest and lowest 24-hour percentage price change
    highest_change = df.nlargest(1, "price_change_percentage_24h")[["name", "price_change_percentage_24h"]]
    lowest_change = df.nsmallest(1, "price_change_percentage_24h")[["name", "price_change_percentage_24h"]]

    return df, top_5, avg_price, highest_change, lowest_change

def create_sheet_if_not_exists(sheet_name):
    """Create a Google Sheet if it doesn't exist."""
    spreadsheet = client.open_by_key(SHEET_ID)
    try:
        sheet = spreadsheet.worksheet(sheet_name)
    except gspread.exceptions.WorksheetNotFound:
        sheet = spreadsheet.add_worksheet(title=sheet_name, rows="100", cols="10")
    return sheet

def update_google_sheets():
    """Fetch data, analyze it, and update Google Sheets."""
    print("Fetching and updating cryptocurrency data...")

    data = fetch_crypto_data()
    if not data:
        return

    df, top_5, avg_price, highest_change, lowest_change = analyze_data(data)

    try:
        # Get sheets (create if not exist)
        sheet_data = create_sheet_if_not_exists(SHEET_NAME_DATA)
        sheet_analysis = create_sheet_if_not_exists(SHEET_NAME_ANALYSIS)

        # Clear previous data
        sheet_data.clear()
        sheet_analysis.clear()

        # Update Crypto Data Sheet
        sheet_data.update([df.columns.values.tolist()] + df.values.tolist())

        # Update Analysis Sheet
        sheet_analysis.append_row(["Top 5 Market Cap"])
        sheet_analysis.append_rows(top_5.values.tolist())

        sheet_analysis.append_row(["Summary"])
        sheet_analysis.append_row(["Average Price", avg_price])
        sheet_analysis.append_row(["Highest 24h Change", highest_change.iloc[0, 1], highest_change.iloc[0, 0]])
        sheet_analysis.append_row(["Lowest 24h Change", lowest_change.iloc[0, 1], lowest_change.iloc[0, 0]])

        print("Google Sheet updated successfully!")

    except Exception as e:
        print("Error updating Google Sheet:", e)

# Schedule updates every 5 minutes
schedule.every(5).minutes.do(update_google_sheets)

# Run first update immediately
update_google_sheets()

print("Live Crypto Data Updating... Press Ctrl+C to stop.")
while True:
    schedule.run_pending()
    time.sleep(60)

import requests
import pandas as pd
from bs4 import BeautifulSoup
import yfinance as yf
from datetime import datetime
import time

FUND_URL = "https://www.valueresearchonline.com/funds/29014/quant-small-cap-fund-direct-plan-growth/"
DIP_THRESHOLD = -1.5

def fetch_holdings_from_vro(url):
    print("📥 Fetching holdings from ValueResearch...")
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")

    table = soup.find("table", {"class": "fund-holdings-table"})

    if not table:
        print("❌ Holdings table not found.")
        return pd.DataFrame()

    rows = table.find_all("tr")[1:]  # Skip header
    data = []
    for row in rows:
        cols = row.find_all("td")
        if len(cols) >= 3:
            stock = cols[0].get_text(strip=True)
            weight = cols[2].get_text(strip=True).replace("%", "")
            try:
                data.append({"Stock": stock, "Weight(%)": float(weight)})
            except:
                continue

    df = pd.DataFrame(data)
    print(f"✅ Found {len(df)} holdings.\n")
    return df

def get_top_holdings(df, threshold=75):
    df_sorted = df.sort_values("Weight(%)", ascending=False).reset_index(drop=True)
    df_sorted["Cumulative"] = df_sorted["Weight(%)"].cumsum()
    selected = df_sorted[df_sorted["Cumulative"] <= threshold]
    if selected.empty:
        print("❌ Could not select top holdings.")
    else:
        print(f"✅ Selected {len(selected)} stocks covering {selected['Cumulative'].iloc[-1]:.2f}% of portfolio.")
    return selected

def map_to_nse_tickers(stock_names):
    # Very simple map, can be expanded with a dictionary
    print("🔁 Mapping stock names to NSE tickers...")
    tickers = []
    for name in stock_names:
        search = yf.Ticker(name + ".NS")
        try:
            info = search.info
            if info.get("regularMarketPrice"):
                tickers.append(name + ".NS")
        except:
            continue
    print(f"✅ Mapped tickers: {tickers}")
    return tickers

def calculate_weighted_movement(tickers, weights):
    print("📈 Fetching today's price data...")
    if not tickers:
        return 0.0
    movements = []
    for ticker in tickers:
        try:
            data = yf.download(ticker, period="1d", interval="5m", progress=False)
            if data.empty:
                continue
            open_price = data.iloc[0]["Open"]
            latest_price = data.iloc[-1]["Close"]
            pct_change = ((latest_price - open_price) / open_price) * 100
            movements.append(pct_change)
        except Exception as e:
            print(f"⚠️ Failed to fetch {ticker}: {e}")
            continue

    if not movements:
        return 0.0
    weighted_avg = sum(w * m for w, m in zip(weights, movements)) / sum(weights)
    return round(weighted_avg, 2)

def run_pipeline():
    print("🚀 Starting Mutual Fund Dip Alert System...\n")

    holdings_df = fetch_holdings_from_vro(FUND_URL)
    if holdings_df.empty:
        print("❌ No holdings data found.")
        return

    top_df = get_top_holdings(holdings_df)
    if top_df.empty:
        return

    tickers = map_to_nse_tickers(top_df["Stock"])
    movement = calculate_weighted_movement(tickers, top_df["Weight(%)"])

    print(f"\n📊 Weighted Average Movement: {movement:.2f}%")

    if movement <= DIP_THRESHOLD:
        print(f"📉 Buy Signal Triggered: Weighted dip = {movement:.2f}%")
    else:
        print(f"✅ No Signal. Weighted dip = {movement:.2f}%")

    print("\n✅ Pipeline completed.")

# ▶️ Run it
run_pipeline()
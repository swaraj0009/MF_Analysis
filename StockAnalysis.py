import os
import json
import pandas as pd
import yfinance as yf
import requests
from datetime import datetime, timedelta

NS_SUFFIX = ".NS"
USE_BACKTEST = False

NAV_DATE = "2025-07-22" if USE_BACKTEST else datetime.now().strftime("%Y-%m-%d")
RUN_TIME = "15:50:00" if USE_BACKTEST else datetime.now().strftime("%H:%M:%S")

# Mapping fund CSVs to their mfapi URLs
fund_sources = {
    "quant-small-cap-fund-direct-plan-growth": "https://api.mfapi.in/mf/120828",
    "canara-robeco-small-cap-fund-direct-growth": "https://api.mfapi.in/mf/146130",
    "motilal-oswal-most-focused-midcap-30-fund-direct-growth": "https://api.mfapi.in/mf/127042"
}

fund_csvs = [
    "quant-small-cap-fund-direct-plan-growth_final.csv",
    "canara-robeco-small-cap-fund-direct-growth_final.csv",
    "motilal-oswal-most-focused-midcap-30-fund-direct-growth_final.csv"
]

def get_prev_trading_day(date_str):
    d = datetime.strptime(date_str, "%Y-%m-%d") - timedelta(days=1)
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d.strftime("%Y-%m-%d")

def fetch_previous_close(ticker):
    prev = get_prev_trading_day(NAV_DATE)
    try:
        hist = yf.Ticker(ticker).history(start=prev, end=NAV_DATE)
        if not hist.empty:
            return hist["Close"].iloc[-1]
    except:
        pass
    return None

def fetch_live_price(ticker):
    try:
        if USE_BACKTEST:
            hist = yf.Ticker(ticker).history(
                start=NAV_DATE,
                end=(datetime.strptime(NAV_DATE, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
            )
        else:
            hist = yf.Ticker(ticker).history(period="1d")
        if not hist.empty:
            return hist["Close"].iloc[-1]
    except:
        pass
    return None

# 🔄 Replacing JSON with live NAV from mfapi
def fetch_nav_from_api(url):
    try:
        response = requests.get(url, timeout=10)
        data = response.json().get("data", [])
        df = pd.DataFrame(data)
        df["date"] = pd.to_datetime(df["date"], dayfirst=True)
        df["nav"] = df["nav"].astype(float)
        df = df.sort_values("date")
        df.set_index("date", inplace=True)
        return df
    except Exception as e:
        print(f"⚠️ Failed to fetch from {url}: {e}")
        return pd.DataFrame()

def get_month_start(date_str):
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return dt.replace(day=1).strftime("%Y-%m-%d")

def analyze_nav_csv_and_generate_msg():
    for csv_file in fund_csvs:
        fund_key = csv_file.split("_")[0]
        api_url = fund_sources.get(fund_key)
        if not api_url:
            print(f"⚠️ No API URL found for {fund_key}")
            continue

        nav_df = fetch_nav_from_api(api_url)
        if nav_df.empty:
            print(f"⚠️ NAV data unavailable for {fund_key}")
            continue

        prev_date = get_prev_trading_day(NAV_DATE)
        month_start_date = get_month_start(NAV_DATE)

        nav_month_start = nav_df.loc[month_start_date]["nav"] if month_start_date in nav_df.index else None
        nav_yesterday = nav_df.loc[prev_date]["nav"] if prev_date in nav_df.index else None
        nav_today = nav_df.loc[NAV_DATE]["nav"] if NAV_DATE in nav_df.index else None

        month_trend = ((nav_yesterday - nav_month_start) / nav_month_start * 100) if nav_month_start and nav_yesterday else None
        off_drop = ((nav_today - nav_yesterday) / nav_yesterday * 100) if nav_today and nav_yesterday else None

        # 💼 Ticker-based estimated NAV
        df = pd.read_csv(csv_file)
        df = df[df['ticker'].notna() & df['ticker'].str.strip().astype(bool)]
        prev_nav = live_nav = 0.0
        for _, row in df.iterrows():
            tkr = f"{row['ticker'].upper()}{NS_SUFFIX}"
            w = row.get('corpus_percent', row.get('corpus_per', 0)) / 100
            pc = fetch_previous_close(tkr)
            lp = fetch_live_price(tkr)
            if pc: prev_nav += pc * w
            if lp: live_nav += lp * w

        calc_drop = (live_nav - prev_nav) / prev_nav * 100 if prev_nav else None
        deviation = calc_drop - off_drop if calc_drop is not None and off_drop is not None else None

        print(f"\n\n📁 Fund: {fund_key}")
        print(f"📊 NAV Date: {NAV_DATE}, Time: {RUN_TIME} IST")

        # if nav_yesterday and nav_today:
        #     print(f"💹 Off NAV (Prev): ₹{nav_yesterday:.2f}")
        #     print(f"💹 Off NAV (Now): ₹{nav_today:.2f}")
        #     print(f"📉 Off Drop %: {off_drop:+.2f}%")
        # else:
        #     print("⚠️ Incomplete official NAVs")

        print(f"\n💹 Calc NAV (Prev): ₹{prev_nav:.2f}")
        print(f"💹 Calc NAV (Now): ₹{live_nav:.2f}")
        if calc_drop is not None:
            print(f"📉 Calc Drop %: {calc_drop:+.2f}%")
        else:
            print("⚠️ Could not compute proxy drop")

        if deviation is not None:
            print(f"\n🔴 Deviation: {deviation:+.2f}%")

        if nav_month_start and nav_yesterday:
            print("\n🔹 Trend Analysis (Month-to-Date):")
            print(f"   NAV on {month_start_date}: ₹{nav_month_start:.2f}")
            print(f"   NAV on {prev_date}: ₹{nav_yesterday:.2f}")
            print(f"   Cumulative Change: {month_trend:+.2f}%")
        else:
            print("⚠️ Month trend data insufficient")

        print("✅ Done.")
        print("::::::::::::::::::::::::::::::::::::::::")

# --- 🚀 RUN ---
if __name__ == "__main__":
    analyze_nav_csv_and_generate_msg()
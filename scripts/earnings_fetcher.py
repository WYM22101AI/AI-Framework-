"""Fetch earnings data from Alpha Vantage."""

import requests
import pandas as pd
import time


def fetch_earnings(api_key: str, symbol: str) -> pd.DataFrame:
    """
    Fetch quarterly earnings history for a symbol.
    Returns DataFrame with: symbol, fiscal_date_ending, reported_date,
    reported_eps, estimated_eps, surprise, surprise_pct
    """
    url = "https://www.alphavantage.co/query"
    params = {
        "function": "EARNINGS",
        "symbol": symbol,
        "apikey": api_key,
    }

    resp = requests.get(url, params=params, timeout=30)
    data = resp.json()

    if "quarterlyEarnings" not in data:
        print(f"  Earnings {symbol}: No data (may be rate limited)")
        return pd.DataFrame()

    records = []
    for q in data["quarterlyEarnings"]:
        try:
            reported_eps = float(q.get("reportedEPS", "None")) if q.get("reportedEPS", "None") != "None" else None
            estimated_eps = float(q.get("estimatedEPS", "None")) if q.get("estimatedEPS", "None") != "None" else None
            surprise = float(q.get("surprise", "None")) if q.get("surprise", "None") != "None" else None
            surprise_pct = float(q.get("surprisePercentage", "None")) if q.get("surprisePercentage", "None") != "None" else None

            records.append({
                "symbol": symbol,
                "fiscal_date_ending": q["fiscalDateEnding"],
                "reported_date": q["reportedDate"],
                "reported_eps": reported_eps,
                "estimated_eps": estimated_eps,
                "surprise": surprise,
                "surprise_pct": surprise_pct,
            })
        except (ValueError, KeyError):
            continue

    if not records:
        return pd.DataFrame()

    df = pd.DataFrame(records)
    df["fiscal_date_ending"] = pd.to_datetime(df["fiscal_date_ending"]).dt.date
    df["reported_date"] = pd.to_datetime(df["reported_date"]).dt.date

    return df


def fetch_all_earnings(api_key: str, symbols: list[str]) -> pd.DataFrame:
    """Fetch earnings for all symbols with rate limit handling."""
    all_data = []

    for i, symbol in enumerate(symbols):
        if symbol == "SPY":  # ETFs don't have earnings
            continue

        df = fetch_earnings(api_key, symbol)
        if not df.empty:
            all_data.append(df)
            print(f"  Earnings {symbol}: {len(df)} quarters")

        # Alpha Vantage free tier: 25 calls/day, ~5/min
        if i < len(symbols) - 1:
            time.sleep(12)

    if not all_data:
        return pd.DataFrame(columns=[
            "symbol", "fiscal_date_ending", "reported_date",
            "reported_eps", "estimated_eps", "surprise", "surprise_pct"
        ])

    return pd.concat(all_data, ignore_index=True)

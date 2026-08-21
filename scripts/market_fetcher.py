"""Fetch historical bar data from Alpaca."""

import alpaca_trade_api as tradeapi
import pandas as pd


def create_client(api_key: str, api_secret: str, base_url: str):
    """Create an Alpaca REST client."""
    return tradeapi.REST(api_key, api_secret, base_url, api_version="v2")


def fetch_bars(client, symbols: list[str], start_date, end_date, feed: str = "iex") -> pd.DataFrame:
    """
    Fetch daily bars for one or more symbols.
    Returns a DataFrame with columns: symbol, timestamp, open, high, low, close, volume, trade_count, vwap
    """
    bars = client.get_bars(
        symbols,
        "1Day",
        start=str(start_date.date()),
        end=str(end_date.date()),
        adjustment="all",
        feed=feed,
    ).df

    if bars.empty:
        return pd.DataFrame(columns=[
            "symbol", "timestamp", "open", "high", "low", "close",
            "volume", "trade_count", "vwap"
        ])

    bars = bars.reset_index()

    # Ensure required columns exist
    if "trade_count" not in bars.columns:
        bars["trade_count"] = None
    if "vwap" not in bars.columns:
        bars["vwap"] = None

    # Standardize column order
    bars = bars[["symbol", "timestamp", "open", "high", "low", "close", "volume", "trade_count", "vwap"]]

    return bars

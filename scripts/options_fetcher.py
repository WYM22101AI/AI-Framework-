"""Fetch options snapshots from Alpaca."""

import pandas as pd
from datetime import date


def fetch_options_snapshot(client, symbol: str) -> dict:
    """
    Get current options chain snapshot and compute key metrics.
    Returns a dict with: symbol, snapshot_date, atm_iv, put_call_volume_ratio, etc.
    """
    try:
        # Get options chain via Alpaca REST API
        chain = client.get_option_chain(symbol)
    except Exception as e:
        print(f"  Options {symbol}: ERROR - {e}")
        return None

    if not chain:
        return None

    total_call_volume = 0
    total_put_volume = 0
    total_call_oi = 0
    total_put_oi = 0
    atm_ivs = []

    # Get current stock price for ATM determination
    try:
        quote = client.get_latest_trade(symbol)
        spot_price = quote.price if quote else None
    except Exception:
        spot_price = None

    for contract_symbol, snapshot in chain.items():
        if snapshot is None:
            continue

        # Determine if call or put from the contract symbol
        is_call = "C" in contract_symbol.split(symbol)[-1][:2] if symbol in contract_symbol else True

        vol = getattr(snapshot, "daily_bar", None)
        if vol and hasattr(vol, "volume"):
            if is_call:
                total_call_volume += vol.volume
            else:
                total_put_volume += vol.volume

        oi = getattr(snapshot, "open_interest", 0) or 0
        if is_call:
            total_call_oi += oi
        else:
            total_put_oi += oi

        # Collect IV for near-ATM options
        greeks = getattr(snapshot, "greeks", None)
        if greeks and spot_price:
            strike = getattr(snapshot, "strike_price", None)
            iv = getattr(greeks, "implied_volatility", None)
            if strike and iv and abs(strike - spot_price) / spot_price < 0.05:
                atm_ivs.append(iv)

    put_call_vol_ratio = (total_put_volume / total_call_volume) if total_call_volume > 0 else None
    put_call_oi_ratio = (total_put_oi / total_call_oi) if total_call_oi > 0 else None
    atm_iv = sum(atm_ivs) / len(atm_ivs) if atm_ivs else None

    return {
        "symbol": symbol,
        "snapshot_date": date.today(),
        "atm_iv": atm_iv,
        "put_call_volume_ratio": put_call_vol_ratio,
        "put_call_oi_ratio": put_call_oi_ratio,
        "total_call_volume": total_call_volume,
        "total_put_volume": total_put_volume,
    }


def fetch_all_options(client, symbols: list[str]) -> pd.DataFrame:
    """Fetch options snapshots for all symbols."""
    records = []

    for symbol in symbols:
        if symbol == "SPY":
            continue  # SPY options chain is huge; skip for now

        result = fetch_options_snapshot(client, symbol)
        if result:
            records.append(result)
            print(f"  Options {symbol}: IV={result['atm_iv']:.2f}" if result['atm_iv'] else f"  Options {symbol}: no IV data")

    if not records:
        return pd.DataFrame(columns=[
            "symbol", "snapshot_date", "atm_iv",
            "put_call_volume_ratio", "put_call_oi_ratio",
            "total_call_volume", "total_put_volume"
        ])

    return pd.DataFrame(records)

"""Fetch options snapshots from Alpaca using alpaca-py."""

import os
import pandas as pd
from datetime import date
from dotenv import load_dotenv

from alpaca.data.historical.option import OptionHistoricalDataClient
from alpaca.data.requests import OptionChainRequest


def create_options_client(api_key: str, api_secret: str) -> OptionHistoricalDataClient:
    """Create an Alpaca options data client (alpaca-py)."""
    return OptionHistoricalDataClient(api_key, api_secret)


def fetch_options_snapshot(client: OptionHistoricalDataClient, symbol: str, spot_price: float = None) -> dict:
    """
    Get options chain snapshot and compute key metrics.
    Returns dict with: symbol, snapshot_date, atm_iv, put_call_volume_ratio, etc.
    """
    try:
        req = OptionChainRequest(underlying_symbol=symbol)
        chain = client.get_option_chain(req)
    except Exception as e:
        print(f"  Options {symbol}: ERROR - {e}")
        return None

    if not chain:
        print(f"  Options {symbol}: empty chain")
        return None

    total_call_volume = 0
    total_put_volume = 0
    total_call_oi = 0
    total_put_oi = 0
    atm_ivs = []

    for contract_symbol, snap in chain.items():
        if snap is None:
            continue

        # Determine call vs put from contract symbol
        # Format: AMZN260919C00200000 (C=call, P=put)
        contract_str = str(contract_symbol)
        underlying_end = len(symbol)
        type_char = None
        for i in range(underlying_end, len(contract_str)):
            if contract_str[i] in ("C", "P"):
                type_char = contract_str[i]
                # Extract strike: digits after C/P, divide by 1000
                strike_str = contract_str[i+1:]
                try:
                    strike = int(strike_str) / 1000
                except ValueError:
                    strike = None
                break

        is_call = (type_char == "C")

        # Volume from latest trade
        if hasattr(snap, "latest_trade") and snap.latest_trade:
            vol = getattr(snap.latest_trade, "size", 0) or 0
        else:
            vol = 0

        if is_call:
            total_call_volume += vol
        else:
            total_put_volume += vol

        # Implied volatility
        iv = getattr(snap, "implied_volatility", None)

        # Collect ATM IVs (within 5% of spot price)
        if iv and spot_price and strike:
            if abs(strike - spot_price) / spot_price < 0.05:
                atm_ivs.append(iv)

    put_call_vol_ratio = (total_put_volume / total_call_volume) if total_call_volume > 0 else None
    atm_iv = sum(atm_ivs) / len(atm_ivs) if atm_ivs else None

    result = {
        "symbol": symbol,
        "snapshot_date": date.today(),
        "atm_iv": round(atm_iv, 4) if atm_iv else None,
        "put_call_volume_ratio": round(put_call_vol_ratio, 4) if put_call_vol_ratio else None,
        "put_call_oi_ratio": None,  # OI not available in snapshot
        "total_call_volume": total_call_volume,
        "total_put_volume": total_put_volume,
    }

    iv_str = f"IV={result['atm_iv']:.2%}" if result['atm_iv'] else "no ATM IV"
    pc_str = f"P/C={result['put_call_volume_ratio']:.2f}" if result['put_call_volume_ratio'] else "no P/C"
    print(f"  Options {symbol}: {len(chain)} contracts, {iv_str}, {pc_str}")

    return result


def fetch_all_options(api_key: str, api_secret: str, symbols: list[str], spot_prices: dict = None) -> pd.DataFrame:
    """Fetch options snapshots for all symbols."""
    client = create_options_client(api_key, api_secret)

    if spot_prices is None:
        spot_prices = {}

    records = []
    for symbol in symbols:
        if symbol == "SPY":
            continue  # SPY chain is huge, skip for now

        spot = spot_prices.get(symbol)
        result = fetch_options_snapshot(client, symbol, spot_price=spot)
        if result:
            records.append(result)

    if not records:
        return pd.DataFrame(columns=[
            "symbol", "snapshot_date", "atm_iv",
            "put_call_volume_ratio", "put_call_oi_ratio",
            "total_call_volume", "total_put_volume"
        ])

    return pd.DataFrame(records)


if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    import config

    load_dotenv()
    print("Testing options fetcher (alpaca-py)...")
    df = fetch_all_options(config.API_KEY, config.API_SECRET, ["AMZN", "NVDA", "TSLA"])
    print(f"\nResults:\n{df.to_string(index=False)}")

"""
Fetch Full S&P 500 Universe:
Loads the comprehensive S&P 500 constituent list across all 11 GICS sectors
and ingests 10-year daily price bars from Alpaca into family_quant.duckdb.

Usage:
    python scripts/fetch_sp500_universe.py
"""

import sys, os, time, requests
from datetime import datetime, timedelta
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from scripts.storage import init_db, upsert_bars, get_last_date
from scripts.market_fetcher import create_client, fetch_bars

# Comprehensive S&P 500 Constituent Universe across all 11 GICS Sectors
SP500_SECTORS = {
    "Information Technology": [
        "AAPL", "MSFT", "NVDA", "AVGO", "ORCL", "CRM", "AMD", "ADBE", "QCOM", "CSCO",
        "TXN", "INTU", "NOW", "AMAT", "IBM", "ADI", "LRCX", "MU", "PANW", "KLAC",
        "SNPS", "CDNS", "CRWD", "FTNT", "MCHP", "NXPI", "APH", "MSI", "TEL", "HPQ",
        "ON", "FSLR", "GLW", "STX", "WDC", "ANET", "KEYS", "TDY", "ZBRA", "SWKS"
    ],
    "Financials": [
        "JPM", "BAC", "WFC", "C", "GS", "MS", "BLK", "SPGI", "AXP", "PGR",
        "CB", "MMC", "AON", "SCHW", "MCO", "CME", "ICE", "USB", "PNC", "TRV",
        "AFL", "AIG", "MET", "PRU", "ALL", "BK", "COF", "DFS", "STT", "FITB",
        "MTB", "HBAN", "RF", "CFG", "KEY", "NTRS", "SYF", "BRO", "WRB", "CINF"
    ],
    "Health Care": [
        "LLY", "UNH", "JNJ", "ABBV", "MRK", "TMO", "ABT", "PFE", "DHR", "ISRG",
        "AMGN", "BMY", "SYK", "GILD", "VRTX", "MDT", "ELV", "BSX", "CI", "REGN",
        "ZTS", "BDX", "HCA", "MCK", "CVS", "COR", "A", "IDXX", "IQV", "EW",
        "RMD", "CNC", "DXCM", "BAX", "MTD", "STE", "CAH", "WST", "PODD", "ALGN"
    ],
    "Consumer Discretionary": [
        "AMZN", "TSLA", "HD", "MCD", "NKE", "LOW", "BKNG", "SBUX", "TJX", "TGT",
        "MAR", "HLT", "CMG", "ORLY", "AZO", "ROST", "DHI", "LEN", "GM", "F",
        "YUM", "LVS", "RCL", "CCL", "EXPE", "DRI", "ULTA", "BBY", "POOL", "TSCO"
    ],
    "Consumer Staples": [
        "PG", "COST", "WMT", "KO", "PEP", "PM", "MDLZ", "MO", "CL", "TGT",
        "ADM", "GIS", "STZ", "KMB", "K", "SYY", "HSY", "KR", "EL", "CAG",
        "CHD", "TSN", "MKC", "CLX", "HRL", "SJM", "CPB", "TAP", "LW", "DG"
    ],
    "Communication Services": [
        "GOOGL", "GOOG", "META", "NFLX", "DIS", "TMUS", "VZ", "T", "CMCSA", "CHTR",
        "EA", "TTWO", "WBD", "OMC", "IPG", "FOXA", "FOX", "NWSA", "NWS", "LYV"
    ],
    "Industrials": [
        "GE", "CAT", "UNP", "HON", "BA", "RTX", "LMT", "DE", "UPS", "ETN",
        "ITW", "WM", "EMR", "GD", "NSC", "CSX", "PH", "TT", "TDG", "PCAR",
        "FDX", "CARR", "OTIS", "JCI", "FAST", "URI", "CMI", "ROK", "AME", "VMC"
    ],
    "Energy": [
        "XOM", "CVX", "COP", "EOG", "SLB", "MPC", "PSX", "VLO", "OXY", "WMB",
        "HES", "KMI", "HAL", "BKR", "DVN", "FANG", "TRGP", "OKE", "EQT", "APA"
    ],
    "Utilities": [
        "NEE", "SO", "DUK", "CEG", "SRE", "AEP", "D", "PEG", "EXC", "XEL",
        "ED", "WEC", "PCG", "AWK", "ES", "DTE", "PPL", "AEE", "CMS", "CNP"
    ],
    "Real Estate": [
        "PLD", "AMT", "EQIX", "CCI", "PSA", "O", "WELL", "DLR", "SPG", "VICI",
        "SBAC", "AVB", "EQR", "WY", "ARE", "MAA", "VTR", "CPT", "INVH", "EXR"
    ],
    "Materials": [
        "LIN", "SHW", "APD", "ECL", "FCX", "NEM", "CTVA", "DOW", "NUE", "DD",
        "VMC", "MLM", "PPG", "BALL", "PKG", "IP", "CF", "FMC", "MOS", "ALB"
    ],
    "Major Index & Sector ETFs": [
        "SPY", "QQQ", "IWM", "DIA", "XLK", "XLF", "XLV", "XLE", "XLI", "XLY"
    ]
}

def get_all_sp500_tickers():
    """Flatten all sectors into a unique list of ~400-500 high-liquidity symbols."""
    tickers = []
    for sec, syms in SP500_SECTORS.items():
        tickers.extend(syms)
    # Remove duplicates preserving order
    seen = set()
    unique_tickers = []
    for t in tickers:
        if t not in seen:
            seen.add(t)
            unique_tickers.append(t)
    return unique_tickers

def fetch_and_store_universe():
    tickers = get_all_sp500_tickers()
    print(f"===========================================================", flush=True)
    print(f"  INGESTING FULL S&P 500 UNIVERSE ({len(tickers)} TICKERS) ", flush=True)
    print(f"===========================================================\n", flush=True)

    conn = init_db(config.DB_PATH)
    client = create_client(config.API_KEY, config.API_SECRET, config.BASE_URL)

    end_date = datetime.now()
    lookback = config.LOOKBACK_YEARS * 365
    
    total_new_bars = 0
    t0 = time.time()

    for i, symbol in enumerate(tickers):
        last = get_last_date(conn, symbol)
        if last is None:
            start_date = end_date - timedelta(days=lookback)
            mode = "FULL 10Y"
        else:
            last_naive = pd.Timestamp(last).tz_localize(None).to_pydatetime()
            start_date = last_naive + timedelta(days=1)
            mode = "INCREMENTAL"

        if start_date.date() >= end_date.date():
            print(f"[{i+1}/{len(tickers)}] {symbol:5s}: up to date.", flush=True)
            continue

        try:
            df = fetch_bars(client, [symbol], start_date, end_date, feed=config.FEED)
            if not df.empty:
                rows = upsert_bars(conn, df)
                total_new_bars += rows
                print(f"[{i+1}/{len(tickers)}] {symbol:5s} ({mode}): {rows:,} bars stored", flush=True)
            else:
                print(f"[{i+1}/{len(tickers)}] {symbol:5s}: no bars returned", flush=True)
        except Exception as e:
            print(f"[{i+1}/{len(tickers)}] {symbol:5s} ERROR: {e}", flush=True)

        time.sleep(0.15) # Fast 0.15s pacing for high-throughput batching

    elapsed = time.time() - t0
    total_bars = conn.execute("SELECT COUNT(*) FROM daily_bars").fetchone()[0]
    total_symbols = conn.execute("SELECT COUNT(DISTINCT symbol) FROM daily_bars").fetchone()[0]
    conn.close()

    print(f"\n===========================================================", flush=True)
    print(f"  INGESTION COMPLETE in {elapsed:.1f}s!", flush=True)
    print(f"  Added {total_new_bars:,} new bars.", flush=True)
    print(f"  Database now holds {total_bars:,} bars across {total_symbols} symbols.", flush=True)
    print(f"===========================================================\n", flush=True)

if __name__ == "__main__":
    fetch_and_store_universe()

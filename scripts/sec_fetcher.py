"""Fetch company fundamentals from SEC EDGAR."""

import requests
import pandas as pd
import time

# Mapping of CIK numbers for our tickers
TICKER_TO_CIK = {
    "TSLA": "0001318605",
    "AAPL": "0000320193",
    "NVDA": "0001045810",
}


def fetch_company_facts(symbol: str, user_agent: str) -> pd.DataFrame:
    """
    Fetch quarterly fundamentals from SEC EDGAR XBRL API.
    Returns DataFrame with: symbol, fiscal_date_ending, filed_date,
    revenue, net_income, total_assets, total_liabilities, operating_cash_flow
    """
    cik = TICKER_TO_CIK.get(symbol)
    if not cik:
        return pd.DataFrame()

    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
    headers = {"User-Agent": user_agent}

    try:
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"  SEC {symbol}: ERROR - {e}")
        return pd.DataFrame()

    facts = data.get("facts", {}).get("us-gaap", {})

    def extract_quarterly(concept_name):
        """Extract quarterly values for a given concept."""
        concept = facts.get(concept_name, {})
        units = concept.get("units", {})
        values = units.get("USD", [])
        quarterly = [v for v in values if v.get("form") in ("10-Q", "10-K")]
        return {(v["end"], v.get("filed")): v["val"] for v in quarterly if "end" in v}

    # Extract key metrics
    revenue_data = extract_quarterly("Revenues") or extract_quarterly("RevenueFromContractWithCustomerExcludingAssessedTax")
    net_income_data = extract_quarterly("NetIncomeLoss")
    assets_data = extract_quarterly("Assets")
    liabilities_data = extract_quarterly("Liabilities")
    cashflow_data = extract_quarterly("NetCashProvidedByUsedInOperatingActivities")

    # Combine all metrics by fiscal period end date
    all_dates = set()
    for d in [revenue_data, net_income_data, assets_data, liabilities_data, cashflow_data]:
        all_dates.update(d.keys())

    records = []
    for (end_date, filed_date) in sorted(all_dates):
        key = (end_date, filed_date)
        records.append({
            "symbol": symbol,
            "fiscal_date_ending": end_date,
            "filed_date": filed_date,
            "revenue": revenue_data.get(key),
            "net_income": net_income_data.get(key),
            "total_assets": assets_data.get(key),
            "total_liabilities": liabilities_data.get(key),
            "operating_cash_flow": cashflow_data.get(key),
        })

    if not records:
        return pd.DataFrame()

    df = pd.DataFrame(records)
    df["fiscal_date_ending"] = pd.to_datetime(df["fiscal_date_ending"]).dt.date
    df["filed_date"] = pd.to_datetime(df["filed_date"]).dt.date

    # Remove rows where all financial fields are None
    financial_cols = ["revenue", "net_income", "total_assets", "total_liabilities", "operating_cash_flow"]
    df = df.dropna(subset=financial_cols, how="all")

    # Keep only the latest filing per fiscal_date_ending (amendments supersede originals)
    df = df.sort_values("filed_date").drop_duplicates(subset=["symbol", "fiscal_date_ending"], keep="last")

    # Ensure column order matches table schema
    df = df[["symbol", "fiscal_date_ending", "filed_date", "revenue", "net_income", "total_assets", "total_liabilities", "operating_cash_flow"]]

    return df


def fetch_all_fundamentals(symbols: list[str], user_agent: str) -> pd.DataFrame:
    """Fetch fundamentals for all symbols."""
    all_data = []

    for i, symbol in enumerate(symbols):
        if symbol == "SPY":  # ETF, skip
            continue

        df = fetch_company_facts(symbol, user_agent)
        if not df.empty:
            all_data.append(df)
            print(f"  SEC {symbol}: {len(df)} filings")

        # SEC rate limit: 10 requests/sec
        if i < len(symbols) - 1:
            time.sleep(0.2)

    if not all_data:
        return pd.DataFrame(columns=[
            "symbol", "fiscal_date_ending", "filed_date",
            "revenue", "net_income", "total_assets", "total_liabilities", "operating_cash_flow"
        ])

    return pd.concat(all_data, ignore_index=True)

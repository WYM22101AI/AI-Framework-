"""Fetch macroeconomic data from FRED (Federal Reserve Economic Data)."""

import pandas as pd
from fredapi import Fred


def create_fred_client(api_key: str) -> Fred:
    """Create a FRED API client."""
    return Fred(api_key=api_key)


def fetch_series(client: Fred, series_id: str, start_date=None) -> pd.DataFrame:
    """
    Fetch a FRED series.
    Returns DataFrame with columns: series_id, observation_date, release_date, value
    """
    data = client.get_series(series_id, observation_start=start_date)

    if data is None or data.empty:
        return pd.DataFrame(columns=["series_id", "observation_date", "release_date", "value"])

    df = pd.DataFrame({
        "series_id": series_id,
        "observation_date": data.index.date,
        "value": data.values,
    })

    # Use observation_date as release_date approximation
    # (FRED data is typically released with a lag, e.g. CPI ~2 weeks after month end)
    df["release_date"] = df["observation_date"]

    # Remove NaN values
    df = df.dropna(subset=["value"])

    # Ensure column order matches table schema
    df = df[["series_id", "observation_date", "release_date", "value"]]

    return df


def fetch_all_series(client: Fred, series_list: list[str], start_date=None) -> pd.DataFrame:
    """Fetch multiple FRED series and combine into one DataFrame."""
    all_data = []

    for series_id in series_list:
        try:
            df = fetch_series(client, series_id, start_date)
            if not df.empty:
                all_data.append(df)
                print(f"  FRED {series_id}: {len(df)} observations")
        except Exception as e:
            print(f"  FRED {series_id}: ERROR - {e}")

    if not all_data:
        return pd.DataFrame(columns=["series_id", "observation_date", "release_date", "value"])

    return pd.concat(all_data, ignore_index=True)

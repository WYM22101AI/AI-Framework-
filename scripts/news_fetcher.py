"""Fetch news from Alpaca."""

import pandas as pd
from datetime import datetime, timedelta


def fetch_news(client, symbols: list[str], days_back: int = 7) -> pd.DataFrame:
    """
    Fetch recent news for given symbols from Alpaca.
    Returns DataFrame with: id, symbol, headline, published_at, source
    """
    start = datetime.now() - timedelta(days=days_back)

    try:
        news_items = client.get_news(
            symbol=",".join(symbols),
            start=start.strftime("%Y-%m-%dT%H:%M:%SZ"),
            limit=50,
        )
    except Exception as e:
        print(f"  News: ERROR - {e}")
        return pd.DataFrame(columns=["id", "symbol", "headline", "published_at", "source"])

    if not news_items:
        return pd.DataFrame(columns=["id", "symbol", "headline", "published_at", "source"])

    records = []
    for item in news_items:
        # Each news item can relate to multiple symbols
        item_symbols = getattr(item, "symbols", []) or []
        related = [s for s in item_symbols if s in symbols]

        for sym in (related or [symbols[0]]):
            records.append({
                "id": str(getattr(item, "id", "")),
                "symbol": sym,
                "headline": getattr(item, "headline", ""),
                "published_at": getattr(item, "created_at", None) or getattr(item, "timestamp", None),
                "source": getattr(item, "source", ""),
            })

    df = pd.DataFrame(records)
    print(f"  News: {len(df)} articles for {symbols}")
    return df

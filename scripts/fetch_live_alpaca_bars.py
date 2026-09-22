import os, requests
from dotenv import load_dotenv

load_dotenv(r"C:\Users\Yaming\family-quant-ai\.env")
api_key = os.getenv("APCA_API_KEY")
api_secret = os.getenv("APCA_API_SECRET")

headers = {
    "APCA-API-KEY-ID": api_key,
    "APCA-API-SECRET-KEY": api_secret
}

symbols = ["SPY", "QQQ", "NVDA", "AMZN", "AAPL", "MSFT", "CAT", "TSLA", "COST", "QCOM", "AMD"]
url = f"https://data.alpaca.markets/v2/stocks/bars?symbols={','.join(symbols)}&timeframe=1Day&limit=5&feed=iex"

r = requests.get(url, headers=headers)
print("=== OFFICIAL ALPACA DATA FEED SETTLED BARS ===")
if r.status_code == 200:
    data = r.json().get("bars", {})
    for sym in symbols:
        bars = data.get(sym, [])
        if bars:
            b_last = bars[-1]
            b_prev = bars[-2] if len(bars) > 1 else b_last
            chg = (b_last['c'] - b_prev['c']) / b_prev['c'] if len(bars) > 1 else 0.0
            dt = b_last['t'][:10]
            print(f"{sym:<6s}: Date: {dt} | Open: ${b_last['o']:7.2f} | High: ${b_last['h']:7.2f} | Low: ${b_last['l']:7.2f} | Close: ${b_last['c']:7.2f} | Change: {chg:+6.2%}")
        else:
            print(f"{sym:<6s}: No bars returned")
else:
    print(f"Error {r.status_code}: {r.text}")

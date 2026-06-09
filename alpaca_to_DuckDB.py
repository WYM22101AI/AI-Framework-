import os
from datetime import datetime, timedelta
import duckdb
from dotenv import load_dotenv

# Alpaca SDK components for historical bar data
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame

# Load credentials
load_dotenv()
API_KEY = os.getenv("APCA_API_KEY")
API_SECRET = os.getenv("APCA_API_SECRET")

# Initialize Alpaca client
client = StockHistoricalDataClient(API_KEY, API_SECRET)

# 1. Define time constraints for exactly 5 years of historical data
ticker = "TSLA"
end_date = datetime.now()
start_date = end_date - timedelta(days=5*365)

print(f"Fetching 5 years of daily bars for {ticker} via Alpaca...")

# 2. Structure historical bar request
request_params = StockBarsRequest(
    symbol_or_symbols=ticker,
    timeframe=TimeFrame.Day,
    start=start_date,
    end=end_date
)

# 3. Pull data and convert directly into a Pandas DataFrame
bars_response = client.get_stock_bars(request_params)
df_bars = bars_response.df

# 4. Clean up multi-index tracking from Alpaca for simple relational storage
df_bars = df_bars.reset_index()

# 5. Open local DuckDB storage
conn = duckdb.connect("market_data.duckdb")

# 6. Build the table structural schema dynamically using the DataFrame 
conn.execute(
    f"""
    CREATE TABLE IF NOT EXISTS {ticker}_history AS 
    SELECT * FROM df_bars LIMIT 0
"""
)

# 7. Wipe older contents and inject fresh historical data 
conn.execute(f"TRUNCATE TABLE {ticker}_history")
conn.execute(f"INSERT INTO {ticker}_history SELECT * FROM df_bars")

# 8. Query verification check
print(f"\nSuccessfully stored inside DuckDB! Previewing the first 5 records:")
preview = conn.execute(f"SELECT timestamp, open, high, low, close, volume FROM {ticker}_history LIMIT 5").fetchall()
for row in preview:
    print(row)

# Close session
conn.close()

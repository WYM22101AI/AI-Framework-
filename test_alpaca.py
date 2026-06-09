import os
from dotenv import load_dotenv

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockLatestQuoteRequest

load_dotenv()

API_KEY = os.getenv("APCA_API_KEY")
API_SECRET = os.getenv("APCA_API_SECRET")

client = StockHistoricalDataClient(API_KEY, API_SECRET)

request = StockLatestQuoteRequest(symbol_or_symbols="TSLA")

quote = client.get_stock_latest_quote(request)

print("AAPL Latest Quote:")
print(quote)
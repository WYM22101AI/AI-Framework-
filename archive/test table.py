bars["symbol"] = SYMBOL

# ensure missing columns exist
if "trade_count" not in bars.columns:
    bars["trade_count"] = None

if "vwap" not in bars.columns:
    bars["vwap"] = None

bars = bars[[
    "symbol",
    "timestamp",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "trade_count",
    "vwap"
]]
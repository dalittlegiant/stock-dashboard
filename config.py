"""Configuration constants for the stock dashboard."""

# Portfolio holdings
HOLDINGS = ["NVDA", "TSLA", "GOOG", "AVGO", "MRVL", "ORCL"]

# Watchlist tickers
WATCHLIST = ["AAPL", "NET", "SMCI", "SKHY", "SPCX"]

# Data fetching settings
CACHE_TTL = 300  # seconds

# Chart settings
CHART_HISTORY_PERIOD = "1y"
SHORT_HISTORY_PERIOD = "3mo"

# Technical indicator parameters
RSI_PERIOD = 14
SMA_SHORT = 20
SMA_LONG = 50
EMA_PERIOD = 12
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9

# Signal thresholds
RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70

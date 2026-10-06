"""Data fetching functions for the stock dashboard."""

import yfinance as yf
import pandas as pd
import streamlit as st
from datetime import datetime
from config import CACHE_TTL, CHART_HISTORY_PERIOD


_last_fetch_time = None

def get_last_fetch_time() -> str:
    """Return the timestamp when data was last fetched."""
    global _last_fetch_time
    if _last_fetch_time is None:
        _last_fetch_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
    return _last_fetch_time

def _update_fetch_time():
    """Call this when data is actually fetched to update the timestamp."""
    global _last_fetch_time
    _last_fetch_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")


@st.cache_data(ttl=CACHE_TTL)
def get_stock_data(ticker: str, period: str = CHART_HISTORY_PERIOD) -> pd.DataFrame:
    """Fetch historical stock data for a ticker.
    
    Filters out rows with NaN Close prices (e.g., pre-market data on weekends).
    """
    _update_fetch_time()
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period=period)
        if df.empty:
            return pd.DataFrame()
        # Drop rows where Close is NaN (happens when market hasn't opened yet)
        df = df.dropna(subset=["Close"])
        return df
    except Exception as e:
        st.warning(f"⚠️ Could not fetch data for {ticker}: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=CACHE_TTL)
def get_stock_info(ticker: str) -> dict:
    """Fetch current stock info/quote for a ticker."""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        return info
    except Exception as e:
        st.warning(f"⚠️ Could not fetch info for {ticker}: {e}")
        return {}


@st.cache_data(ttl=CACHE_TTL)
def get_stock_news(ticker: str) -> list:
    """Fetch news for a ticker (top 3 items)."""
    try:
        stock = yf.Ticker(ticker)
        news = stock.news
        if news is None:
            return []
        return news[:3]
    except Exception as e:
        st.warning(f"⚠️ Could not fetch news for {ticker}: {e}")
        return []


def get_current_price_data(ticker: str) -> dict:
    """Get current price, daily change, and volume for a ticker.
    
    Uses the last available trading day's data, whether market is open or closed.
    """
    try:
        df = get_stock_data(ticker, period="5d")
        if df.empty or len(df) < 2:
            return {"price": None, "change_pct": None, "volume": None, "error": True}
        
        # Use last valid trading day (already filtered for NaN in get_stock_data)
        current = df.iloc[-1]
        previous = df.iloc[-2]
        
        price = current["Close"]
        change_pct = ((price - previous["Close"]) / previous["Close"]) * 100
        volume = current["Volume"]
        
        return {
            "price": price,
            "change_pct": change_pct,
            "volume": volume,
            "error": False
        }
    except Exception as e:
        return {"price": None, "change_pct": None, "volume": None, "error": True}

"""Data fetching functions for the stock dashboard."""

import yfinance as yf
import pandas as pd
import streamlit as st
from config import CACHE_TTL, CHART_HISTORY_PERIOD


@st.cache_data(ttl=CACHE_TTL)
def get_stock_data(ticker: str, period: str = CHART_HISTORY_PERIOD) -> pd.DataFrame:
    """Fetch historical stock data for a ticker.
    
    Filters out rows with NaN Close prices (e.g., pre-market data on weekends).
    """
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


@st.cache_data(ttl=CACHE_TTL)
def get_enhanced_price_data(ticker: str) -> dict:
    """Get enhanced price data with all fields for the Portfolio Overview table.
    
    Returns dict with: price, price_change_pct, open, close, day_change_pct,
    high, low, gap_pct, volume, avg_volume_3m, error flag.
    """
    try:
        df = get_stock_data(ticker, period="5d")
        if df.empty or len(df) < 2:
            return {"error": True}

        current = df.iloc[-1]
        previous = df.iloc[-2]

        open_price = current["Open"]
        close_price = current["Close"]
        high = current["High"]
        low = current["Low"]
        volume = current["Volume"]
        prev_close = previous["Close"]

        # Price change vs previous close
        price_change_pct = ((close_price - prev_close) / prev_close) * 100

        # Intraday change: (Close - Open) / Open * 100
        day_change_pct = ((close_price - open_price) / open_price) * 100 if open_price != 0 else 0.0

        # Overnight gap: (Open - PreviousClose) / PreviousClose * 100
        gap_pct = ((open_price - prev_close) / prev_close) * 100 if prev_close != 0 else 0.0

        # Average volume over 3 months
        df_3mo = get_stock_data(ticker, period="3mo")
        avg_volume_3m = df_3mo["Volume"].mean() if not df_3mo.empty else None

        return {
            "price": close_price,
            "price_change_pct": price_change_pct,
            "open": open_price,
            "close": close_price,
            "day_change_pct": day_change_pct,
            "high": high,
            "low": low,
            "gap_pct": gap_pct,
            "volume": volume,
            "avg_volume_3m": avg_volume_3m,
            "error": False,
        }
    except Exception:
        return {"error": True}

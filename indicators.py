"""Technical indicator calculations using ta library (pure Python, no numba needed)."""

import pandas as pd
import ta
from config import (
    RSI_PERIOD, SMA_SHORT, SMA_LONG, EMA_PERIOD,
    MACD_FAST, MACD_SLOW, MACD_SIGNAL,
    RSI_OVERSOLD, RSI_OVERBOUGHT
)


def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate all technical indicators on a DataFrame."""
    if df.empty or len(df) < 50:
        return df
    
    df = df.copy()
    
    # RSI
    rsi = ta.momentum.RSIIndicator(df["Close"], window=RSI_PERIOD)
    df["RSI"] = rsi.rsi()
    
    # SMA
    sma20 = ta.trend.SMAIndicator(df["Close"], window=SMA_SHORT)
    df["SMA_20"] = sma20.sma_indicator()
    
    sma50 = ta.trend.SMAIndicator(df["Close"], window=SMA_LONG)
    df["SMA_50"] = sma50.sma_indicator()
    
    # EMA
    ema12 = ta.trend.EMAIndicator(df["Close"], window=EMA_PERIOD)
    df["EMA_12"] = ema12.ema_indicator()
    
    # MACD
    macd = ta.trend.MACD(
        df["Close"],
        window_fast=MACD_FAST,
        window_slow=MACD_SLOW,
        window_sign=MACD_SIGNAL
    )
    df["MACD_12_26_9"] = macd.macd()
    df["MACDs_12_26_9"] = macd.macd_signal()
    df["MACDh_12_26_9"] = macd.macd_diff()
    
    return df


def generate_signal(df: pd.DataFrame) -> str:
    """Generate a BUY/SELL/HOLD signal based on technical indicators."""
    if df.empty or len(df) < 50:
        return "⏸️ HOLD"
    
    latest = df.iloc[-1]
    signals = []
    
    # RSI signal
    if pd.notna(latest.get("RSI")):
        rsi = latest["RSI"]
        if rsi < RSI_OVERSOLD:
            signals.append(1)  # Bullish
        elif rsi > RSI_OVERBOUGHT:
            signals.append(-1)  # Bearish
        else:
            signals.append(0)
    
    # SMA crossover signal
    if pd.notna(latest.get("SMA_20")) and pd.notna(latest.get("SMA_50")):
        if latest["SMA_20"] > latest["SMA_50"]:
            signals.append(1)  # Bullish - golden cross
        else:
            signals.append(-1)  # Bearish - death cross
    
    # Price vs EMA signal
    if pd.notna(latest.get("EMA_12")):
        if latest["Close"] > latest["EMA_12"]:
            signals.append(1)  # Bullish
        else:
            signals.append(-1)  # Bearish
    
    # MACD histogram signal
    if pd.notna(latest.get("MACDh_12_26_9")):
        if latest["MACDh_12_26_9"] > 0:
            signals.append(1)  # Bullish
        else:
            signals.append(-1)  # Bearish
    
    if not signals:
        return "⏸️ HOLD"
    
    avg_signal = sum(signals) / len(signals)
    
    if avg_signal >= 0.5:
        return "🟢 BUY"
    elif avg_signal <= -0.5:
        return "🔴 SELL"
    else:
        return "⏸️ HOLD"


def get_indicator_summary(df: pd.DataFrame) -> dict:
    """Get a summary dict of current indicator values."""
    if df.empty:
        return {}
    
    latest = df.iloc[-1]
    
    summary = {
        "RSI(14)": f"{latest.get('RSI', 0):.1f}" if pd.notna(latest.get("RSI")) else "N/A",
        "SMA(20)": f"${latest.get('SMA_20', 0):.2f}" if pd.notna(latest.get("SMA_20")) else "N/A",
        "SMA(50)": f"${latest.get('SMA_50', 0):.2f}" if pd.notna(latest.get("SMA_50")) else "N/A",
        "EMA(12)": f"${latest.get('EMA_12', 0):.2f}" if pd.notna(latest.get("EMA_12")) else "N/A",
    }
    
    # MACD histogram
    if pd.notna(latest.get("MACDh_12_26_9")):
        summary["MACD Histogram"] = f"{latest['MACDh_12_26_9']:.4f}"
    else:
        summary["MACD Histogram"] = "N/A"
    
    return summary

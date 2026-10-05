"""Technical indicator calculations for the stock dashboard."""

import pandas as pd
import pandas_ta as ta
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
    df["RSI"] = ta.rsi(df["Close"], length=RSI_PERIOD)
    
    # SMA
    df["SMA_20"] = ta.sma(df["Close"], length=SMA_SHORT)
    df["SMA_50"] = ta.sma(df["Close"], length=SMA_LONG)
    
    # EMA
    df["EMA_12"] = ta.ema(df["Close"], length=EMA_PERIOD)
    
    # MACD
    macd = ta.macd(df["Close"], fast=MACD_FAST, slow=MACD_SLOW, signal=MACD_SIGNAL)
    if macd is not None and not macd.empty:
        df = pd.concat([df, macd], axis=1)
    
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
    
    # MACD signal
    macd_col = [c for c in df.columns if "MACD_12_26_9" in c and "h" not in c.lower() and "s" not in c.lower()]
    macd_hist_col = [c for c in df.columns if "MACDh" in c or "MACD" in c and "h" in c.lower()]
    
    if macd_hist_col and pd.notna(latest.get(macd_hist_col[0])):
        if latest[macd_hist_col[0]] > 0:
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
        "RSI(14)": f"{latest.get('RSI', 'N/A'):.1f}" if pd.notna(latest.get("RSI")) else "N/A",
        "SMA(20)": f"${latest.get('SMA_20', 0):.2f}" if pd.notna(latest.get("SMA_20")) else "N/A",
        "SMA(50)": f"${latest.get('SMA_50', 0):.2f}" if pd.notna(latest.get("SMA_50")) else "N/A",
        "EMA(12)": f"${latest.get('EMA_12', 0):.2f}" if pd.notna(latest.get("EMA_12")) else "N/A",
    }
    
    # MACD
    macd_hist_col = [c for c in df.columns if "MACDh" in c]
    if macd_hist_col and pd.notna(latest.get(macd_hist_col[0])):
        summary["MACD Histogram"] = f"{latest[macd_hist_col[0]]:.4f}"
    else:
        summary["MACD Histogram"] = "N/A"
    
    return summary

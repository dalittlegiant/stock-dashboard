"""Technical indicator calculations using ta library (pure Python, no numba needed)."""

import pandas as pd
import numpy as np
import ta
from config import (
    RSI_PERIOD, SMA_SHORT, SMA_LONG, EMA_PERIOD,
    MACD_FAST, MACD_SLOW, MACD_SIGNAL,
    RSI_OVERSOLD, RSI_OVERBOUGHT,
    BB_PERIOD, BB_STD,
    STOCH_K_PERIOD, STOCH_D_PERIOD, STOCH_SMOOTH,
    STOCH_OVERSOLD, STOCH_OVERBOUGHT,
    ATR_PERIOD,
    ADX_PERIOD, ADX_STRONG, ADX_WEAK,
    SR_LOOKBACK,
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

    # Bollinger Bands
    bb = ta.volatility.BollingerBands(
        df["Close"], window=BB_PERIOD, window_dev=BB_STD
    )
    df["BB_Upper"] = bb.bollinger_hband()
    df["BB_Middle"] = bb.bollinger_mavg()
    df["BB_Lower"] = bb.bollinger_lband()

    # Stochastic Oscillator
    stoch = ta.momentum.StochasticOscillator(
        df["High"], df["Low"], df["Close"],
        window=STOCH_K_PERIOD,
        smooth_window=STOCH_SMOOTH,
    )
    df["Stoch_K"] = stoch.stoch()
    df["Stoch_D"] = stoch.stoch_signal()

    # ATR (Average True Range)
    atr = ta.volatility.AverageTrueRange(
        df["High"], df["Low"], df["Close"], window=ATR_PERIOD
    )
    df["ATR"] = atr.average_true_range()

    # ADX (Average Directional Index)
    adx = ta.trend.ADXIndicator(
        df["High"], df["Low"], df["Close"], window=ADX_PERIOD
    )
    df["ADX"] = adx.adx()
    df["DI_Plus"] = adx.adx_pos()  # +DI
    df["DI_Minus"] = adx.adx_neg()  # -DI

    return df


def find_support_resistance(df: pd.DataFrame, lookback: int = SR_LOOKBACK) -> dict:
    """Find recent pivot highs (resistance) and pivot lows (support) from last N days."""
    if df.empty or len(df) < 10:
        return {"support": [], "resistance": []}

    recent = df.tail(lookback).copy()

    supports = []
    resistances = []

    # Find pivot points: local minima (support) and local maxima (resistance)
    # A pivot high is when a bar's high is higher than the 2 bars before and after
    # A pivot low is when a bar's low is lower than the 2 bars before and after
    window = 2  # look 2 bars each side

    for i in range(window, len(recent) - window):
        # Check for pivot high (resistance)
        is_pivot_high = True
        for j in range(1, window + 1):
            if recent["High"].iloc[i] <= recent["High"].iloc[i - j] or \
               recent["High"].iloc[i] <= recent["High"].iloc[i + j]:
                is_pivot_high = False
                break
        if is_pivot_high:
            resistances.append(recent["High"].iloc[i])

        # Check for pivot low (support)
        is_pivot_low = True
        for j in range(1, window + 1):
            if recent["Low"].iloc[i] >= recent["Low"].iloc[i - j] or \
               recent["Low"].iloc[i] >= recent["Low"].iloc[i + j]:
                is_pivot_low = False
                break
        if is_pivot_low:
            supports.append(recent["Low"].iloc[i])

    # Sort and take the most relevant (closest to current price)
    current_price = recent["Close"].iloc[-1]

    # Supports: below current price, sorted descending (closest first)
    supports = sorted([s for s in supports if s < current_price], reverse=True)
    # Resistances: above current price, sorted ascending (closest first)
    resistances = sorted([r for r in resistances if r > current_price])

    return {
        "support": supports[:3],  # top 3
        "resistance": resistances[:3],  # top 3
    }


def calculate_fibonacci(df: pd.DataFrame) -> dict:
    """Calculate Fibonacci retracement levels from recent swing high/low."""
    if df.empty or len(df) < 20:
        return {}

    # Use last 60 days or available data
    lookback = min(SR_LOOKBACK, len(df))
    recent = df.tail(lookback)

    swing_high = recent["High"].max()
    swing_low = recent["Low"].min()
    diff = swing_high - swing_low

    if diff == 0:
        return {}

    fib_levels = {
        "swing_high": swing_high,
        "swing_low": swing_low,
        "0.236": swing_high - diff * 0.236,
        "0.382": swing_high - diff * 0.382,
        "0.500": swing_high - diff * 0.500,
        "0.618": swing_high - diff * 0.618,
        "0.786": swing_high - diff * 0.786,
    }

    return fib_levels


def generate_signal(df: pd.DataFrame) -> tuple:
    """
    Generate a BUY/SELL/HOLD signal based on 8 technical indicators.

    Returns:
        tuple: (signal_str, explanation_list)
            signal_str: e.g. "🟢 BUY"
            explanation_list: list of strings explaining each indicator's vote
    """
    if df.empty or len(df) < 50:
        return "⏸️ HOLD", ["Insufficient data"]

    latest = df.iloc[-1]
    prev = df.iloc[-2] if len(df) >= 2 else latest
    signals = []
    explanations = []

    # 1. RSI signal
    if pd.notna(latest.get("RSI")):
        rsi = latest["RSI"]
        if rsi < RSI_OVERSOLD:
            signals.append(1)
            explanations.append("RSI oversold")
        elif rsi > RSI_OVERBOUGHT:
            signals.append(-1)
            explanations.append("RSI overbought")
        else:
            signals.append(0)
            explanations.append("RSI neutral")

    # 2. SMA Cross signal
    if pd.notna(latest.get("SMA_20")) and pd.notna(latest.get("SMA_50")):
        if latest["SMA_20"] > latest["SMA_50"]:
            signals.append(1)
            explanations.append("SMA20 > SMA50")
        else:
            signals.append(-1)
            explanations.append("SMA20 < SMA50")

    # 3. Price vs EMA12 signal
    if pd.notna(latest.get("EMA_12")):
        if latest["Close"] > latest["EMA_12"]:
            signals.append(1)
            explanations.append("Price above EMA12")
        else:
            signals.append(-1)
            explanations.append("Price below EMA12")

    # 4. MACD Histogram signal
    if pd.notna(latest.get("MACDh_12_26_9")):
        if latest["MACDh_12_26_9"] > 0:
            signals.append(1)
            explanations.append("MACD histogram positive")
        else:
            signals.append(-1)
            explanations.append("MACD histogram negative")

    # 5. Bollinger Bands signal
    if pd.notna(latest.get("BB_Upper")) and pd.notna(latest.get("BB_Lower")):
        price = latest["Close"]
        bb_upper = latest["BB_Upper"]
        bb_lower = latest["BB_Lower"]
        bb_range = bb_upper - bb_lower
        if bb_range > 0:
            # Price near lower band (within 10% of band width from lower)
            lower_threshold = bb_lower + bb_range * 0.1
            upper_threshold = bb_upper - bb_range * 0.1
            if price <= lower_threshold:
                signals.append(1)
                explanations.append("Near lower Bollinger band")
            elif price >= upper_threshold:
                signals.append(-1)
                explanations.append("Near upper Bollinger band")
            else:
                signals.append(0)
                explanations.append("Bollinger middle")

    # 6. Stochastic signal
    if pd.notna(latest.get("Stoch_K")) and pd.notna(prev.get("Stoch_K")):
        stoch_k = latest["Stoch_K"]
        stoch_k_prev = prev["Stoch_K"]
        stoch_d = latest.get("Stoch_D", stoch_k)

        if stoch_k < STOCH_OVERSOLD and stoch_k > stoch_k_prev:
            signals.append(1)
            explanations.append("Stoch oversold + crossing up")
        elif stoch_k > STOCH_OVERBOUGHT and stoch_k < stoch_k_prev:
            signals.append(-1)
            explanations.append("Stoch overbought + crossing down")
        else:
            signals.append(0)
            explanations.append("Stoch neutral")

    # 7. ADX signal (combined with price direction)
    if pd.notna(latest.get("ADX")):
        adx_val = latest["ADX"]
        price_direction = 1 if latest["Close"] > prev["Close"] else -1

        if adx_val > ADX_STRONG:
            # Strong trend - signal follows price direction
            signals.append(price_direction)
            if price_direction == 1:
                explanations.append(f"Strong uptrend (ADX={adx_val:.0f})")
            else:
                explanations.append(f"Strong downtrend (ADX={adx_val:.0f})")
        elif adx_val < ADX_WEAK:
            signals.append(0)
            explanations.append(f"Weak trend (ADX={adx_val:.0f})")
        else:
            # Moderate trend
            signals.append(price_direction * 0.5)
            explanations.append(f"Moderate trend (ADX={adx_val:.0f})")

    # 8. Price vs Support/Resistance
    sr = find_support_resistance(df)
    current_price = latest["Close"]
    if sr["support"] and sr["resistance"]:
        nearest_support = sr["support"][0]
        nearest_resistance = sr["resistance"][0]

        # Calculate proximity as percentage of price
        support_dist = (current_price - nearest_support) / current_price
        resistance_dist = (nearest_resistance - current_price) / current_price

        if support_dist < 0.03:  # Within 3% of support
            signals.append(1)
            explanations.append("Near support")
        elif resistance_dist < 0.03:  # Within 3% of resistance
            signals.append(-1)
            explanations.append("Near resistance")
        else:
            signals.append(0)
            explanations.append("Mid-range S/R")
    elif sr["support"]:
        nearest_support = sr["support"][0]
        support_dist = (current_price - nearest_support) / current_price
        if support_dist < 0.03:
            signals.append(1)
            explanations.append("Near support")
        else:
            signals.append(0)
            explanations.append("Mid-range S/R")
    elif sr["resistance"]:
        nearest_resistance = sr["resistance"][0]
        resistance_dist = (nearest_resistance - current_price) / current_price
        if resistance_dist < 0.03:
            signals.append(-1)
            explanations.append("Near resistance")
        else:
            signals.append(0)
            explanations.append("Mid-range S/R")
    else:
        signals.append(0)
        explanations.append("No S/R levels found")

    if not signals:
        return "⏸️ HOLD", ["No signals available"]

    avg_signal = sum(signals) / len(signals)

    if avg_signal >= 0.5:
        return "🟢 BUY", explanations
    elif avg_signal <= -0.5:
        return "🔴 SELL", explanations
    else:
        return "⏸️ HOLD", explanations


def get_suggested_levels(df: pd.DataFrame, ticker: str = "") -> dict:
    """
    Calculate suggested entry, stop loss, and target levels.

    Returns dict with:
        entry, stop_loss, target_1, target_2, risk_reward,
        support_levels, resistance_levels
    """
    if df.empty or len(df) < 50:
        return {
            "entry": 0.0,
            "stop_loss": 0.0,
            "target_1": 0.0,
            "target_2": 0.0,
            "risk_reward": "N/A",
            "support_levels": [],
            "resistance_levels": [],
        }

    latest = df.iloc[-1]
    current_price = latest["Close"]

    # Get ATR
    atr_val = latest.get("ATR", current_price * 0.02) if pd.notna(latest.get("ATR")) else current_price * 0.02

    # Get support/resistance
    sr = find_support_resistance(df)
    supports = sr["support"][:2] if sr["support"] else [current_price * 0.97]
    resistances = sr["resistance"][:2] if sr["resistance"] else [current_price * 1.05]

    # Entry: near support if available, otherwise current price
    if supports and supports[0] < current_price:
        # Entry slightly above nearest support
        entry = supports[0] * 1.005  # 0.5% above support
        # But don't go too far from current price
        if entry < current_price * 0.95:
            entry = current_price
    else:
        entry = current_price

    # Stop loss: entry - 1.5 * ATR
    stop_loss = entry - 1.5 * atr_val

    # Target 1: entry + 2 * ATR
    target_1 = entry + 2.0 * atr_val

    # Target 2: nearest resistance
    target_2 = resistances[0] if resistances else entry + 3.0 * atr_val

    # Ensure target_2 > target_1, otherwise use a higher level
    if target_2 <= target_1:
        target_2 = entry + 3.0 * atr_val

    # Risk/Reward ratio
    risk = entry - stop_loss
    reward = target_1 - entry
    if risk > 0:
        rr_ratio = reward / risk
        risk_reward = f"1:{rr_ratio:.1f}"
    else:
        risk_reward = "N/A"

    return {
        "entry": round(entry, 2),
        "stop_loss": round(stop_loss, 2),
        "target_1": round(target_1, 2),
        "target_2": round(target_2, 2),
        "risk_reward": risk_reward,
        "support_levels": [round(float(s), 2) for s in supports[:2]],
        "resistance_levels": [round(float(r), 2) for r in resistances[:2]],
    }


def get_indicator_summary(df: pd.DataFrame) -> dict:
    """Get a summary dict of ALL current indicator values for display."""
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
        summary["MACD Hist"] = f"{latest['MACDh_12_26_9']:.4f}"
    else:
        summary["MACD Hist"] = "N/A"

    # Bollinger Bands
    if pd.notna(latest.get("BB_Upper")):
        summary["BB Upper"] = f"${latest['BB_Upper']:.2f}"
        summary["BB Lower"] = f"${latest['BB_Lower']:.2f}"
    else:
        summary["BB Upper"] = "N/A"
        summary["BB Lower"] = "N/A"

    # Stochastic
    if pd.notna(latest.get("Stoch_K")):
        summary["Stoch %K"] = f"{latest['Stoch_K']:.1f}"
        summary["Stoch %D"] = f"{latest.get('Stoch_D', 0):.1f}" if pd.notna(latest.get("Stoch_D")) else "N/A"
    else:
        summary["Stoch %K"] = "N/A"
        summary["Stoch %D"] = "N/A"

    # ATR
    if pd.notna(latest.get("ATR")):
        summary["ATR(14)"] = f"{latest['ATR']:.2f}"
    else:
        summary["ATR(14)"] = "N/A"

    # ADX
    if pd.notna(latest.get("ADX")):
        adx_val = latest["ADX"]
        if adx_val > ADX_STRONG:
            trend_label = "Strong"
        elif adx_val < ADX_WEAK:
            trend_label = "Weak"
        else:
            trend_label = "Moderate"
        summary["ADX(14)"] = f"{adx_val:.1f} ({trend_label})"
    else:
        summary["ADX(14)"] = "N/A"

    return summary

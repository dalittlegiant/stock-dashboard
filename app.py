"""
📊 Stock Portfolio Dashboard
A comprehensive Streamlit app for tracking stock holdings and watchlist.
"""

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

from config import HOLDINGS, WATCHLIST
from data import get_stock_data, get_stock_info, get_stock_news, get_current_price_data
from indicators import (
    calculate_indicators, generate_signal, get_indicator_summary,
    get_suggested_levels, find_support_resistance, calculate_fibonacci,
)

# ─── Page Config ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="📊 Stock Portfolio Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─── Custom CSS ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .metric-card {
        background: #1a1a2e;
        border-radius: 10px;
        padding: 15px;
        text-align: center;
        border: 1px solid #333;
    }
    .positive { color: #00ff88; }
    .negative { color: #ff4444; }
    .signal-buy { color: #00ff88; font-weight: bold; }
    .signal-sell { color: #ff4444; font-weight: bold; }
    .signal-hold { color: #ffaa00; font-weight: bold; }
    .level-card {
        background: #16213e;
        border-radius: 10px;
        padding: 15px;
        border: 1px solid #0f3460;
        text-align: center;
    }
    .level-card h4 { margin: 0 0 5px 0; color: #aaa; font-size: 0.85em; }
    .level-card p { margin: 0; font-size: 1.3em; color: #FFD700; font-weight: bold; }
    .explanation-item {
        padding: 4px 8px;
        margin: 2px 0;
        border-radius: 4px;
        font-size: 0.9em;
    }
    .bullish-exp { background: rgba(0, 255, 136, 0.1); color: #00ff88; }
    .bearish-exp { background: rgba(255, 68, 68, 0.1); color: #ff4444; }
    .neutral-exp { background: rgba(255, 170, 0, 0.1); color: #ffaa00; }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 10px 20px;
        border-radius: 8px 8px 0 0;
    }
</style>
""", unsafe_allow_html=True)


# ─── Helper Functions ───────────────────────────────────────────────────────

def format_change(change_pct):
    """Format change percentage with color."""
    if change_pct is None:
        return "N/A"
    color = "positive" if change_pct >= 0 else "negative"
    arrow = "▲" if change_pct >= 0 else "▼"
    return f'<span class="{color}">{arrow} {abs(change_pct):.2f}%</span>'


def format_volume(vol):
    """Format volume in human-readable form."""
    if vol is None:
        return "N/A"
    if vol >= 1_000_000_000:
        return f"{vol/1_000_000_000:.2f}B"
    elif vol >= 1_000_000:
        return f"{vol/1_000_000:.2f}M"
    elif vol >= 1_000:
        return f"{vol/1_000:.1f}K"
    return str(int(vol))


def get_filtered_tickers(filter_choice: str) -> list:
    """Get list of tickers based on filter selection."""
    if filter_choice == "Holdings":
        return HOLDINGS
    elif filter_choice == "Watchlist":
        return WATCHLIST
    else:  # "All"
        return HOLDINGS + WATCHLIST


def create_price_chart_with_overlays(df: pd.DataFrame, ticker: str):
    """Create price chart with Bollinger Bands + SMA/EMA overlays."""
    fig = go.Figure()

    # Candlestick
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df["Open"],
        high=df["High"],
        low=df["Low"],
        close=df["Close"],
        name=ticker,
        increasing_line_color="#00ff88",
        decreasing_line_color="#ff4444",
    ))

    # Bollinger Bands
    if "BB_Upper" in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index, y=df["BB_Upper"], mode="lines",
            name="BB Upper", line=dict(color="rgba(173,216,230,0.5)", width=1, dash="dot")
        ))
        fig.add_trace(go.Scatter(
            x=df.index, y=df["BB_Lower"], mode="lines",
            name="BB Lower", line=dict(color="rgba(173,216,230,0.5)", width=1, dash="dot"),
            fill="tonexty", fillcolor="rgba(173,216,230,0.05)"
        ))

    # SMA
    if "SMA_20" in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index, y=df["SMA_20"], mode="lines",
            name="SMA(20)", line=dict(color="#FFD700", width=1.5)
        ))
    if "SMA_50" in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index, y=df["SMA_50"], mode="lines",
            name="SMA(50)", line=dict(color="#FF6347", width=1.5)
        ))
    if "EMA_12" in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index, y=df["EMA_12"], mode="lines",
            name="EMA(12)", line=dict(color="#00BFFF", width=1.5, dash="dash")
        ))

    fig.update_layout(
        title=f"📈 {ticker} - Price with Indicators",
        yaxis_title="Price ($)",
        template="plotly_dark",
        height=450,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=20, r=20, t=50, b=20),
    )
    return fig


def create_macd_chart(df: pd.DataFrame, ticker: str):
    """Create MACD subplot."""
    fig_macd = make_subplots(
        rows=2, cols=1, shared_xaxes=True,
        vertical_spacing=0.05, row_heights=[0.7, 0.3],
        subplot_titles=["MACD Line & Signal", "MACD Histogram"]
    )

    if "MACD_12_26_9" in df.columns:
        fig_macd.add_trace(go.Scatter(
            x=df.index, y=df["MACD_12_26_9"], mode="lines",
            name="MACD", line=dict(color="#2196F3", width=2)
        ), row=1, col=1)

    if "MACDs_12_26_9" in df.columns:
        fig_macd.add_trace(go.Scatter(
            x=df.index, y=df["MACDs_12_26_9"], mode="lines",
            name="Signal", line=dict(color="#FF9800", width=2)
        ), row=1, col=1)

    if "MACDh_12_26_9" in df.columns:
        colors = ["#00ff88" if v >= 0 else "#ff4444"
                  for v in df["MACDh_12_26_9"].fillna(0)]
        fig_macd.add_trace(go.Bar(
            x=df.index, y=df["MACDh_12_26_9"],
            name="Histogram", marker_color=colors
        ), row=2, col=1)

    fig_macd.update_layout(
        template="plotly_dark",
        height=350,
        showlegend=True,
        margin=dict(l=20, r=20, t=40, b=20),
    )
    return fig_macd


def create_stochastic_chart(df: pd.DataFrame, ticker: str):
    """Create Stochastic oscillator chart."""
    fig_stoch = go.Figure()

    if "Stoch_K" in df.columns:
        fig_stoch.add_trace(go.Scatter(
            x=df.index, y=df["Stoch_K"], mode="lines",
            name="%K", line=dict(color="#2196F3", width=2)
        ))
    if "Stoch_D" in df.columns:
        fig_stoch.add_trace(go.Scatter(
            x=df.index, y=df["Stoch_D"], mode="lines",
            name="%D", line=dict(color="#FF9800", width=2)
        ))

    # Overbought/Oversold lines
    fig_stoch.add_hline(y=80, line_dash="dash", line_color="#ff4444", opacity=0.5)
    fig_stoch.add_hline(y=20, line_dash="dash", line_color="#00ff88", opacity=0.5)

    fig_stoch.update_layout(
        title=f"📉 {ticker} - Stochastic Oscillator",
        yaxis_title="Stochastic",
        template="plotly_dark",
        height=250,
        margin=dict(l=20, r=20, t=40, b=20),
        yaxis=dict(range=[0, 100]),
    )
    return fig_stoch


def create_volume_chart(ticker: str):
    """Create a volume chart."""
    df = get_stock_data(ticker, period="3mo")
    if df.empty:
        return None

    colors = ["#00ff88" if df["Close"].iloc[i] >= df["Open"].iloc[i] else "#ff4444"
              for i in range(len(df))]

    fig = go.Figure(go.Bar(
        x=df.index,
        y=df["Volume"],
        marker_color=colors,
        name="Volume",
    ))

    fig.update_layout(
        title=f"📊 {ticker} - Volume (3 Months)",
        yaxis_title="Volume",
        template="plotly_dark",
        height=250,
        margin=dict(l=20, r=20, t=40, b=20),
    )
    return fig


def render_signal_explanation(signal_str: str, explanations: list):
    """Render signal with color-coded explanations."""
    st.markdown(f"### Signal: {signal_str}")

    if explanations:
        for exp in explanations:
            # Determine if bullish, bearish, or neutral
            exp_lower = exp.lower()
            bullish_keywords = ["oversold", "above", "positive", "uptrend", "support",
                              "lower bollinger", "crossing up", "sma20 > sma50"]
            bearish_keywords = ["overbought", "below", "negative", "downtrend", "resistance",
                               "upper bollinger", "crossing down", "sma20 < sma50"]

            if any(kw in exp_lower for kw in bullish_keywords):
                css_class = "bullish-exp"
                icon = "🟢"
            elif any(kw in exp_lower for kw in bearish_keywords):
                css_class = "bearish-exp"
                icon = "🔴"
            else:
                css_class = "neutral-exp"
                icon = "🟡"

            st.markdown(
                f'<div class="explanation-item {css_class}">{icon} {exp}</div>',
                unsafe_allow_html=True
            )


def render_suggested_levels(levels: dict):
    """Render suggested levels in a clean card format."""
    st.subheader("🎯 Suggested Trade Levels")

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.markdown(f"""
        <div class="level-card">
            <h4>📍 Entry</h4>
            <p>${levels['entry']:.2f}</p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="level-card">
            <h4>🛑 Stop Loss</h4>
            <p style="color: #ff4444;">${levels['stop_loss']:.2f}</p>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class="level-card">
            <h4>🎯 Target 1</h4>
            <p style="color: #00ff88;">${levels['target_1']:.2f}</p>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown(f"""
        <div class="level-card">
            <h4>🚀 Target 2</h4>
            <p style="color: #00ff88;">${levels['target_2']:.2f}</p>
        </div>
        """, unsafe_allow_html=True)

    with col5:
        st.markdown(f"""
        <div class="level-card">
            <h4>⚖️ Risk/Reward</h4>
            <p>{levels['risk_reward']}</p>
        </div>
        """, unsafe_allow_html=True)

    # Support and Resistance levels
    col_s, col_r = st.columns(2)
    with col_s:
        support_str = ", ".join([f"${s:.2f}" for s in levels["support_levels"]]) if levels["support_levels"] else "N/A"
        st.markdown(f"""
        <div class="level-card" style="margin-top: 10px;">
            <h4>🟢 Support Levels</h4>
            <p style="font-size: 1.0em;">{support_str}</p>
        </div>
        """, unsafe_allow_html=True)

    with col_r:
        resistance_str = ", ".join([f"${r:.2f}" for r in levels["resistance_levels"]]) if levels["resistance_levels"] else "N/A"
        st.markdown(f"""
        <div class="level-card" style="margin-top: 10px;">
            <h4>🔴 Resistance Levels</h4>
            <p style="font-size: 1.0em;">{resistance_str}</p>
        </div>
        """, unsafe_allow_html=True)


# ─── TAB 1: Portfolio Overview ─────────────────────────────────────────────
def render_portfolio_overview(tickers: list):
    """Render the Portfolio Overview tab."""
    st.header("💼 Portfolio Overview")
    st.markdown("---")

    # Build table
    holdings_data = []
    for ticker in tickers:
        price_data = get_current_price_data(ticker)
        df = get_stock_data(ticker, period="1y")
        if not df.empty:
            df = calculate_indicators(df)
            signal_str, _ = generate_signal(df)
        else:
            signal_str = "⏸️ HOLD"

        if not price_data["error"]:
            holdings_data.append({
                "Ticker": ticker,
                "Price ($)": f"${price_data['price']:.2f}",
                "Daily Change": format_change(price_data["change_pct"]),
                "Volume": format_volume(price_data["volume"]),
                "Signal": signal_str,
            })
        else:
            holdings_data.append({
                "Ticker": ticker,
                "Price ($)": "N/A",
                "Daily Change": "N/A",
                "Volume": "N/A",
                "Signal": signal_str,
            })

    # Display as styled HTML table
    table_html = """
    <table style="width:100%; border-collapse: collapse; text-align: center;">
    <tr style="border-bottom: 2px solid #444;">
        <th style="padding: 10px; color: #4CAF50;">Ticker</th>
        <th style="padding: 10px; color: #4CAF50;">Price</th>
        <th style="padding: 10px; color: #4CAF50;">Daily Change</th>
        <th style="padding: 10px; color: #4CAF50;">Volume</th>
        <th style="padding: 10px; color: #4CAF50;">Signal</th>
    </tr>
    """
    for row in holdings_data:
        table_html += f"""
    <tr style="border-bottom: 1px solid #333;">
        <td style="padding: 10px; font-weight: bold; color: #FFD700;">{row['Ticker']}</td>
        <td style="padding: 10px;">{row['Price ($)']}</td>
        <td style="padding: 10px;">{row['Daily Change']}</td>
        <td style="padding: 10px;">{row['Volume']}</td>
        <td style="padding: 10px; font-size: 1.1em;">{row['Signal']}</td>
    </tr>
    """
    table_html += "</table>"
    st.markdown(table_html, unsafe_allow_html=True)

    st.markdown("---")

    # Interactive price chart
    st.subheader("📈 Price Chart")
    selected_stock = st.selectbox("Select a stock to view:", tickers, key="overview_select")

    col1, col2 = st.columns([3, 1])
    with col1:
        df = get_stock_data(selected_stock, period="1y")
        if not df.empty:
            df = calculate_indicators(df)
            chart = create_price_chart_with_overlays(df, selected_stock)
            st.plotly_chart(chart, use_container_width=True, key="overview_price_chart")
        else:
            st.warning(f"⚠️ No data available for {selected_stock}")

    with col2:
        st.markdown("#### 📋 Quick Stats")
        df_stats = get_stock_data(selected_stock, period="1y")
        if not df_stats.empty:
            high_52w = df_stats["High"].max()
            low_52w = df_stats["Low"].min()
            avg_vol = df_stats["Volume"].mean()
            current = df_stats["Close"].iloc[-1]

            st.metric("52W High", f"${high_52w:.2f}")
            st.metric("52W Low", f"${low_52w:.2f}")
            st.metric("Avg Volume", format_volume(avg_vol))
            pct_from_high = ((current - high_52w) / high_52w) * 100
            st.metric("From 52W High", f"{pct_from_high:.1f}%")


# ─── TAB 2: Daily Report ───────────────────────────────────────────────────
def render_daily_report(tickers: list):
    """Render the Daily Report tab."""
    st.header("📅 Daily Report")
    st.markdown("---")

    st.subheader("📊 Today's Performance")

    # Performance cards in columns (handle up to 12 stocks)
    num_cols = min(len(tickers), 6)
    rows_needed = (len(tickers) + num_cols - 1) // num_cols

    for row_idx in range(rows_needed):
        start = row_idx * num_cols
        end = min(start + num_cols, len(tickers))
        row_tickers = tickers[start:end]
        cols = st.columns(len(row_tickers))

        for i, ticker in enumerate(row_tickers):
            price_data = get_current_price_data(ticker)
            with cols[i]:
                if not price_data["error"]:
                    color_class = "positive" if price_data["change_pct"] >= 0 else "negative"
                    arrow = "▲" if price_data["change_pct"] >= 0 else "▼"
                    st.markdown(f"""
                    <div class="metric-card">
                        <h3 style="color: #FFD700; margin: 0;">{ticker}</h3>
                        <p style="font-size: 1.4em; margin: 5px 0;">${price_data['price']:.2f}</p>
                        <p class="{color_class}" style="font-size: 1.1em; margin: 0;">
                            {arrow} {abs(price_data['change_pct']):.2f}%
                        </p>
                        <p style="color: #888; font-size: 0.8em; margin: 5px 0 0 0;">
                            Vol: {format_volume(price_data['volume'])}
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div class="metric-card">
                        <h3 style="color: #FFD700; margin: 0;">{ticker}</h3>
                        <p style="color: #888;">⚠️ Data unavailable</p>
                    </div>
                    """, unsafe_allow_html=True)

    st.markdown("---")

    # News section
    st.subheader("📰 News Highlights")
    news_ticker = st.selectbox("Select a stock for news:", tickers, key="news_select")

    news = get_stock_news(news_ticker)
    if news:
        for idx, item in enumerate(news, 1):
            title = item.get("title", "No title")
            publisher = item.get("publisher", "Unknown")
            link = item.get("link", "#")

            with st.container():
                st.markdown(f"**{idx}. [{title}]({link})**")
                st.caption(f"📰 {publisher}")
                st.markdown("---")
    else:
        st.info(f"📭 No news available for {news_ticker} at the moment.")

    # Daily summary chart
    st.markdown("---")
    st.subheader("📉 Daily Price Movement")

    chart_data = {}
    for ticker in tickers:
        price_data = get_current_price_data(ticker)
        if not price_data["error"] and price_data["change_pct"] is not None:
            chart_data[ticker] = price_data["change_pct"]

    if chart_data:
        fig = go.Figure(go.Bar(
            x=list(chart_data.keys()),
            y=list(chart_data.values()),
            marker_color=["#00ff88" if v >= 0 else "#ff4444" for v in chart_data.values()],
            text=[f"{v:+.2f}%" for v in chart_data.values()],
            textposition="outside",
        ))
        fig.update_layout(
            title="Daily Change %",
            yaxis_title="Change (%)",
            template="plotly_dark",
            height=350,
            margin=dict(l=20, r=20, t=40, b=20),
        )
        st.plotly_chart(fig, use_container_width=True, key="daily_change_chart")


# ─── TAB 3: Technical Analysis ─────────────────────────────────────────────
def render_technical_analysis(tickers: list):
    """Render the Technical Analysis tab."""
    st.header("📈 Technical Analysis")
    st.markdown("---")

    # Stock selector
    selected = st.selectbox("🔍 Select stock for analysis:", tickers, key="ta_select")

    # Fetch and calculate
    df = get_stock_data(selected, period="1y")
    if df.empty:
        st.error(f"❌ Could not load data for {selected}")
        return

    df = calculate_indicators(df)
    signal_str, explanations = generate_signal(df)
    indicators = get_indicator_summary(df)

    # Signal and price
    col1, col2 = st.columns([2, 1])
    with col1:
        render_signal_explanation(signal_str, explanations)
    with col2:
        price_data = get_current_price_data(selected)
        if not price_data["error"]:
            st.metric("Current Price", f"${price_data['price']:.2f}",
                      f"{price_data['change_pct']:+.2f}%")

    st.markdown("---")

    # Indicator cards (display in rows of 4)
    st.subheader("📐 Technical Indicators")
    indicator_items = list(indicators.items())
    for i in range(0, len(indicator_items), 4):
        row_items = indicator_items[i:i+4]
        ind_cols = st.columns(len(row_items))
        for j, (name, value) in enumerate(row_items):
            with ind_cols[j]:
                st.markdown(f"""
                <div class="metric-card">
                    <p style="color: #888; margin: 0; font-size: 0.85em;">{name}</p>
                    <p style="font-size: 1.2em; margin: 5px 0; color: #FFD700;">{value}</p>
                </div>
                """, unsafe_allow_html=True)

    st.markdown("---")

    # Price chart with Bollinger Bands + SMA/EMA
    st.subheader("📊 Price Chart with Indicators")
    price_chart = create_price_chart_with_overlays(df, selected)
    st.plotly_chart(price_chart, use_container_width=True, key="ta_price_chart")

    # MACD chart
    st.markdown("---")
    st.subheader("📉 MACD")
    macd_chart = create_macd_chart(df, selected)
    st.plotly_chart(macd_chart, use_container_width=True, key="ta_macd_chart")

    # Stochastic chart
    st.markdown("---")
    st.subheader("📈 Stochastic Oscillator")
    stoch_chart = create_stochastic_chart(df, selected)
    st.plotly_chart(stoch_chart, use_container_width=True, key="ta_stoch_chart")

    # Volume chart
    st.markdown("---")
    vol_chart = create_volume_chart(selected)
    if vol_chart:
        st.plotly_chart(vol_chart, use_container_width=True, key="ta_volume_chart")

    # Suggested Levels
    st.markdown("---")
    levels = get_suggested_levels(df, selected)
    render_suggested_levels(levels)

    # Fibonacci levels
    fib = calculate_fibonacci(df)
    if fib:
        st.markdown("---")
        st.subheader("🌀 Fibonacci Retracement")
        fib_cols = st.columns(7)
        fib_labels = ["swing_high", "0.236", "0.382", "0.500", "0.618", "0.786", "swing_low"]
        fib_display = ["Swing High", "23.6%", "38.2%", "50.0%", "61.8%", "78.6%", "Swing Low"]
        for i, (label, display) in enumerate(zip(fib_labels, fib_display)):
            with fib_cols[i]:
                val = fib.get(label, 0)
                st.markdown(f"""
                <div class="metric-card">
                    <p style="color: #888; margin: 0; font-size: 0.8em;">{display}</p>
                    <p style="font-size: 1.0em; margin: 5px 0; color: #E0B0FF;">${val:.2f}</p>
                </div>
                """, unsafe_allow_html=True)


# ─── TAB 4: Summary ────────────────────────────────────────────────────────
def render_summary(tickers: list):
    """Render the Summary comparison table."""
    st.header("📊 Summary")
    st.markdown("---")

    st.subheader("📋 Comparison Table")

    summary_rows = []
    for ticker in tickers:
        df = get_stock_data(ticker, period="1y")
        if not df.empty:
            df = calculate_indicators(df)
            signal_str, _ = generate_signal(df)
            ind = get_indicator_summary(df)
            price_data = get_current_price_data(ticker)

            latest = df.iloc[-1]
            atr_val = f"{latest['ATR']:.2f}" if pd.notna(latest.get("ATR")) else "N/A"
            adx_val = f"{latest['ADX']:.1f}" if pd.notna(latest.get("ADX")) else "N/A"

            if not price_data["error"]:
                price = f"${price_data['price']:.2f}"
                change_html = format_change(price_data["change_pct"])
            else:
                price = "N/A"
                change_html = "N/A"

            summary_rows.append({
                "Ticker": ticker,
                "Price": price,
                "Change": change_html,
                "RSI": ind.get("RSI(14)", "N/A"),
                "Signal": signal_str,
                "ATR": atr_val,
                "ADX": adx_val,
            })
        else:
            summary_rows.append({
                "Ticker": ticker,
                "Price": "N/A",
                "Change": "N/A",
                "RSI": "N/A",
                "Signal": "⏸️ HOLD",
                "ATR": "N/A",
                "ADX": "N/A",
            })

    # Render as HTML table
    table_html = """
    <table style="width:100%; border-collapse: collapse; text-align: center;">
    <tr style="border-bottom: 2px solid #444;">
        <th style="padding: 12px; color: #4CAF50;">Ticker</th>
        <th style="padding: 12px; color: #4CAF50;">Price</th>
        <th style="padding: 12px; color: #4CAF50;">Change</th>
        <th style="padding: 12px; color: #4CAF50;">RSI(14)</th>
        <th style="padding: 12px; color: #4CAF50;">Signal</th>
        <th style="padding: 12px; color: #4CAF50;">ATR</th>
        <th style="padding: 12px; color: #4CAF50;">ADX</th>
    </tr>
    """
    for row in summary_rows:
        table_html += f"""
    <tr style="border-bottom: 1px solid #333;">
        <td style="padding: 12px; font-weight: bold; color: #FFD700;">{row['Ticker']}</td>
        <td style="padding: 12px;">{row['Price']}</td>
        <td style="padding: 12px;">{row['Change']}</td>
        <td style="padding: 12px;">{row['RSI']}</td>
        <td style="padding: 12px; font-size: 1.1em;">{row['Signal']}</td>
        <td style="padding: 12px;">{row['ATR']}</td>
        <td style="padding: 12px;">{row['ADX']}</td>
    </tr>
    """
    table_html += "</table>"
    st.markdown(table_html, unsafe_allow_html=True)


# ─── Main App ──────────────────────────────────────────────────────────────
def main():
    from data import get_last_fetch_time
    
    st.markdown("# 📊 Stock Portfolio Dashboard")
    
    # Fetch one stock to trigger data fetch, then get the timestamp
    get_stock_data("AAPL", period="5d")
    last_update = get_last_fetch_time()
    
    st.caption(f"🕐 Data refreshes every 5 minutes | Last update: {last_update} | Powered by Yahoo Finance")
    st.markdown("---")

    # Sidebar-style filter at the top (persists across tabs)
    col_filter, col_spacer = st.columns([1, 4])
    with col_filter:
        filter_choice = st.selectbox(
            "🔍 Filter:",
            options=["All", "Holdings", "Watchlist"],
            key="portfolio_filter",
        )

    # Get filtered tickers
    tickers = get_filtered_tickers(filter_choice)

    # Tabs
    tabs = st.tabs([
        "💼 Portfolio Overview",
        "📅 Daily Report",
        "📈 Technical Analysis",
        "📊 Summary",
    ])

    with tabs[0]:
        render_portfolio_overview(tickers)

    with tabs[1]:
        render_daily_report(tickers)

    with tabs[2]:
        render_technical_analysis(tickers)

    with tabs[3]:
        render_summary(tickers)

    # Footer
    st.markdown("---")
    st.markdown(
        '<p style="text-align: center; color: #666;">'
        '📊 Stock Portfolio Dashboard | Data provided by Yahoo Finance | '
        'Not financial advice ⚠️</p>',
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()

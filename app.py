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
from indicators import calculate_indicators, generate_signal, get_indicator_summary

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


def create_price_chart(ticker: str, show_ma: bool = False):
    """Create an interactive price chart with plotly."""
    df = get_stock_data(ticker, period="1y")
    if df.empty:
        st.warning(f"⚠️ No data available for {ticker}")
        return None

    if show_ma:
        df = calculate_indicators(df)

    fig = go.Figure()

    # Candlestick chart
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

    if show_ma:
        # Add moving averages
        if "SMA_20" in df.columns:
            fig.add_trace(go.Scatter(
                x=df.index, y=df["SMA_20"],
                mode="lines", name="SMA(20)",
                line=dict(color="#FFD700", width=1.5)
            ))
        if "SMA_50" in df.columns:
            fig.add_trace(go.Scatter(
                x=df.index, y=df["SMA_50"],
                mode="lines", name="SMA(50)",
                line=dict(color="#FF6347", width=1.5)
            ))
        if "EMA_12" in df.columns:
            fig.add_trace(go.Scatter(
                x=df.index, y=df["EMA_12"],
                mode="lines", name="EMA(12)",
                line=dict(color="#00BFFF", width=1.5, dash="dash")
            ))

    fig.update_layout(
        title=f"📈 {ticker} - 1 Year Price",
        yaxis_title="Price ($)",
        xaxis_title="Date",
        template="plotly_dark",
        height=450,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=20, r=20, t=40, b=20),
    )

    return fig


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


# ─── TAB 1: Portfolio Overview ─────────────────────────────────────────────
def render_portfolio_overview():
    """Render the Portfolio Overview tab."""
    st.header("📊 Portfolio Overview")
    st.markdown("---")

    # Build holdings table
    st.subheader("💼 Current Holdings")
    
    holdings_data = []
    for ticker in HOLDINGS:
        price_data = get_current_price_data(ticker)
        if not price_data["error"]:
            holdings_data.append({
                "Ticker": ticker,
                "Price ($)": f"${price_data['price']:.2f}",
                "Daily Change": format_change(price_data["change_pct"]),
                "Volume": format_volume(price_data["volume"]),
                "_change_raw": price_data["change_pct"],
            })
        else:
            holdings_data.append({
                "Ticker": ticker,
                "Price ($)": "N/A",
                "Daily Change": "N/A",
                "Volume": "N/A",
                "_change_raw": None,
            })

    # Display as styled HTML table
    table_html = """
    <table style="width:100%; border-collapse: collapse; text-align: center;">
    <tr style="border-bottom: 2px solid #444;">
        <th style="padding: 10px; color: #4CAF50;">Ticker</th>
        <th style="padding: 10px; color: #4CAF50;">Price</th>
        <th style="padding: 10px; color: #4CAF50;">Daily Change</th>
        <th style="padding: 10px; color: #4CAF50;">Volume</th>
    </tr>
    """
    for row in holdings_data:
        table_html += f"""
    <tr style="border-bottom: 1px solid #333;">
        <td style="padding: 10px; font-weight: bold; color: #FFD700;">{row['Ticker']}</td>
        <td style="padding: 10px;">{row['Price ($)']}</td>
        <td style="padding: 10px;">{row['Daily Change']}</td>
        <td style="padding: 10px;">{row['Volume']}</td>
    </tr>
    """
    table_html += "</table>"
    st.markdown(table_html, unsafe_allow_html=True)

    st.markdown("---")

    # Interactive price chart
    st.subheader("📈 Price Chart")
    selected_stock = st.selectbox("Select a stock to view:", HOLDINGS, key="overview_select")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        chart = create_price_chart(selected_stock)
        if chart:
            st.plotly_chart(chart, use_container_width=True)

    with col2:
        st.markdown("#### 📋 Quick Stats")
        df = get_stock_data(selected_stock, period="1y")
        if not df.empty:
            high_52w = df["High"].max()
            low_52w = df["Low"].min()
            avg_vol = df["Volume"].mean()
            current = df["Close"].iloc[-1]
            
            st.metric("52W High", f"${high_52w:.2f}")
            st.metric("52W Low", f"${low_52w:.2f}")
            st.metric("Avg Volume", format_volume(avg_vol))
            pct_from_high = ((current - high_52w) / high_52w) * 100
            st.metric("From 52W High", f"{pct_from_high:.1f}%")


# ─── TAB 2: Daily Report ───────────────────────────────────────────────────
def render_daily_report():
    """Render the Daily Report tab."""
    st.header("📅 Daily Report")
    st.markdown("---")

    st.subheader("📊 Today's Performance")
    
    # Performance cards in columns
    cols = st.columns(len(HOLDINGS))
    for i, ticker in enumerate(HOLDINGS):
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
    news_ticker = st.selectbox("Select a stock for news:", HOLDINGS, key="news_select")
    
    news = get_stock_news(news_ticker)
    if news:
        for idx, item in enumerate(news, 1):
            title = item.get("title", "No title")
            publisher = item.get("publisher", "Unknown")
            link = item.get("link", "#")
            published = item.get("providerPublishTime", "")
            
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
    for ticker in HOLDINGS:
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
            title="Daily Change % - All Holdings",
            yaxis_title="Change (%)",
            template="plotly_dark",
            height=350,
            margin=dict(l=20, r=20, t=40, b=20),
        )
        st.plotly_chart(fig, use_container_width=True)


# ─── TAB 3: Weekly Report ──────────────────────────────────────────────────
def render_weekly_report():
    """Render the Weekly Report tab with technical analysis."""
    st.header("📈 Weekly Report - Technical Analysis")
    st.markdown("---")

    # Stock selector
    selected = st.selectbox("🔍 Select stock for analysis:", HOLDINGS, key="weekly_select")

    # Fetch and calculate
    df = get_stock_data(selected, period="1y")
    if df.empty:
        st.error(f"❌ Could not load data for {selected}")
        return

    df = calculate_indicators(df)
    signal = generate_signal(df)
    indicators = get_indicator_summary(df)

    # Signal and summary
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        st.markdown(f"### Signal: {signal}")
    with col2:
        price_data = get_current_price_data(selected)
        if not price_data["error"]:
            st.metric("Current Price", f"${price_data['price']:.2f}",
                      f"{price_data['change_pct']:+.2f}%")
    with col3:
        if indicators.get("RSI(14)", "N/A") != "N/A":
            rsi_val = float(indicators["RSI(14)"])
            rsi_label = "Oversold" if rsi_val < 30 else ("Overbought" if rsi_val > 70 else "Neutral")
            st.metric("RSI(14)", indicators["RSI(14)"], rsi_label)

    st.markdown("---")

    # Indicator cards
    st.subheader("📐 Technical Indicators")
    ind_cols = st.columns(len(indicators))
    for i, (name, value) in enumerate(indicators.items()):
        with ind_cols[i]:
            st.markdown(f"""
            <div class="metric-card">
                <p style="color: #888; margin: 0; font-size: 0.85em;">{name}</p>
                <p style="font-size: 1.2em; margin: 5px 0; color: #FFD700;">{value}</p>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")

    # Price chart with moving averages
    st.subheader("📊 Price Chart with Moving Averages")
    chart = create_price_chart(selected, show_ma=True)
    if chart:
        st.plotly_chart(chart, use_container_width=True)

    # MACD Chart
    st.markdown("---")
    st.subheader("📉 MACD")
    macd_col = [c for c in df.columns if "MACD_12_26_9" in c and "h" not in c.lower() and "s" not in c.lower()]
    macd_hist_col = [c for c in df.columns if "MACDh" in c]
    macd_signal_col = [c for c in df.columns if "MACDs" in c]

    if macd_col:
        fig_macd = make_subplots(rows=2, cols=1, shared_xaxes=True,
                                  vertical_spacing=0.05, row_heights=[0.7, 0.3],
                                  subplot_titles=["MACD Line & Signal", "MACD Histogram"])
        
        fig_macd.add_trace(go.Scatter(
            x=df.index, y=df[macd_col[0]], mode="lines",
            name="MACD", line=dict(color="#2196F3", width=2)
        ), row=1, col=1)
        
        if macd_signal_col:
            fig_macd.add_trace(go.Scatter(
                x=df.index, y=df[macd_signal_col[0]], mode="lines",
                name="Signal", line=dict(color="#FF9800", width=2)
            ), row=1, col=1)
        
        if macd_hist_col:
            colors = ["#00ff88" if v >= 0 else "#ff4444" for v in df[macd_hist_col[0]].fillna(0)]
            fig_macd.add_trace(go.Bar(
                x=df.index, y=df[macd_hist_col[0]],
                name="Histogram", marker_color=colors
            ), row=2, col=1)
        
        fig_macd.update_layout(
            template="plotly_dark",
            height=400,
            showlegend=True,
            margin=dict(l=20, r=20, t=40, b=20),
        )
        st.plotly_chart(fig_macd, use_container_width=True)

    # Full analysis table for all holdings
    st.markdown("---")
    st.subheader("📋 All Holdings - Signal Summary")
    
    summary_rows = []
    for ticker in HOLDINGS:
        tdf = get_stock_data(ticker, period="1y")
        if not tdf.empty:
            tdf = calculate_indicators(tdf)
            t_signal = generate_signal(tdf)
            t_indicators = get_indicator_summary(tdf)
            price_data = get_current_price_data(ticker)
            price = f"${price_data['price']:.2f}" if not price_data["error"] else "N/A"
            summary_rows.append({
                "Ticker": ticker,
                "Price": price,
                "RSI(14)": t_indicators.get("RSI(14)", "N/A"),
                "SMA(20)": t_indicators.get("SMA(20)", "N/A"),
                "Signal": t_signal,
            })
    
    if summary_rows:
        for row in summary_rows:
            col_a, col_b, col_c, col_d, col_e = st.columns([1, 1, 1, 1, 1])
            col_a.markdown(f"**{row['Ticker']}**")
            col_b.write(row["Price"])
            col_c.write(f"RSI: {row['RSI(14)']}")
            col_d.write(row["SMA(20)"])
            col_e.markdown(row["Signal"])


# ─── TAB 4: Watchlist ──────────────────────────────────────────────────────
def render_watchlist():
    """Render the Watchlist tab."""
    st.header("👀 Watchlist")
    st.markdown("---")

    # Watchlist table with analysis
    st.subheader("📋 Watchlist Overview")
    
    watch_rows = []
    for ticker in WATCHLIST:
        price_data = get_current_price_data(ticker)
        df = get_stock_data(ticker, period="1y")
        
        if not df.empty:
            df = calculate_indicators(df)
            signal = generate_signal(df)
            indicators = get_indicator_summary(df)
        else:
            signal = "⏸️ HOLD"
            indicators = {}
        
        if not price_data["error"]:
            change_html = format_change(price_data["change_pct"])
            price = f"${price_data['price']:.2f}"
        else:
            change_html = "N/A"
            price = "N/A"
        
        watch_rows.append({
            "ticker": ticker,
            "price": price,
            "change": change_html,
            "rsi": indicators.get("RSI(14)", "N/A"),
            "signal": signal,
            "volume": format_volume(price_data["volume"]) if not price_data["error"] else "N/A",
        })

    # Render table
    table_html = """
    <table style="width:100%; border-collapse: collapse; text-align: center;">
    <tr style="border-bottom: 2px solid #444;">
        <th style="padding: 12px; color: #4CAF50;">Ticker</th>
        <th style="padding: 12px; color: #4CAF50;">Price</th>
        <th style="padding: 12px; color: #4CAF50;">Change</th>
        <th style="padding: 12px; color: #4CAF50;">RSI(14)</th>
        <th style="padding: 12px; color: #4CAF50;">Volume</th>
        <th style="padding: 12px; color: #4CAF50;">Signal</th>
    </tr>
    """
    for row in watch_rows:
        table_html += f"""
    <tr style="border-bottom: 1px solid #333;">
        <td style="padding: 12px; font-weight: bold; color: #FFD700;">{row['ticker']}</td>
        <td style="padding: 12px;">{row['price']}</td>
        <td style="padding: 12px;">{row['change']}</td>
        <td style="padding: 12px;">{row['rsi']}</td>
        <td style="padding: 12px;">{row['volume']}</td>
        <td style="padding: 12px; font-size: 1.1em;">{row['signal']}</td>
    </tr>
    """
    table_html += "</table>"
    st.markdown(table_html, unsafe_allow_html=True)

    st.markdown("---")

    # Detailed analysis for selected watchlist stock
    st.subheader("🔍 Detailed Analysis")
    selected_watch = st.selectbox("Select a watchlist stock:", WATCHLIST, key="watch_select")

    df = get_stock_data(selected_watch, period="1y")
    if df.empty:
        st.warning(f"⚠️ Could not load data for {selected_watch}")
        return

    df = calculate_indicators(df)
    signal = generate_signal(df)
    indicators = get_indicator_summary(df)

    # Signal display
    col1, col2 = st.columns([1, 1])
    with col1:
        st.markdown(f"### Signal: {signal}")
    with col2:
        if indicators:
            st.markdown(f"**RSI(14):** {indicators.get('RSI(14)', 'N/A')} | "
                       f"**SMA(20):** {indicators.get('SMA(20)', 'N/A')} | "
                       f"**EMA(12):** {indicators.get('EMA(12)', 'N/A')}")

    # Price chart with MAs
    chart = create_price_chart(selected_watch, show_ma=True)
    if chart:
        st.plotly_chart(chart, use_container_width=True)

    # Volume chart
    vol_chart = create_volume_chart(selected_watch)
    if vol_chart:
        st.plotly_chart(vol_chart, use_container_width=True)


# ─── Main App ──────────────────────────────────────────────────────────────
def main():
    st.markdown("# 📊 Stock Portfolio Dashboard")
    st.caption("🕐 Data refreshes every 5 minutes | Powered by Yahoo Finance")
    st.markdown("---")

    tabs = st.tabs([
        "💼 Portfolio Overview",
        "📅 Daily Report",
        "📈 Weekly Report",
        "👀 Watchlist"
    ])

    with tabs[0]:
        render_portfolio_overview()

    with tabs[1]:
        render_daily_report()

    with tabs[2]:
        render_weekly_report()

    with tabs[3]:
        render_watchlist()

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

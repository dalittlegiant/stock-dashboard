"""
📊 Stock Portfolio Dashboard
A comprehensive Streamlit app for tracking stock holdings and watchlist.
"""

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import yaml
import os

from config import HOLDINGS, WATCHLIST
from data import get_stock_data, get_stock_info, get_stock_news, get_current_price_data, get_enhanced_price_data
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


# ─── Classification Data ───────────────────────────────────────────────────

@st.cache_data
def load_classification_data():
    """Load and parse the sp100.yaml classification data."""
    yaml_path = os.path.join(os.path.dirname(__file__), "data", "sp100.yaml")
    with open(yaml_path, "r") as f:
        data = yaml.safe_load(f)

    # Build lookup dict: ticker -> {name, sector, style, themes}
    lookup = {}
    all_tickers = []
    sectors = set()
    styles = set()
    themes = set()

    for stock in data.get("stocks", []):
        ticker = stock["ticker"]
        all_tickers.append(ticker)
        lookup[ticker] = {
            "name": stock.get("name", ticker),
            "sector": stock.get("sector", "Unknown"),
            "style": stock.get("style", "Unknown"),
            "themes": stock.get("themes", []),
        }
        sectors.add(stock.get("sector", "Unknown"))
        styles.add(stock.get("style", "Unknown"))
        for theme in stock.get("themes", []):
            themes.add(theme)

    return {
        "lookup": lookup,
        "all_tickers": all_tickers,
        "sectors": sorted(sectors),
        "styles": sorted(styles),
        "themes": sorted(themes),
    }


# ─── Holdings Management ────────────────────────────────────────────────────

HOLDINGS_CSV_PATH = os.path.join(os.path.dirname(__file__), "data", "holdings.csv")


def load_holdings_data():
    """Load holdings data from CSV or create default from config."""
    if os.path.exists(HOLDINGS_CSV_PATH):
        try:
            df = pd.read_csv(HOLDINGS_CSV_PATH)
            # Ensure required columns
            required_cols = ["ticker", "shares", "avg_cost", "is_holding", "is_watchlist"]
            for col in required_cols:
                if col not in df.columns:
                    if col in ["is_holding", "is_watchlist"]:
                        df[col] = False
                    else:
                        df[col] = 0
            return df
        except Exception:
            pass

    # Create default from config
    rows = []
    for ticker in HOLDINGS:
        rows.append({"ticker": ticker, "shares": 0.0, "avg_cost": 0.0, "is_holding": True, "is_watchlist": False})
    for ticker in WATCHLIST:
        rows.append({"ticker": ticker, "shares": 0.0, "avg_cost": 0.0, "is_holding": False, "is_watchlist": True})
    df = pd.DataFrame(rows)
    return df


def save_holdings_data(df):
    """Save holdings data to CSV."""
    os.makedirs(os.path.dirname(HOLDINGS_CSV_PATH), exist_ok=True)
    df.to_csv(HOLDINGS_CSV_PATH, index=False)


def get_dynamic_holdings_and_watchlist():
    """Get current holdings and watchlist from CSV if it exists, else from config."""
    if os.path.exists(HOLDINGS_CSV_PATH):
        try:
            df = pd.read_csv(HOLDINGS_CSV_PATH)
            holdings = df[df["is_holding"] == True]["ticker"].tolist()
            watchlist = df[df["is_watchlist"] == True]["ticker"].tolist()
            return holdings, watchlist
        except Exception:
            pass
    return list(HOLDINGS), list(WATCHLIST)


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


def apply_universe_filter(all_tickers, sector, style, selected_themes, classification_data):
    """Apply Level 1 universe filter (Sector + Style + Tags only)."""
    lookup = classification_data["lookup"]
    tickers = list(all_tickers)

    if sector != "All":
        tickers = [t for t in tickers if lookup.get(t, {}).get("sector") == sector or t not in lookup]

    if style != "All":
        tickers = [t for t in tickers if lookup.get(t, {}).get("style") == style or t not in lookup]

    if selected_themes:
        tickers = [
            t for t in tickers
            if t not in lookup or
            any(theme in lookup[t].get("themes", []) for theme in selected_themes)
        ]

    return tickers


def get_filtered_tickers(filter_choice: str, sector: str = "All", style: str = "All",
                         selected_themes: list = None, classification_data: dict = None) -> list:
    """Get list of tickers based on combined filter selections (legacy compatibility)."""
    if classification_data is None:
        classification_data = load_classification_data()

    holdings, watchlist = get_dynamic_holdings_and_watchlist()

    # Step 1: Start with portfolio filter
    if filter_choice == "Holdings":
        tickers = list(holdings)
    elif filter_choice == "Watchlist":
        tickers = list(watchlist)
    else:  # "All" - use all tickers from YAML
        tickers = list(classification_data["all_tickers"])

    # Step 2-4: Apply universe filter
    return apply_universe_filter(tickers, sector, style, selected_themes, classification_data)


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


# ─── TAB 1: Portfolio Overview (Restructured) ──────────────────────────────
def render_portfolio_overview(universe_tickers: list, classification_data: dict):
    """Render the Portfolio Overview tab with 3-level filtering."""
    st.header("💼 Portfolio Overview")
    st.markdown("---")

    lookup = classification_data["lookup"]
    holdings, watchlist = get_dynamic_holdings_and_watchlist()

    # ── Level 2: Scope Selector ──
    scope_choice = st.radio(
        "Scope:",
        options=["Holdings Only", "Watchlist Only", "Holdings + Watchlist"],
        horizontal=True,
        key="tab1_scope",
    )

    # Apply Level 2 scope
    if scope_choice == "Holdings Only":
        scope_tickers = [t for t in holdings if t in universe_tickers]
    elif scope_choice == "Watchlist Only":
        scope_tickers = [t for t in watchlist if t in universe_tickers]
    else:  # Holdings + Watchlist
        combined = list(dict.fromkeys(holdings + watchlist))  # preserve order, no dupes
        scope_tickers = [t for t in combined if t in universe_tickers]

    # ── Holdings Management Expander ──
    with st.expander("⚙️ Manage Holdings & Watchlist"):
        holdings_df = load_holdings_data()
        edited_df = st.data_editor(
            holdings_df,
            num_rows="dynamic",
            column_config={
                "ticker": st.column_config.TextColumn("Ticker", width="small"),
                "shares": st.column_config.NumberColumn("Shares", min_value=0.0, step=1.0, format="%.2f"),
                "avg_cost": st.column_config.NumberColumn("Avg Cost ($)", min_value=0.0, step=1.0, format="%.2f"),
                "is_holding": st.column_config.CheckboxColumn("Holding"),
                "is_watchlist": st.column_config.CheckboxColumn("Watchlist"),
            },
            key="holdings_editor",
            use_container_width=True,
        )
        if st.button("💾 Save Holdings", key="save_holdings_btn"):
            save_holdings_data(edited_df)
            st.success("✅ Holdings saved!")
            st.rerun()

    st.markdown("---")

    # ── Build summary table ──
    if not scope_tickers:
        st.warning("⚠️ No stocks match the current filters. Adjust your Level 1 or Level 2 selections.")
        return

    # Load holdings data for P&L calcs
    holdings_positions = load_holdings_data()
    pos_lookup = {}
    for _, row in holdings_positions.iterrows():
        pos_lookup[row["ticker"]] = {"shares": row["shares"], "avg_cost": row["avg_cost"]}

    rows = []
    zero_shares_tickers = []
    for ticker in scope_tickers:
        enhanced = get_enhanced_price_data(ticker)
        df_hist = get_stock_data(ticker, period="1y")
        if not df_hist.empty:
            df_hist = calculate_indicators(df_hist)
            signal_str, _ = generate_signal(df_hist)
        else:
            signal_str = "⏸️ HOLD"

        stock_info = lookup.get(ticker, {})
        company = stock_info.get("name", ticker)
        sector = stock_info.get("sector", "—")
        style = stock_info.get("style", "—")
        themes = stock_info.get("themes", [])
        tags_str = ", ".join(themes[:3]) + ("..." if len(themes) > 3 else "") if themes else "—"

        # Portfolio calculations
        pos = pos_lookup.get(ticker, {"shares": 0, "avg_cost": 0})
        shares = pos["shares"]
        avg_cost = pos["avg_cost"]
        price = enhanced.get("price") if not enhanced.get("error", True) else None

        if shares == 0:
            zero_shares_tickers.append(ticker)

        market_value = shares * price if price and shares > 0 else 0.0
        unrealized_pl = (price - avg_cost) * shares if price and shares > 0 and avg_cost > 0 else 0.0
        pl_pct = ((price - avg_cost) / avg_cost * 100) if price and avg_cost > 0 and shares > 0 else 0.0

        if not enhanced.get("error", True):
            rows.append({
                "Ticker": ticker,
                "Company": company,
                "Price": price,
                "Price Δ%": enhanced["price_change_pct"],
                "Day Δ%": enhanced["day_change_pct"],
                "Gap%": enhanced["gap_pct"],
                "Volume": enhanced["volume"],
                "Signal": signal_str,
                "Shares": shares,
                "Avg Cost": avg_cost,
                "Market Value": market_value,
                "P&L ($)": unrealized_pl,
                "P&L (%)": pl_pct,
                "Sector": sector,
                "Style": style,
                "Tags": tags_str,
            })
        else:
            rows.append({
                "Ticker": ticker,
                "Company": company,
                "Price": None,
                "Price Δ%": None,
                "Day Δ%": None,
                "Gap%": None,
                "Volume": None,
                "Signal": signal_str,
                "Shares": shares,
                "Avg Cost": avg_cost,
                "Market Value": market_value,
                "P&L ($)": unrealized_pl,
                "P&L (%)": pl_pct,
                "Sector": sector,
                "Style": style,
                "Tags": tags_str,
            })

    if not rows:
        st.info("No stocks to display.")
        return

    df_table = pd.DataFrame(rows)

    # Calculate weight %
    total_mv = df_table["Market Value"].sum()
    if total_mv > 0:
        df_table["Weight %"] = (df_table["Market Value"] / total_mv * 100).round(2)
    else:
        df_table["Weight %"] = 0.0

    # Show warning for zero shares
    if zero_shares_tickers:
        st.warning(f"⚠️ Missing position data for {len(zero_shares_tickers)} stock(s): {', '.join(zero_shares_tickers)}. Set shares in 'Manage Holdings & Watchlist' above.")

    # Display table
    def color_pct(val):
        if val is None or pd.isna(val):
            return ""
        if val > 0:
            return "color: #00ff88"
        elif val < 0:
            return "color: #ff4444"
        return "color: #aaaaaa"

    styled = df_table.style.format({
        "Price": lambda x: f"${x:.2f}" if pd.notna(x) else "N/A",
        "Price Δ%": lambda x: f"{x:+.2f}%" if pd.notna(x) else "N/A",
        "Day Δ%": lambda x: f"{x:+.2f}%" if pd.notna(x) else "N/A",
        "Gap%": lambda x: f"{x:+.2f}%" if pd.notna(x) else "N/A",
        "Volume": lambda x: format_volume(x) if pd.notna(x) else "N/A",
        "Shares": lambda x: f"{x:.0f}" if pd.notna(x) else "0",
        "Avg Cost": lambda x: f"${x:.2f}" if pd.notna(x) else "N/A",
        "Market Value": lambda x: f"${x:,.0f}" if pd.notna(x) else "$0",
        "P&L ($)": lambda x: f"${x:,.0f}" if pd.notna(x) else "$0",
        "P&L (%)": lambda x: f"{x:+.2f}%" if pd.notna(x) else "N/A",
        "Weight %": lambda x: f"{x:.1f}%" if pd.notna(x) else "0%",
    }).map(color_pct, subset=["Price Δ%", "Day Δ%", "Gap%", "P&L (%)"])

    st.dataframe(styled, use_container_width=True, height=400)

    # ── Portfolio Breakdown ──
    st.markdown("---")
    st.subheader("📊 Portfolio Breakdown")

    # Filter rows with non-zero market value for breakdown charts
    df_weighted = df_table[df_table["Market Value"] > 0].copy()

    if not df_weighted.empty:
        col_a, col_b = st.columns(2)

        with col_a:
            # Sector Allocation
            st.markdown("**Sector Allocation**")
            sector_alloc = df_weighted.groupby("Sector")["Weight %"].sum().sort_values(ascending=True)
            fig_sector = go.Figure(go.Bar(
                y=sector_alloc.index.tolist(),
                x=sector_alloc.values.tolist(),
                orientation="h",
                marker_color="#2196F3",
                text=[f"{v:.1f}%" for v in sector_alloc.values],
                textposition="outside",
            ))
            fig_sector.update_layout(
                template="plotly_dark", height=350,
                margin=dict(l=20, r=80, t=30, b=20),
                xaxis_title="Weight %",
            )
            st.plotly_chart(fig_sector, use_container_width=True, key="tab1_sector_alloc")

        with col_b:
            # Style Allocation
            st.markdown("**Style Allocation**")
            style_alloc = df_weighted.groupby("Style")["Weight %"].sum().sort_values(ascending=True)
            fig_style = go.Figure(go.Bar(
                y=style_alloc.index.tolist(),
                x=style_alloc.values.tolist(),
                orientation="h",
                marker_color="#FF9800",
                text=[f"{v:.1f}%" for v in style_alloc.values],
                textposition="outside",
            ))
            fig_style.update_layout(
                template="plotly_dark", height=350,
                margin=dict(l=20, r=80, t=30, b=20),
                xaxis_title="Weight %",
            )
            st.plotly_chart(fig_style, use_container_width=True, key="tab1_style_alloc")

        # Top Tags
        st.markdown("**Top 15 Tags**")
        col_t1, col_t2 = st.columns(2)

        # By portfolio weight
        tag_weight = {}
        tag_count = {}
        for _, row in df_weighted.iterrows():
            ticker = row["Ticker"]
            weight = row["Weight %"]
            themes = lookup.get(ticker, {}).get("themes", [])
            for theme in themes:
                tag_weight[theme] = tag_weight.get(theme, 0) + weight
                tag_count[theme] = tag_count.get(theme, 0) + 1

        with col_t1:
            st.markdown("*By Portfolio Weight*")
            top_tags_weight = sorted(tag_weight.items(), key=lambda x: x[1], reverse=True)[:15]
            if top_tags_weight:
                tag_names = [t[0] for t in top_tags_weight]
                tag_vals = [t[1] for t in top_tags_weight]
                fig_tag_w = go.Figure(go.Bar(
                    y=tag_names[::-1],
                    x=tag_vals[::-1],
                    orientation="h",
                    marker_color="#00ff88",
                    text=[f"{v:.1f}%" for v in tag_vals[::-1]],
                    textposition="outside",
                ))
                fig_tag_w.update_layout(
                    template="plotly_dark", height=400,
                    margin=dict(l=20, r=80, t=30, b=20),
                )
                st.plotly_chart(fig_tag_w, use_container_width=True, key="tab1_tags_weight")

        with col_t2:
            st.markdown("*By Count of Stocks*")
            top_tags_count = sorted(tag_count.items(), key=lambda x: x[1], reverse=True)[:15]
            if top_tags_count:
                tag_names_c = [t[0] for t in top_tags_count]
                tag_vals_c = [t[1] for t in top_tags_count]
                fig_tag_c = go.Figure(go.Bar(
                    y=tag_names_c[::-1],
                    x=tag_vals_c[::-1],
                    orientation="h",
                    marker_color="#E0B0FF",
                    text=[str(v) for v in tag_vals_c[::-1]],
                    textposition="outside",
                ))
                fig_tag_c.update_layout(
                    template="plotly_dark", height=400,
                    margin=dict(l=20, r=80, t=30, b=20),
                )
                st.plotly_chart(fig_tag_c, use_container_width=True, key="tab1_tags_count")
    else:
        st.info("ℹ️ No positions with market value to show breakdown. Set shares in 'Manage Holdings & Watchlist'.")

    # ── Performance Attribution ──
    st.markdown("---")
    st.subheader("📈 Performance Attribution")

    group_by = st.radio("Group by:", ["Sector", "Style", "Tag"], horizontal=True, key="tab1_group_by")

    if not df_weighted.empty:
        if group_by == "Sector":
            group_col = "Sector"
        elif group_by == "Style":
            group_col = "Style"
        else:
            group_col = None  # Tag needs special handling

        if group_col:
            grouped = df_weighted.groupby(group_col).agg(
                Weight=("Weight %", "sum"),
                Total_PL=("P&L ($)", "sum"),
                Count=("Ticker", "count"),
            ).reset_index()

            # Calculate P&L %, Win Rate, Best/Worst
            attr_rows = []
            for _, g in grouped.iterrows():
                cat_tickers = df_weighted[df_weighted[group_col] == g[group_col]]
                total_cost = sum(
                    pos_lookup.get(t, {"shares": 0, "avg_cost": 0})["shares"] *
                    pos_lookup.get(t, {"shares": 0, "avg_cost": 0})["avg_cost"]
                    for t in cat_tickers["Ticker"]
                )
                pl_pct_cat = (g["Total_PL"] / total_cost * 100) if total_cost > 0 else 0.0
                winners = cat_tickers[cat_tickers["P&L (%)"] > 0]["Ticker"].count()
                win_rate = (winners / g["Count"] * 100) if g["Count"] > 0 else 0.0
                best = cat_tickers.loc[cat_tickers["P&L (%)"].idxmax(), "Ticker"] if g["Count"] > 0 else "—"
                worst = cat_tickers.loc[cat_tickers["P&L (%)"].idxmin(), "Ticker"] if g["Count"] > 0 else "—"

                attr_rows.append({
                    "Category": g[group_col],
                    "Weight %": g["Weight"],
                    "Total P&L": g["Total_PL"],
                    "P&L %": pl_pct_cat,
                    "Win Rate": win_rate,
                    "# Stocks": g["Count"],
                    "Best": best,
                    "Worst": worst,
                })

            attr_df = pd.DataFrame(attr_rows).sort_values("Weight %", ascending=False)
            st.dataframe(
                attr_df.style.format({
                    "Weight %": lambda x: f"{x:.1f}%",
                    "Total P&L": lambda x: f"${x:,.0f}",
                    "P&L %": lambda x: f"{x:+.2f}%",
                    "Win Rate": lambda x: f"{x:.0f}%",
                }),
                use_container_width=True,
                hide_index=True,
            )
        else:
            # Group by Tag
            tag_attr = {}
            for _, row in df_weighted.iterrows():
                ticker = row["Ticker"]
                weight = row["Weight %"]
                pl = row["P&L ($)"]
                pl_pct = row["P&L (%)"]
                themes = lookup.get(ticker, {}).get("themes", [])
                for theme in themes:
                    if theme not in tag_attr:
                        tag_attr[theme] = {"weight": 0, "pl": 0, "pl_pcts": [], "tickers": []}
                    tag_attr[theme]["weight"] += weight
                    tag_attr[theme]["pl"] += pl
                    tag_attr[theme]["pl_pcts"].append(pl_pct)
                    tag_attr[theme]["tickers"].append(ticker)

            tag_rows = []
            for tag_name, data in tag_attr.items():
                count = len(data["tickers"])
                winners = sum(1 for p in data["pl_pcts"] if p > 0)
                win_rate = (winners / count * 100) if count > 0 else 0
                best_idx = max(range(len(data["pl_pcts"])), key=lambda i: data["pl_pcts"][i])
                worst_idx = min(range(len(data["pl_pcts"])), key=lambda i: data["pl_pcts"][i])
                tag_rows.append({
                    "Category": tag_name,
                    "Weight %": data["weight"],
                    "Total P&L": data["pl"],
                    "P&L %": sum(data["pl_pcts"]) / count if count > 0 else 0,
                    "Win Rate": win_rate,
                    "# Stocks": count,
                    "Best": data["tickers"][best_idx],
                    "Worst": data["tickers"][worst_idx],
                })

            tag_attr_df = pd.DataFrame(tag_rows).sort_values("Weight %", ascending=False).head(20)
            st.dataframe(
                tag_attr_df.style.format({
                    "Weight %": lambda x: f"{x:.1f}%",
                    "Total P&L": lambda x: f"${x:,.0f}",
                    "P&L %": lambda x: f"{x:+.2f}%",
                    "Win Rate": lambda x: f"{x:.0f}%",
                }),
                use_container_width=True,
                hide_index=True,
            )
    else:
        st.info("ℹ️ No positions with market value to show attribution.")

    # ── Price Chart + Quick Stats (Level 3) ──
    st.markdown("---")
    st.subheader("📈 Price Chart & Quick Stats")

    if scope_tickers:
        # Default to first ticker (or first holding if available)
        default_ticker = scope_tickers[0]
        selected_stock = st.selectbox(
            "Select a stock to view:",
            scope_tickers,
            index=0,
            key="tab1_chart_select",
        )

        col1, col2 = st.columns([3, 1])
        with col1:
            df_chart = get_stock_data(selected_stock, period="1y")
            if not df_chart.empty:
                df_chart = calculate_indicators(df_chart)
                chart = create_price_chart_with_overlays(df_chart, selected_stock)
                st.plotly_chart(chart, use_container_width=True, key="tab1_price_chart")
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
    else:
        st.warning("⚠️ No stocks available for chart. Adjust filters.")


# ─── TAB 2: Market Universe (NEW) ──────────────────────────────────────────
def render_market_universe(universe_tickers: list, classification_data: dict):
    """Render the Market Universe tab using full universe (Level 1 only)."""
    st.header("🌐 Market Universe")
    st.markdown("---")

    lookup = classification_data["lookup"]
    holdings, watchlist = get_dynamic_holdings_and_watchlist()

    if not universe_tickers:
        st.warning("⚠️ No stocks match the current Level 1 filters.")
        return

    # Collect daily price data for all universe tickers
    market_data = []
    for ticker in universe_tickers:
        price_data = get_current_price_data(ticker)
        stock_info = lookup.get(ticker, {})
        if not price_data["error"]:
            market_data.append({
                "Ticker": ticker,
                "Change %": price_data["change_pct"],
                "Sector": stock_info.get("sector", "Unknown"),
                "Style": stock_info.get("style", "Unknown"),
                "Themes": stock_info.get("themes", []),
            })
        else:
            market_data.append({
                "Ticker": ticker,
                "Change %": None,
                "Sector": stock_info.get("sector", "Unknown"),
                "Style": stock_info.get("style", "Unknown"),
                "Themes": stock_info.get("themes", []),
            })

    df_market = pd.DataFrame(market_data)
    df_valid = df_market.dropna(subset=["Change %"])

    if df_valid.empty:
        st.warning("⚠️ No valid market data available.")
        return

    # ── Market Breadth by Sector ──
    st.subheader("📊 Market Breadth by Sector")
    sector_stats = df_valid.groupby("Sector").agg(
        Avg_Change=("Change %", "mean"),
        Count=("Ticker", "count"),
    ).reset_index()
    pct_up_series = df_valid.groupby("Sector").apply(
        lambda x: (x["Change %"] > 0).sum() / len(x) * 100, include_groups=False
    )
    sector_stats["Pct_Up"] = sector_stats["Sector"].map(pct_up_series)

    fig_breadth = go.Figure(go.Bar(
        x=sector_stats["Sector"],
        y=sector_stats["Avg_Change"],
        marker_color=["#00ff88" if v >= 0 else "#ff4444" for v in sector_stats["Avg_Change"]],
        text=[f"{v:+.2f}%\n({int(u)}% up, n={int(c)})" for v, u, c in zip(
            sector_stats["Avg_Change"], sector_stats["Pct_Up"], sector_stats["Count"])],
        textposition="outside",
    ))
    fig_breadth.update_layout(
        title="Avg Daily Change by Sector",
        yaxis_title="Avg Change %",
        template="plotly_dark",
        height=400,
        margin=dict(l=20, r=20, t=50, b=80),
    )
    st.plotly_chart(fig_breadth, use_container_width=True, key="tab2_sector_breadth")

    # ── Style Performance Today ──
    st.markdown("---")
    st.subheader("📈 Style Performance Today")
    style_stats = df_valid.groupby("Style")["Change %"].mean().sort_values(ascending=True)
    fig_style_perf = go.Figure(go.Bar(
        y=style_stats.index.tolist(),
        x=style_stats.values.tolist(),
        orientation="h",
        marker_color=["#00ff88" if v >= 0 else "#ff4444" for v in style_stats.values],
        text=[f"{v:+.2f}%" for v in style_stats.values],
        textposition="outside",
    ))
    fig_style_perf.update_layout(
        title="Avg Daily Return by Style",
        template="plotly_dark",
        height=350,
        margin=dict(l=20, r=80, t=50, b=20),
    )
    st.plotly_chart(fig_style_perf, use_container_width=True, key="tab2_style_perf")

    # ── Hot Tags Today ──
    st.markdown("---")
    st.subheader("🔥 Hot Tags Today")

    # Calculate avg daily return per tag (only tags with ≥3 stocks)
    tag_returns = {}
    for _, row in df_valid.iterrows():
        for theme in row["Themes"]:
            if theme not in tag_returns:
                tag_returns[theme] = []
            tag_returns[theme].append(row["Change %"])

    tag_avg = {}
    for tag, returns in tag_returns.items():
        if len(returns) >= 3:
            tag_avg[tag] = sum(returns) / len(returns)

    if tag_avg:
        sorted_tags = sorted(tag_avg.items(), key=lambda x: x[1], reverse=True)
        top_10 = sorted_tags[:10]
        bottom_10 = sorted_tags[-10:]

        col_hot, col_cold = st.columns(2)

        with col_hot:
            st.markdown("**🔝 Top 10 Tags (Best Performers)**")
            fig_hot = go.Figure(go.Bar(
                y=[t[0] for t in top_10][::-1],
                x=[t[1] for t in top_10][::-1],
                orientation="h",
                marker_color="#00ff88",
                text=[f"{t[1]:+.2f}%" for t in top_10][::-1],
                textposition="outside",
            ))
            fig_hot.update_layout(
                template="plotly_dark", height=350,
                margin=dict(l=20, r=80, t=30, b=20),
            )
            st.plotly_chart(fig_hot, use_container_width=True, key="tab2_hot_tags")

        with col_cold:
            st.markdown("**🔻 Bottom 10 Tags (Worst Performers)**")
            fig_cold = go.Figure(go.Bar(
                y=[t[0] for t in bottom_10],
                x=[t[1] for t in bottom_10],
                orientation="h",
                marker_color="#ff4444",
                text=[f"{t[1]:+.2f}%" for t in bottom_10],
                textposition="outside",
            ))
            fig_cold.update_layout(
                template="plotly_dark", height=350,
                margin=dict(l=20, r=80, t=30, b=20),
            )
            st.plotly_chart(fig_cold, use_container_width=True, key="tab2_cold_tags")
    else:
        st.info("ℹ️ Not enough data for hot tags (need ≥3 stocks per tag).")

    # ── Holdings vs Market Comparison ──
    st.markdown("---")
    st.subheader("⚖️ Holdings vs Market Comparison")

    # Holdings weight by sector (using portfolio weights)
    holdings_positions = load_holdings_data()
    pos_lookup = {}
    for _, row in holdings_positions.iterrows():
        pos_lookup[row["ticker"]] = {"shares": row["shares"], "avg_cost": row["avg_cost"]}

    # Calculate holdings MV by sector
    holdings_sectors = {}
    total_holdings_mv = 0
    for ticker in holdings:
        if ticker not in universe_tickers:
            continue
        pos = pos_lookup.get(ticker, {"shares": 0, "avg_cost": 0})
        if pos["shares"] == 0:
            continue
        price_data = get_current_price_data(ticker)
        if not price_data["error"]:
            mv = pos["shares"] * price_data["price"]
            sector = lookup.get(ticker, {}).get("sector", "Unknown")
            holdings_sectors[sector] = holdings_sectors.get(sector, 0) + mv
            total_holdings_mv += mv

    # Market universe count by sector
    market_sectors = df_valid.groupby("Sector")["Ticker"].count().to_dict()

    # Build comparison table
    all_sectors = sorted(set(list(holdings_sectors.keys()) + list(market_sectors.keys())))
    comp_rows = []
    for sector in all_sectors:
        h_weight = (holdings_sectors.get(sector, 0) / total_holdings_mv * 100) if total_holdings_mv > 0 else 0
        m_count = market_sectors.get(sector, 0)
        m_pct = (m_count / len(df_valid) * 100) if len(df_valid) > 0 else 0
        diff = h_weight - m_pct
        signal = "Overweight" if diff > 2 else ("Underweight" if diff < -2 else "Neutral")
        comp_rows.append({
            "Sector": sector,
            "Holdings Wt %": h_weight,
            "Market Count": m_count,
            "Market %": m_pct,
            "Diff": diff,
            "Signal": signal,
        })

    comp_df = pd.DataFrame(comp_rows).sort_values("Holdings Wt %", ascending=False)
    st.dataframe(
        comp_df.style.format({
            "Holdings Wt %": lambda x: f"{x:.1f}%",
            "Market %": lambda x: f"{x:.1f}%",
            "Diff": lambda x: f"{x:+.1f}%",
        }),
        use_container_width=True,
        hide_index=True,
    )


# ─── TAB 3: Daily Report ───────────────────────────────────────────────────
def render_daily_report(universe_tickers: list, classification_data: dict):
    """Render the Daily Report tab with its own Level 2 scope."""
    st.header("📅 Daily Report")
    st.markdown("---")

    lookup = classification_data["lookup"]
    holdings, watchlist = get_dynamic_holdings_and_watchlist()

    # ── Level 2: Scope Selector ──
    scope_choice = st.radio(
        "Scope:",
        options=["Holdings", "Watchlist", "Full Universe"],
        horizontal=True,
        key="tab3_scope",
    )

    # Apply Level 2 scope
    if scope_choice == "Holdings":
        scope_tickers = [t for t in holdings if t in universe_tickers]
    elif scope_choice == "Watchlist":
        scope_tickers = [t for t in watchlist if t in universe_tickers]
    else:  # Full Universe
        scope_tickers = universe_tickers

    if not scope_tickers:
        st.warning("⚠️ No stocks match the current filters.")
        return

    st.subheader("📊 Today's Performance")

    # Performance cards in columns
    num_cols = min(len(scope_tickers), 6)
    rows_needed = (len(scope_tickers) + num_cols - 1) // num_cols

    for row_idx in range(rows_needed):
        start = row_idx * num_cols
        end = min(start + num_cols, len(scope_tickers))
        row_tickers = scope_tickers[start:end]
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
    news_ticker = st.selectbox("Select a stock for news:", scope_tickers, key="tab3_news_select")

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
    for ticker in scope_tickers:
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
        st.plotly_chart(fig, use_container_width=True, key="tab3_daily_change_chart")


# ─── TAB 4: Technical Analysis ─────────────────────────────────────────────
def render_technical_analysis(universe_tickers: list, classification_data: dict):
    """Render the Technical Analysis tab with Level 3 + Show All toggle."""
    st.header("📈 Technical Analysis")
    st.markdown("---")

    lookup = classification_data["lookup"]
    all_tickers = classification_data["all_tickers"]

    # ── Show All Tickers toggle ──
    show_all = st.toggle("Show All Tickers (ignore Level 1/2 filters)", value=False, key="tab4_show_all")

    if show_all:
        available_tickers = all_tickers
    else:
        available_tickers = universe_tickers

    if not available_tickers:
        st.warning("⚠️ No stocks available for analysis. Adjust filters or enable 'Show All Tickers'.")
        return

    # ── Level 3: Chart Ticker Selector ──
    selected = st.selectbox("🔍 Select stock for analysis:", available_tickers, key="tab4_ta_select")

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
    st.plotly_chart(price_chart, use_container_width=True, key="tab4_price_chart")

    # MACD chart
    st.markdown("---")
    st.subheader("📉 MACD")
    macd_chart = create_macd_chart(df, selected)
    st.plotly_chart(macd_chart, use_container_width=True, key="tab4_macd_chart")

    # Stochastic chart
    st.markdown("---")
    st.subheader("📈 Stochastic Oscillator")
    stoch_chart = create_stochastic_chart(df, selected)
    st.plotly_chart(stoch_chart, use_container_width=True, key="tab4_stoch_chart")

    # Volume chart
    st.markdown("---")
    vol_chart = create_volume_chart(selected)
    if vol_chart:
        st.plotly_chart(vol_chart, use_container_width=True, key="tab4_volume_chart")

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


# ─── Main App ──────────────────────────────────────────────────────────────
def main():
    st.markdown("# 📊 Stock Portfolio Dashboard")
    st.caption("🕐 Data refreshes every 5 minutes | Powered by Yahoo Finance")
    st.markdown("---")

    # Load classification data
    classification_data = load_classification_data()

    # ── Level 1: Universe Filter (shared across all tabs) ──
    st.subheader("🔍 Universe Filter")
    col1, col2, col3 = st.columns([1, 1, 2])

    with col1:
        sector_options = ["All"] + classification_data["sectors"]
        sector_filter = st.selectbox(
            "Sector:",
            options=sector_options,
            key="sector_filter",
        )

    with col2:
        style_options = ["All"] + classification_data["styles"]
        style_filter = st.selectbox(
            "Style:",
            options=style_options,
            key="style_filter",
        )

    with col3:
        theme_filter = st.multiselect(
            "Theme Tags:",
            options=classification_data["themes"],
            key="theme_filter",
            placeholder="Select themes...",
        )

    # Apply Level 1 filter to full universe
    universe_tickers = apply_universe_filter(
        classification_data["all_tickers"],
        sector_filter, style_filter, theme_filter, classification_data
    )

    st.markdown(f"**Universe: {len(universe_tickers)} stocks** (after Level 1 filter)")

    # Tabs
    tabs = st.tabs([
        "💼 Portfolio Overview",
        "🌐 Market Universe",
        "📅 Daily Report",
        "📈 Technical Analysis",
    ])

    with tabs[0]:
        render_portfolio_overview(universe_tickers, classification_data)

    with tabs[1]:
        render_market_universe(universe_tickers, classification_data)

    with tabs[2]:
        render_daily_report(universe_tickers, classification_data)

    with tabs[3]:
        render_technical_analysis(universe_tickers, classification_data)

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

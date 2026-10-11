# 📊 Stock Portfolio Dashboard — Developer Guide

> **Purpose:** This document enables any AI agent (or human developer) to understand, maintain, and extend this project without needing prior context. Read this file first before making any changes.

---

## 1. Project Overview

A **personal stock portfolio dashboard** built with **Streamlit**, deployed on **Streamlit Cloud** (free tier). It tracks US equity holdings and a watchlist, provides real-time market data via Yahoo Finance, calculates technical indicators, and generates buy/sell/hold signals.

**Live URL:** https://dav-stock-dashboard.streamlit.app

### Key Characteristics
- **Single user** — personal dashboard, no auth needed
- **Free data** — Yahoo Finance via `yfinance` (no paid APIs)
- **Free hosting** — Streamlit Cloud (auto-deploys on git push)
- **Dark theme** — `plotly_dark` template, custom CSS
- **Responsive** — works on desktop and mobile browsers

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────┐
│                   Streamlit Cloud                     │
│  ┌─────────────────────────────────────────────────┐ │
│  │                  app.py (Main)                   │ │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────────────┐ │ │
│  │  │ config.py│ │ data.py  │ │ indicators.py    │ │ │
│  │  │(constants)│ │(yfinance)│ │(ta lib + signals)│ │ │
│  │  └──────────┘ └──────────┘ └──────────────────┘ │ │
│  │                                                   │ │
│  │  ┌──────────────────────────────────────────────┐ │ │
│  │  │ data/                                        │ │ │
│  │  │  ├── sp100.yaml    (105 stocks classification)│ │ │
│  │  │  └── holdings.csv  (user positions, runtime) │ │ │
│  │  └──────────────────────────────────────────────┘ │ │
│  └─────────────────────────────────────────────────┘ │
│                                                       │
│  ┌─────────────────────┐  ┌────────────────────────┐ │
│  │ .streamlit/config.toml│  │ requirements.txt     │ │
│  │  (dark theme config) │  │ (6 dependencies)     │ │
│  └─────────────────────┘  └────────────────────────┘ │
└─────────────────────────────────────────────────────┘
```

### Data Flow
```
Yahoo Finance API → data.py (@st.cache_data, TTL=300s) → indicators.py → app.py → Streamlit UI
```

---

## 3. File Structure

```
stock-dashboard/
├── app.py                  # Main Streamlit app (1572 lines)
├── config.py               # Constants & indicator parameters (52 lines)
├── data.py                 # Data fetching via yfinance (132 lines)
├── indicators.py           # Technical indicators & signal logic (461 lines)
├── requirements.txt        # Python dependencies
├── DEVELOPER_GUIDE.md      # This file
├── .streamlit/
│   └── config.toml         # Streamlit dark theme config
└── data/
    ├── sp100.yaml          # 105 stocks with GICS classification
    └── holdings.csv        # User positions (created at runtime by UI)
```

### File Responsibilities

| File | Role | Key Functions |
|------|------|---------------|
| `config.py` | All tunable constants | Indicator periods, thresholds, holdings list |
| `data.py` | Data layer | `get_stock_data()`, `get_stock_info()`, `get_stock_news()`, `get_enhanced_price_data()` |
| `indicators.py` | Analytics engine | `calculate_indicators()`, `generate_signal()`, `get_suggested_levels()`, `find_support_resistance()` |
| `app.py` | UI + business logic | 4 tab renderers, filter system, chart builders |
| `data/sp100.yaml` | Stock universe | 105 stocks with sector, style, themes |
| `data/holdings.csv` | User positions | ticker, shares, avg_cost, is_holding, is_watchlist |

---

## 4. Dependencies

```
streamlit>=1.28.0    # Web framework
yfinance>=0.2.31     # Yahoo Finance data
pandas>=2.0.0        # Data manipulation
plotly>=5.18.0       # Interactive charts
ta>=0.11.0           # Technical analysis (pure Python, no numba/llvmlite)
pyyaml>=6.0          # YAML parsing for sp100.yaml
```

**Important:** The `ta` library is used because it's pure Python. Do NOT switch to `pandas-ta` or `TA-Lib` as those require C compilation which fails on Streamlit Cloud.

---

## 5. Stock Universe & Classification

### Source: `data/sp100.yaml`

Contains **105 stocks** (100 S&P 100 + 5 user additions):

| Extra Stock | Reason |
|-------------|--------|
| MRVL (Marvell) | User holding |
| NET (Cloudflare) | User watchlist |
| SMCI (Super Micro) | User watchlist |
| SKHY | User watchlist (may be delisted) |
| SPCX | User watchlist (may be delisted) |

### Classification Schema

Each stock has:
```yaml
- ticker: NVDA
  name: NVIDIA Corporation
  sector: Information Technology        # GICS sector (1 of 11)
  style: Mega-Cap Growth                # Market cap + growth/value blend
  themes:                               # 5-8 English tags
    - Semiconductors
    - AI Compute
    - Data Center
    - GPU
    - Autonomous Driving
    - Gaming
```

### GICS Sectors (11)
Communication Services, Consumer Discretionary, Consumer Staples, Energy, Financials, Health Care, Industrials, Information Technology, Materials, Real Estate, Utilities

### Styles
Mega-Cap Growth, Mega-Cap Blend, Large-Cap Growth, Large-Cap Blend, Large-Cap Value, Mid-Cap Growth, Mid-Cap Blend

---

## 6. Holdings Management

### Storage: `data/holdings.csv`

```csv
ticker,shares,avg_cost,is_holding,is_watchlist
NVDA,100.0,450.50,True,False
TSLA,50.0,180.00,True,False
AAPL,0.0,0.00,False,True
```

- **Created at runtime** by the Streamlit UI (⚙️ Manage Holdings & Watchlist expander)
- **Editable** via `st.data_editor` — user can add/remove rows
- **Loaded** by `load_holdings_data()` in `app.py`
- **Saved** by `save_holdings_data()` on button click
- **Default** falls back to `config.py` HOLDINGS/WATCHLIST lists if CSV doesn't exist
- **Warning:** `shares=0` means position data is missing; excluded from P&L and weight calculations

### Important: Streamlit Cloud Persistence
The CSV is written to the app's filesystem. On Streamlit Cloud free tier, **the container may be rebuilt**, which resets the CSV. The user should periodically commit updated holdings to git if they want persistence across restarts.

---

## 7. Filter System (3-Level)

The dashboard uses a **3-level filter hierarchy**:

```
Level 1: Universe Filter (shared across ALL tabs)
  ├── Sector dropdown (11 GICS sectors + "All")
  ├── Style dropdown (6 styles + "All")
  └── Theme Tags multiselect (free-form tags)

Level 2: Scope Selector (per-tab, independent)
  ├── Tab 1: Holdings Only / Watchlist Only / Holdings + Watchlist
  ├── Tab 2: N/A (always shows full universe)
  ├── Tab 3: Holdings / Watchlist / Full Universe
  └── Tab 4: Uses universe tickers (or "Show All" toggle)

Level 3: Chart Ticker Selector (per-tab, independent)
  ├── Tab 1: Price chart for selected stock
  └── Tab 4: Full technical analysis for selected stock
```

**Key Design Decisions:**
- Level 1 filters are **shared** (changing sector in Tab 1 affects Tab 2, 3, 4)
- Level 2 and Level 3 are **independent per tab** (selecting "Holdings" in Tab 1 doesn't affect Tab 3)
- Each tab has its own `key=` prefix to avoid Streamlit widget ID conflicts (e.g., `key="tab1_scope"`, `key="tab3_scope"`)

### Filter Functions

| Function | Purpose |
|----------|---------|
| `apply_universe_filter()` | Applies Sector + Style + Tags to full ticker list |
| `get_filtered_tickers()` | Legacy: combines portfolio filter + universe filter |
| `get_dynamic_holdings_and_watchlist()` | Reads holdings/watchlist from CSV |

---

## 8. Tab Structure

### Tab 1: 💼 Portfolio Overview
- **Level 2:** Scope selector (Holdings / Watchlist / Both)
- **Holdings Manager:** `st.data_editor` in expander for editing positions
- **Summary Table:** Price, Δ%, Signal, Shares, Market Value, P&L, Weight%
- **Portfolio Breakdown:** Sector allocation bar chart, Style allocation bar chart
- **Top Tags:** By portfolio weight and by count of stocks
- **Performance Attribution:** Group by Sector/Style/Tag → Weight, P&L, Win Rate, Best/Worst
- **Price Chart + Quick Stats:** Level 3 selector for individual stock view

### Tab 2: 🌐 Market Universe
- **No Level 2** — always shows full Level 1 filtered universe
- **Market Breadth by Sector:** Bar chart (avg daily change + % stocks up + count)
- **Style Performance Today:** Horizontal bar chart
- **Hot Tags:** Top 10 / Bottom 10 tags by avg daily return (min 3 stocks per tag)
- **Holdings vs Market:** Sector overweight/underweight comparison
- **Full Universe KPI Table:** 23-column comprehensive table (see Section 11)

### Tab 3: 📅 Daily Report
- **Level 2:** Holdings / Watchlist / Full Universe
- **Performance Cards:** Grid of metric cards showing price + change + volume
- **News Highlights:** Per-stock news (top 3 items from yfinance)
- **Daily Change Chart:** Bar chart of all stocks' daily % change

### Tab 4: 📈 Technical Analysis
- **"Show All" toggle:** Override filters to access any stock
- **Level 3:** Stock selector for deep analysis
- **Signal Explanation:** Color-coded list of 8 indicator votes
- **Indicator Cards:** All current values in metric cards
- **Charts:** Price+overlays, MACD, Stochastic, Volume
- **Suggested Levels:** Entry, Stop Loss (1.5x ATR), Target 1 (2x ATR), Target 2 (resistance)
- **Fibonacci Retracement:** 0.236, 0.382, 0.500, 0.618, 0.786 from recent swing high/low

---

## 9. Technical Indicators

### Parameters (all in `config.py`)

| Indicator | Parameter | Value |
|-----------|-----------|-------|
| RSI | Period | 14 |
| SMA | Short | 20 |
| SMA | Long | 50 |
| EMA | Period | 12 |
| MACD | Fast | 12 |
| MACD | Slow | 26 |
| MACD | Signal | 9 |
| Bollinger Bands | Period | 20 |
| Bollinger Bands | Std Dev | 2 |
| Stochastic | %K Period | 14 |
| Stochastic | %D Period | 3 |
| Stochastic | Smooth | 3 |
| ATR | Period | 14 |
| ADX | Period | 14 |
| S/R Lookback | Days | 60 |

### Indicator Calculation (`calculate_indicators()` in `indicators.py`)

Uses the `ta` library. All indicators are calculated on the full DataFrame and added as columns:

```python
RSI, SMA_20, SMA_50, EMA_12,
MACD_12_26_9, MACDs_12_26_9, MACDh_12_26_9,
BB_Upper, BB_Middle, BB_Lower,
Stoch_K, Stoch_D,
ATR,
ADX, DI_Plus, DI_Minus
```

### Support/Resistance (`find_support_resistance()`)

- Looks at last 60 days
- Finds pivot highs (resistance) and pivot lows (support)
- A pivot point = bar higher/lower than 2 bars on each side
- Returns top 3 closest to current price

---

## 10. Signal Logic (8-Vote System)

### How It Works

`generate_signal()` in `indicators.py` polls 8 technical indicators. Each votes:
- **+1** = bullish
- **-1** = bearish
- **0** = neutral (or **±0.5** for moderate signals)

| # | Indicator | Bullish Condition | Bearish Condition |
|---|-----------|-------------------|-------------------|
| 1 | RSI | < 30 (oversold) | > 70 (overbought) |
| 2 | SMA Cross | SMA20 > SMA50 | SMA20 < SMA50 |
| 3 | Price vs EMA12 | Price > EMA12 | Price < EMA12 |
| 4 | MACD Histogram | > 0 (positive) | < 0 (negative) |
| 5 | Bollinger Bands | Within 10% of lower band | Within 10% of upper band |
| 6 | Stochastic | %K < 20 AND crossing up | %K > 80 AND crossing down |
| 7 | ADX | ADX > 25 → follow price direction | ADX < 20 → neutral |
| 8 | S/R Proximity | Within 3% of support | Within 3% of resistance |

### Final Signal

```python
avg = sum(signals) / len(signals)

if avg >= 0.5:  → 🟢 BUY
if avg <= -0.5: → 🔴 SELL
else:           → ⏸️ HOLD
```

### Suggested Trade Levels (`get_suggested_levels()`)

| Level | Formula |
|-------|---------|
| Entry | 0.5% above nearest support (or current price) |
| Stop Loss | Entry - 1.5 × ATR |
| Target 1 | Entry + 2.0 × ATR |
| Target 2 | Nearest resistance (or Entry + 3.0 × ATR) |
| Risk/Reward | (Target1 - Entry) / (Entry - StopLoss) |

---

## 11. Full Universe KPI Table (Tab 2 — 23 Columns)

The comprehensive comparison table at the bottom of the Market Universe tab.

### Column Order & Meaning

| # | Column | Formula / Source | Color Coding |
|---|--------|-----------------|--------------|
| 1 | Ticker | Stock symbol | — |
| 2 | Company | Full name from YAML | — |
| 3 | Sector | GICS sector from YAML | — |
| 4 | Style | Cap size + growth/value from YAML | — |
| 5 | Price | Last close price | — |
| 6 | Price Δ% | (Today Close - Yesterday Close) / Yesterday Close × 100 | Green > 0, Red < 0 |
| 7 | Day Δ% | (Close - Open) / Open × 100 (intraday only) | Green > 0, Red < 0 |
| 8 | Gap% | (Today Open - Yesterday Close) / Yesterday Close × 100 (overnight) | Green > 0, Red < 0 |
| 9 | Volume | Today's traded shares (formatted K/M/B) | — |
| 10 | Avg Vol (3M) | 3-month average daily volume | — |
| 11 | Vol Ratio | Today Volume / Avg Vol 3M | Gold bold if > 1.5x |
| 12 | Signal | 8-vote system result (🟢/🔴/⏸️) | — |
| 13 | ADX(14) | Trend strength (0-100) | Gold bold if > 25 (strong) |
| 14 | RSI(14) | Relative Strength Index | Green bold < 30, Red bold > 70 |
| 15 | Stoch %K | Stochastic oscillator | — |
| 16 | MACD Hist | MACD histogram value | — |
| 17 | SMA(20) | 20-day simple moving average | — |
| 18 | SMA(50) | 50-day simple moving average | — |
| 19 | EMA(12) | 12-day exponential moving average | — |
| 20 | BB Width% | (BB_Upper - BB_Lower) / BB_Middle × 100 | Green highlight if < 5% (squeeze) |
| 21 | Week % | 5-trading-day return | Green > 0, Red < 0 |
| 22 | From 52W High% | (Current - 52W High) / 52W High × 100 (always ≤ 0) | Green > 0, Red < 0 |
| 23 | Tags | First 3 themes from YAML + "..." if more | — |

---

## 12. Caching Strategy

| Function | Cache | TTL | Notes |
|----------|-------|-----|-------|
| `get_stock_data()` | `@st.cache_data` | 300s (5 min) | Historical OHLCV |
| `get_stock_info()` | `@st.cache_data` | 300s | Stock metadata |
| `get_stock_news()` | `@st.cache_data` | 300s | Top 3 news items |
| `get_enhanced_price_data()` | `@st.cache_data` | 300s | Full price snapshot |
| `load_classification_data()` | `@st.cache_data` | No expiry | YAML file (static) |

**Important:** Changing filters does NOT re-fetch Yahoo Finance data (just Python list filtering). The 5-minute cache prevents API rate limiting.

---

## 13. Deployment

### Streamlit Cloud (Free Tier)
- **Repo:** https://github.com/dalittlegiant/stock-dashboard
- **URL:** https://dav-stock-dashboard.streamlit.app
- **Auto-deploy:** Pushes to `main` branch trigger automatic redeployment
- **Python version:** No `runtime.txt` pinned — uses Streamlit Cloud default
- **Rebuild:** If the app shows stale errors (ImportError, NameError), go to Streamlit Cloud dashboard and click "Reboot"

### Pushing Changes
```bash
cd /tmp/stock_dashboard
git add -A
git commit -m "description of changes"
git push origin main
```

The GitHub PAT is stored in the git remote URL. If it expires, the user needs to provide a new one.

---

## 14. Telegram Reporting (External System)

The user has **Hermes Agent cron jobs** that generate daily and weekly Telegram reports:
- **Daily:** Mon-Fri 21:30 UTC — today's changes, sector performance, news highlights
- **Weekly:** Fri 22:00 UTC — weekly performance, technical indicators, buy/sell signals

These reports are generated by Hermes Agent independently (not by this Streamlit app). They use the same stock universe and indicator logic described here.

---

## 15. User Preferences & Conventions

- **Language:** User speaks Cantonese (粵語). Communication should be in Cantonese/Traditional Chinese.
- **Color scheme:** Green (#00ff88) for bullish, Red (#ff4444) for bearish, Gold (#FFD700) for highlights
- **Chart style:** `plotly_dark` template, dark backgrounds
- **Volume bar colors:** Green = close > open (bullish day), Red = close < open (bearish day)
- **Number formatting:** Volumes as K/M/B, percentages with 2 decimal places, prices with 2 decimal places
- **Tables:** Use `st.dataframe()` with `hide_index=True`, pandas Styler for color coding
- **Widget keys:** Always use `key=` parameter with tab prefix (e.g., `key="tab1_chart_select"`) to avoid Streamlit duplicate ID errors

---

## 16. Common Pitfalls & Gotchas

### For AI Agents Working on This Project

1. **Do NOT use `numba` or `llvmlite`** — they fail to compile on Streamlit Cloud. Use the `ta` library (pure Python).

2. **Do NOT add `runtime.txt`** — previously caused build failures. Streamlit Cloud auto-selects a compatible Python version.

3. **Widget key conflicts** — Every `st.selectbox`, `st.radio`, `st.data_editor` etc. MUST have a unique `key=` parameter. Use tab prefixes: `tab1_`, `tab2_`, `tab3_`, `tab4_`.

4. **Streamlit Cloud caching** — If the deployed app shows old code (ImportError, NameError for removed functions), the user must manually "Reboot" the app from Streamlit Cloud dashboard.

5. **yfinance reliability** — Sometimes returns empty data or NaN for pre-market hours. The code handles this with `.dropna(subset=["Close"])` and error fallbacks.

6. **holdings.csv persistence** — On Streamlit Cloud free tier, the container can be rebuilt, losing the CSV. User data may need to be re-entered or committed to git.

7. **`ta` library API** — Column names follow `ta` library conventions: `MACD_12_26_9`, `MACDs_12_26_9`, `MACDh_12_26_9`. Don't rename these without updating all references.

8. **Filter independence** — Tab 1 and Tab 4 each have their own Level 3 stock selector. They must NOT be synced (user explicitly requested this).

9. **Adding new stocks** — Edit `data/sp100.yaml` and add ticker + name + sector + style + themes. The dashboard picks it up automatically.

10. **Performance** — The Full Universe KPI Table (Tab 2) fetches data for ALL stocks. With 105 stocks and caching, the first load can take 30-60 seconds. Subsequent loads (within 5 min) are instant from cache.

---

## 17. Extension Ideas (Not Yet Implemented)

- **Sector heatmap** — Treemap of sectors sized by market cap, colored by daily return
- **Correlation matrix** — Pairwise correlation between holdings
- **Backtesting** — Test signal logic against historical data
- **Alerts** — Notify when RSI crosses 30/70, or price hits S/R levels
- **Options data** — Implied volatility, put/call ratios
- **Fundamental data** — P/E, P/S, EPS growth, revenue growth
- **Multi-timeframe analysis** — Weekly/monthly charts alongside daily
- **Portfolio rebalancing** — Target allocation vs actual, with suggested trades

---

## 18. Git & Version Control

- **Repo:** https://github.com/dalittlegiant/stock-dashboard
- **Main branch:** `main`
- **Commit convention:** `feat:`, `fix:`, `refactor:`, `docs:`, `data:` prefixes
- **GitHub username:** dalittlegiant

### Making Changes Workflow
1. Edit files locally in `/tmp/stock_dashboard/`
2. `git add -A && git commit -m "feat: description"`
3. `git push origin main`
4. Streamlit Cloud auto-deploys (~2-3 minutes)
5. User refreshes the URL

---

## 19. Quick Reference: Function Index

### config.py
| Constant | Value | Purpose |
|----------|-------|---------|
| `CACHE_TTL` | 300 | yfinance cache seconds |
| `CHART_HISTORY_PERIOD` | "1y" | Default history length |
| `RSI_PERIOD` | 14 | RSI window |
| `SMA_SHORT` / `SMA_LONG` | 20 / 50 | SMA windows |
| `EMA_PERIOD` | 12 | EMA window |
| `MACD_FAST/SLOW/SIGNAL` | 12/26/9 | MACD parameters |
| `BB_PERIOD` / `BB_STD` | 20 / 2 | Bollinger Band parameters |
| `STOCH_K_PERIOD/D_PERIOD/SMOOTH` | 14/3/3 | Stochastic parameters |
| `ATR_PERIOD` | 14 | ATR window |
| `ADX_PERIOD` | 14 | ADX window |
| `ADX_STRONG` / `ADX_WEAK` | 25 / 20 | ADX thresholds |
| `SR_LOOKBACK` | 60 | Support/Resistance lookback days |

### data.py
| Function | Returns | Cached |
|----------|---------|--------|
| `get_stock_data(ticker, period)` | pd.DataFrame (OHLCV) | Yes (300s) |
| `get_stock_info(ticker)` | dict | Yes (300s) |
| `get_stock_news(ticker)` | list[dict] (top 3) | Yes (300s) |
| `get_current_price_data(ticker)` | dict (price, change_pct, volume) | No (calls cached fn) |
| `get_enhanced_price_data(ticker)` | dict (full price snapshot) | Yes (300s) |

### indicators.py
| Function | Returns |
|----------|---------|
| `calculate_indicators(df)` | pd.DataFrame with indicator columns |
| `generate_signal(df)` | tuple(str, list) — signal + explanations |
| `get_indicator_summary(df)` | dict of current values |
| `get_suggested_levels(df)` | dict with entry/SL/TP1/TP2/S/R |
| `find_support_resistance(df)` | dict with support[] and resistance[] |
| `calculate_fibonacci(df)` | dict with fib levels |

### app.py (Key Functions)
| Function | Purpose |
|----------|---------|
| `load_classification_data()` | Parse sp100.yaml → lookup dict |
| `load_holdings_data()` | Read CSV or create default |
| `save_holdings_data(df)` | Write CSV |
| `get_dynamic_holdings_and_watchlist()` | Current holdings/watchlist from CSV |
| `apply_universe_filter()` | Filter tickers by sector/style/tags |
| `render_portfolio_overview()` | Tab 1 |
| `render_market_universe()` | Tab 2 |
| `render_daily_report()` | Tab 3 |
| `render_technical_analysis()` | Tab 4 |
| `create_price_chart_with_overlays()` | Candlestick + BB + SMA/EMA |
| `create_macd_chart()` | MACD line + signal + histogram |
| `create_stochastic_chart()` | %K/%D with overbought/oversold |
| `create_volume_chart()` | 3-month volume bars |

---

*Last updated: October 2025*
*Maintained by: D K (via Hermes Agent)*

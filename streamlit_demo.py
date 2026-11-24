"""PUBLIC DEMO ONLY: synthetic data, no Yahoo Finance, no PSE files.

Run: python -m streamlit run streamlit_demo.py
For locally researched real-data stocks, keep using streamlit_app.py privately.
"""

import altair as alt
import pandas as pd
import streamlit as st

from data_quality import assess_metric_coverage
from demo_data import create_demo_history
from performance import calculate_price_return
from portfolio_dashboard import render_portfolio_dashboard
from risk_metrics import calculate_annualized_volatility, calculate_sharpe_ratio

st.set_page_config(page_title="Global Investor | Public demo", page_icon="📈", layout="wide")

st.title("Fenric Investment · Global Investor")
st.warning(
    "PUBLIC DEMO: All investment research prices are computer-generated fictional examples. "
    "They do not describe any real ticker, exchange, asset, price or expected return."
)
st.caption("Demonstration only · No live market data · No personal investment advice")

with st.sidebar:
    page = st.radio("Section", ["Fictional Investment Research", "Portfolio Dashboard", "About this demo"])
    st.caption("Actual US/PSE market data is NOT displayed in this public demo.")

if page == "About this demo":
    st.header("Demo scope and limitations")
    st.write(
        "This public demonstration is powered by Global Investor's financial calculation modules "
        "and a synthetic weekday OHLCV dataset. It has no connection to Yahoo Finance, the PSE, "
        "a brokerage, or a trading system. It demonstrates functionality, NOT actual research."
    )
    st.write(
        "Portfolio holdings, prices and PHP/USD FX rates are entered manually. They can be "
        "downloaded as CSV or JSON and uploaded later. Uploads are processed by this remote "
        "Streamlit server in memory, so do not enter or upload sensitive real holdings for testing. "
        "No permanent user accounts or server-side saved portfolios exist."
    )
    st.write("Performance and risk statistics are not forecasts or investment recommendations.")
    st.stop()

if page == "Portfolio Dashboard":
    st.info("Use fictional holdings only. This beta has no authentication and no persistent account storage.")
    render_portfolio_dashboard()
    st.stop()

history = create_demo_history()
coverage = assess_metric_coverage(history)

st.header("DEMO-ONLY · Fictional asset research")
st.caption(
    f"Synthetic observations: {len(history)} weekdays, {history.index[0].date()} "
    f"to {history.index[-1].date()} · Generated test prices, NOT market quotations"
)
left, right = st.columns(2)
left.metric("Latest simulated close", f"${history['Close'].iloc[-1]:,.2f}")
right.metric("Synthetic historical records", f"{len(history):,}")

st.subheader("Simulated price history")
plot = history[["Close"]].tail(252).reset_index()
plot["Date"] = pd.to_datetime(plot["Date"])
low, high = float(plot["Close"].min()), float(plot["Close"].max())
pad = max(0.5, (high - low) * 0.07)
chart = (
    alt.Chart(plot)
    .mark_line(strokeWidth=2)
    .encode(
        x=alt.X("Date:T", title="Synthetic weekday", scale=alt.Scale(nice=False)),
        y=alt.Y("Close:Q", title="Simulated price", scale=alt.Scale(domain=[max(0, low-pad), high+pad], zero=False)),
        tooltip=[alt.Tooltip("Date:T"), alt.Tooltip("Close:Q", format=",.2f")],
    )
    .properties(height=300)
)
st.altair_chart(chart, width="stretch")

st.subheader("Synthetic historical returns")
rows = []
for label, months in (("1 Month", 1), ("6 Months", 6), ("1 Year", 12)):
    coverage_label = {1: "1 Month Return", 6: "6 Month Return", 12: "1 Year Return"}[months]
    if not coverage[coverage_label]["available"]:
        rows.append({"Period": label, "Simulated price return": "Insufficient data", "Simulated adjusted return": "Insufficient data"})
        continue
    raw = calculate_price_return(history, months)
    adj = calculate_price_return(history, months, price_column="Adj Close")
    rows.append({
        "Period": label,
        "Simulated price return": f"{raw['return_pct']:+.2f}%",
        "Simulated adjusted return": f"{adj['return_pct']:+.2f}%",
    })
st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")

st.subheader("Historical risk calculations — synthetic inputs")
first, second = st.columns(2)
try:
    vol = calculate_annualized_volatility(history)
    first.metric("90-day annualized volatility (demo)", f"{vol['volatility_pct']:.2f}%")
except ValueError as err:
    first.warning(f"Volatility unavailable: {err}")
try:
    sharpe = calculate_sharpe_ratio(history, risk_free_rate_pct=4.0)
    second.metric("1-year Sharpe ratio (demo)", f"{sharpe['sharpe_ratio']:.4f}")
except ValueError as err:
    second.warning(f"Sharpe ratio unavailable: {err}")
st.caption("Sharpe demo assumes a fixed 4% effective annual risk-free rate, not a verified market rate.")
st.info("All values on this research page are fictional. Do not make investment decisions using this demonstration.")

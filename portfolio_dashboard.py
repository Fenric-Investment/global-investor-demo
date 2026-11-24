"""Streamlit portfolio beta: manually entered prices and user-supplied FX assumption."""

import altair as alt
import pandas as pd
import streamlit as st

from portfolio_valuation import calculate_portfolio
from portfolio_io import export_csv, export_snapshot, import_portfolio_file


DEMO_HOLDINGS = [
    {"name": "DEMO-US", "shares": 3.0, "buy_price": 100.0, "current_price": 115.0, "currency": "USD"},
    {"name": "DEMO-PH", "shares": 15.0, "buy_price": 80.0, "current_price": 85.0, "currency": "PHP"},
]


def render_portfolio_dashboard():
    st.header("Portfolio dashboard · PHP/USD beta")
    st.caption("Manual holdings and FX assumptions · No live portfolio quotes or brokerage connection")
    st.warning(
        "The initial sample holdings are fictional. All holdings and current prices are manual; "
        "they are not written to portfolio.csv or sent to a market-data provider."
    )
    st.write("Edit your holdings below. Add or delete rows using the table controls.")

    # Session-only state. No shared file or database writes.
    if "sprint3_holdings" not in st.session_state:
        st.session_state["sprint3_holdings"] = pd.DataFrame(DEMO_HOLDINGS)
    if "sprint3_editor_version" not in st.session_state:
        st.session_state["sprint3_editor_version"] = 0
    if "sprint3_base" not in st.session_state:
        st.session_state["sprint3_base"] = "PHP"
    if "sprint3_fx" not in st.session_state:
        st.session_state["sprint3_fx"] = 58.0

    with st.expander("Load a saved portfolio (CSV or JSON)"):
        st.caption(
            "Import a file you previously downloaded. CSV restores holdings only; "
            "a Global Investor JSON snapshot also restores reporting currency and assumed FX. "
            "Uploaded files are processed by this Streamlit server in memory; "
            "the beta does not write them to a shared database or to portfolio.csv."
        )
        incoming = st.file_uploader(
            "Select portfolio file", type=["csv", "json"], key="sprint3_file_upload"
        )
        if st.button("Load selected file", disabled=incoming is None):
            try:
                loaded = import_portfolio_file(incoming.getvalue(), incoming.name)
            except ValueError as error:
                st.error(f"Import failed: {error}")
            else:
                st.session_state["sprint3_holdings"] = pd.DataFrame(loaded["holdings"])
                if loaded["base_currency"] is not None:
                    st.session_state["sprint3_base"] = loaded["base_currency"]
                    st.session_state["sprint3_fx"] = loaded["php_per_usd"]
                st.session_state["sprint3_editor_version"] += 1
                st.session_state["sprint3_flash"] = "Portfolio loaded into this browser session."
                st.rerun()

    if message := st.session_state.pop("sprint3_flash", None):
        st.success(message)

    holdings_df = st.data_editor(
        st.session_state["sprint3_holdings"],
        num_rows="dynamic",
        hide_index=True,
        width="stretch",
        key=f"sprint3_holdings_editor_{st.session_state['sprint3_editor_version']}",
        column_config={
            "name": st.column_config.TextColumn("Ticker / Holding", required=True),
            "shares": st.column_config.NumberColumn("Shares", min_value=0.000001, step=1.0, required=True),
            "buy_price": st.column_config.NumberColumn("Average buy price", min_value=0.01, format="%.4f", required=True),
            "current_price": st.column_config.NumberColumn("Current price (manual)", min_value=0.0, format="%.4f", required=True),
            "currency": st.column_config.SelectboxColumn(
                "Price currency", options=["USD", "PHP"], required=True
            ),
        },
    )

    # Capture edited rows for subsequent reruns and local-file exports.
    st.session_state["sprint3_holdings"] = holdings_df.copy()

    c1, c2 = st.columns(2)
    with c1:
        base = st.selectbox("Portfolio reporting currency", ["PHP", "USD"], key="sprint3_base")
    with c2:
        fx = st.number_input(
            "Assumed PHP per 1 USD (manual rate)",
            min_value=0.000001, step=0.25, format="%.4f", key="sprint3_fx",
            help="Illustrative starting value only. Enter a rate you have verified independently.",
        )

    st.subheader("Save a copy of your portfolio")
    st.caption(
        "Downloads belong to you. CSV stores holdings only; JSON also stores the reporting "
        "currency and manual FX assumption. Neither option sends portfolio data to a brokerage."
    )
    try:
        editable_rows = holdings_df.to_dict("records")
        csv_bytes = export_csv(editable_rows)
        json_bytes = export_snapshot(editable_rows, base, fx)
    except ValueError as error:
        st.warning(f"Fix the holdings before exporting: {error}")
    else:
        download_csv, download_json = st.columns(2)
        with download_csv:
            st.download_button(
                "Download holdings CSV", data=csv_bytes,
                file_name="global_investor_holdings.csv", mime="text/csv",
            )
        with download_json:
            st.download_button(
                "Download full portfolio snapshot (JSON)", data=json_bytes,
                file_name="global_investor_portfolio.json", mime="application/json",
            )

    st.caption(
        "P&L compares holding prices at the **same selected FX rate**, so it does not "
        "measure gains or losses from currency movements between purchase and today. "
        "Dividends, fees, taxes and transaction timing are also excluded."
    )
    if not st.button("Calculate portfolio", type="primary"):
        return

    try:
        data = calculate_portfolio(holdings_df.to_dict("records"), base, fx)
    except ValueError as error:
        st.error(f"Portfolio input issue: {error}")
        return

    symbol = "₱" if base == "PHP" else "$"
    a, b, c, d = st.columns(4)
    a.metric(f"Invested ({base})", f"{symbol}{data['invested']:,.2f}")
    b.metric(f"Current value ({base})", f"{symbol}{data['value']:,.2f}")
    c.metric(f"Price P&L ({base})", f"{symbol}{data['pnl']:+,.2f}")
    d.metric("Holding-price return", f"{data['return_pct']:+.2f}%")

    st.subheader("Holdings and valuation")
    rows = []
    for h in data["holdings"]:
        rows.append({
            "Holding": h["name"], "Currency": h["currency"],
            "Shares": h["shares"],
            f"Invested ({base})": round(h["invested_base"], 2),
            f"Current value ({base})": round(h["current_value_base"], 2),
            f"Price P&L ({base})": round(h["pnl_base"], 2),
            "Return (%)": round(h["return_pct"], 2),
            "Allocation (%)": round(h["allocation_pct"], 2),
        })
    table = pd.DataFrame(rows)
    st.dataframe(table, hide_index=True, width="stretch")

    st.subheader("Portfolio allocation")
    allocation = table.groupby("Holding", as_index=False)[f"Current value ({base})"].sum()
    if data["value"] > 0:
        chart = (
            alt.Chart(allocation)
            .mark_bar()
            .encode(
                x=alt.X(f"Current value ({base}):Q", title=f"Value ({base})"),
                y=alt.Y("Holding:N", sort="-x", title="Holding"),
                tooltip=["Holding", alt.Tooltip(f"Current value ({base}):Q", format=",.2f")],
            )
            .properties(height=max(170, 50 * len(allocation)))
        )
        st.altair_chart(chart, width="stretch")
        st.caption(f"Largest individual position: {data['largest_allocation_pct']:.1f}% of portfolio value.")
    else:
        st.info("All holdings have zero current value. Allocation percentages are unavailable.")

    st.info(
        "Prototype valuation only. FX is an assumed single rate; prices are manually entered. "
        "The results are not brokerage statements, realized performance or investment advice."
    )

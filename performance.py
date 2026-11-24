
import numpy as np
import pandas as pd



def calculate_price_return(history, months, price_column="Close"):
    """Calculate a price return using calendar-aligned dates."""

    if months not in (1, 6, 12):
        raise ValueError("Supported periods: 1, 6, or 12 months.")

    if history is None or history.empty:
        raise ValueError("Historical data is unavailable.")

    if price_column not in ("Close", "Adj Close"):
        raise ValueError("Unsupported price column.")

    if price_column not in history.columns:
        raise ValueError(
            f"Missing {price_column} price column."
        )

    # Select the requested historical price series
    prices = pd.to_numeric(
        history[price_column], errors="coerce"
    ).copy()

    # Validate the selected prices
    if (
        prices.isna().any()
        or (prices <= 0).any()
        or not np.isfinite(prices.to_numpy()).all()
    ):
        raise ValueError("Invalid historical closing prices.")

    # Keep the existing date-processing code below

    dates = pd.DatetimeIndex(
        pd.to_datetime(history.index, errors="raise")
    )

    if dates.hasnans:
        raise ValueError("Invalid historical dates.")

    if dates.tz is not None:
        dates = dates.tz_localize(None)

    dates = dates.normalize()

    if dates.duplicated().any():
        raise ValueError("Duplicate trading dates detected.")

    prices.index = dates
    prices = prices.sort_index()

    end_date = prices.index[-1]
    target_date = end_date - pd.DateOffset(months=months)

    # Use the most recent observation on or before
    # the target calendar date.
    eligible = prices.loc[prices.index <= target_date]

    if eligible.empty:
        raise ValueError(
            "Insufficient history for the selected period."
        )

    start_date = eligible.index[-1]

    if (target_date - start_date).days > 7:
        raise ValueError(
            "No sufficiently close historical price "
            "for the target date."
        )

    start_price = float(eligible.iloc[-1])
    end_price = float(prices.iloc[-1])

    return_pct = (
        (end_price / start_price) - 1
    ) * 100

    return {
        "start_date": start_date.date(),
        "end_date": end_date.date(),
        "start_price": start_price,
        "end_price": end_price,
        "return_pct": return_pct,
        "price_field": price_column
    }


from datetime import date, timedelta
import pandas as pd


def assess_market_data(
    history,
    source="Unknown",
    data_type="Historical",
    as_of_date=None
):
    """Assess price-data freshness and historical coverage."""

    if history is None or history.empty:
        raise ValueError("No historical market data available.")

    dates = pd.to_datetime(history.index, errors="raise")

    if dates.hasnans:
        raise ValueError("Historical data contains invalid dates.")

    latest_date = dates.max().date()
    earliest_date = dates.min().date()

    today = as_of_date if as_of_date is not None else date.today()

    if not isinstance(today, date):
        raise ValueError("as_of_date must be a date object.")

    days_old = (today - latest_date).days
    record_count = len(history)

    warnings = []

    if days_old < 0:
        freshness = "Invalid future date"
        warnings.append(
            "Quotation date is in the future. Check the source."
        )

    elif days_old >= 5:
        freshness = "Potentially outdated"
        warnings.append(
            "Market data may be outdated. Check for newer quotations."
        )

    else:
        freshness = "Recently dated"

    if record_count < 20:
        warnings.append(
            "Insufficient records for reliable longer-term analysis."
        )

    return {
        "source": source,
        "data_type": data_type,
        "earliest_date": earliest_date,
        "latest_date": latest_date,
        "days_old": days_old,
        "record_count": record_count,
        "freshness": freshness,
        "warnings": warnings
    }


def assess_metric_coverage(history):
    """Assess historical coverage for each financial metric."""

    if history is None or history.empty:
        raise ValueError("No historical market data available.")

    dates = pd.to_datetime(history.index, errors="raise")

    if dates.hasnans or dates.duplicated().any():
        raise ValueError(
            "Historical data contains invalid or duplicate dates."
        )

    trading_dates = sorted(d.date() for d in dates)
    latest_date = trading_dates[-1]

    # Metric: (window days, minimum records, minimum span)
    requirements = {
        "1 Month Return": (30, 18, 24),
        "6 Month Return": (183, 100, 160),
        "1 Year Return": (365, 200, 330),
        "Annualized Volatility": (90, 61, 70),
        "Sharpe Ratio": (365, 201, 330)
    }

    # Provisional maximum gap between observations
    maximum_gap_days = 10

    results = {}

    for metric, (
        window_days,
        min_records,
        min_span
    ) in requirements.items():

        start_date = latest_date - timedelta(days=window_days)

        window_dates = [
            d for d in trading_dates
            if d >= start_date
        ]

        record_count = len(window_dates)

        if record_count >= 2:
            span_days = (
                window_dates[-1] - window_dates[0]
            ).days

            largest_gap = max(
                (current - previous).days
                for previous, current in zip(
                    window_dates,
                    window_dates[1:]
                )
            )
        else:
            span_days = 0
            largest_gap = 0

        available = (
            record_count >= min_records
            and span_days >= min_span
            and largest_gap <= maximum_gap_days
        )

        results[metric] = {
            "available": available,
            "records": record_count,
            "span_days": span_days,
            "required_records": min_records,
            "required_span_days": min_span,
            "largest_gap_days": largest_gap,
            "window_days": window_days
        }

    return results

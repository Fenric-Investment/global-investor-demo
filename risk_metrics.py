
import numpy as np
import pandas as pd

from data_quality import assess_metric_coverage


def calculate_annualized_volatility(history):
    """Calculate 90-day historical annualized volatility."""

    if history is None or history.empty:
        raise ValueError("Historical data is unavailable.")

    coverage = assess_metric_coverage(history)

    if not coverage["Annualized Volatility"]["available"]:
        raise ValueError(
            "Insufficient historical coverage for volatility."
        )

    # Prefer corporate-action-adjusted prices when available.
    price_column = (
        "Adj Close" if "Adj Close" in history.columns
        else "Close"
    )

    if price_column not in history.columns:
        raise ValueError("Missing closing price column.")

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

    prices = pd.to_numeric(
        history[price_column], errors="coerce"
    ).copy()

    prices.index = dates
    prices = prices.sort_index()

    end_date = prices.index[-1]
    start_date = end_date - pd.Timedelta(days=90)

    recent_prices = prices.loc[
        prices.index >= start_date
    ]

    if (
        recent_prices.isna().any()
        or (recent_prices <= 0).any()
        or not np.isfinite(recent_prices.to_numpy()).all()
    ):
        raise ValueError("Invalid historical prices.")

    daily_returns = recent_prices.pct_change().dropna()

    if len(daily_returns) < 2:
        raise ValueError("Insufficient daily returns.")

    volatility = (
        daily_returns.std(ddof=1)
        * np.sqrt(252)
        * 100
    )

    return {
        "volatility_pct": float(volatility),
        "observations": len(daily_returns),
        "price_field": price_column,
        "start_date": recent_prices.index[0].date(),
        "end_date": end_date.date()
    }

def calculate_sharpe_ratio(history, risk_free_rate_pct=4.0):
    """Calculate the trailing one-year annualized Sharpe ratio."""

    if history is None or history.empty:
        raise ValueError("Historical data is unavailable.")

    coverage = assess_metric_coverage(history)

    if not coverage["Sharpe Ratio"]["available"]:
        raise ValueError(
            "Insufficient historical coverage for Sharpe ratio."
        )

    try:
        risk_free_rate_pct = float(risk_free_rate_pct)
    except (TypeError, ValueError):
        raise ValueError("Invalid risk-free rate.")

    if (
        not np.isfinite(risk_free_rate_pct)
        or risk_free_rate_pct <= -100
    ):
        raise ValueError("Invalid risk-free rate.")

    price_column = (
        "Adj Close" if "Adj Close" in history.columns
        else "Close"
    )

    if price_column not in history.columns:
        raise ValueError("Missing closing price column.")

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

    prices = pd.to_numeric(
        history[price_column], errors="coerce"
    ).copy()

    prices.index = dates
    prices = prices.sort_index()

    end_date = prices.index[-1]
    start_date = end_date - pd.Timedelta(days=365)

    recent_prices = prices.loc[
        prices.index >= start_date
    ]

    if (
        recent_prices.isna().any()
        or (recent_prices <= 0).any()
        or not np.isfinite(recent_prices.to_numpy()).all()
    ):
        raise ValueError("Invalid historical prices.")

    daily_returns = recent_prices.pct_change().dropna()

    if len(daily_returns) < 2:
        raise ValueError("Insufficient daily returns.")

    # Convert an assumed effective annual risk-free
    # rate into an equivalent daily rate.
    daily_risk_free = (
        (1 + risk_free_rate_pct / 100) ** (1 / 252)
        - 1
    )

    daily_excess_returns = (
        daily_returns - daily_risk_free
    )

    daily_volatility = daily_returns.std(ddof=1)

    if (
        not np.isfinite(daily_volatility)
        or np.isclose(daily_volatility, 0, atol=1e-12)
    ):
        raise ValueError(
            "Sharpe ratio is undefined for zero volatility."
        )

    sharpe_ratio = (
        daily_excess_returns.mean()
        / daily_volatility
        * np.sqrt(252)
    )

    return {
        "sharpe_ratio": float(sharpe_ratio),
        "risk_free_rate_pct": risk_free_rate_pct,
        "annualized_volatility_pct": float(
            daily_volatility * np.sqrt(252) * 100
        ),
        "observations": len(daily_returns),
        "price_field": price_column,
        "start_date": recent_prices.index[0].date(),
        "end_date": end_date.date()
    }

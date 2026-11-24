"""Deterministic, FICTIONAL weekday OHLCV data for a public demo.

Not sourced from or related to a listed security, exchange, or live market.
The weekday calendar is illustrative; it is not an actual exchange calendar.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def create_demo_history(as_of=None, observations=510) -> pd.DataFrame:
    """Generate synthetic historical quotations on approximate weekday dates."""
    if not isinstance(observations, int) or observations < 270 or observations > 1000:
        raise ValueError("Demo observations must be between 270 and 1000.")
    latest = pd.Timestamp.today().normalize() if as_of is None else pd.Timestamp(as_of).normalize()
    dates = pd.bdate_range(end=latest, periods=observations)
    # Fixed repeating returns so results are deterministic and do not use external APIs.
    moves = np.resize(np.array([0.006, -0.005, 0.003, -0.004, 0.002, -0.001]), observations - 1)
    close = np.r_[100.0, 100.0 * np.cumprod(1.0 + moves)]
    # Illustrate the difference between two price bases without representing real dividends.
    adjustment = np.linspace(0.985, 1.0, observations)
    prices = pd.DataFrame(
        {
            "Open": close * 0.998,
            "High": close * 1.012,
            "Low": close * 0.985,
            "Close": close,
            "Adj Close": close * adjustment,
            "Volume": np.resize([100000, 115000, 130000, 90000], observations),
        },
        index=dates,
    )
    prices.index.name = "Date"
    return prices

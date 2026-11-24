"""Local, manually priced two-currency portfolio valuation for Global Investor.

All entered prices are user-supplied and all conversions use ONE manually supplied
FX assumption. This models holding-price P&L at a common FX rate; it does NOT
model the FX rate at the time of each purchase, dividends, fees, or taxes.
"""

from decimal import Decimal, InvalidOperation

CURRENCIES = ("PHP", "USD")


def _decimal(value, field):
    if isinstance(value, bool):
        raise ValueError(f"{field} must be numeric.")
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError(f"{field} must be numeric.") from None
    if not amount.is_finite():
        raise ValueError(f"{field} must be finite.")
    return amount


def calculate_portfolio(holdings, base_currency="PHP", php_per_usd=58.0):
    """Value long-only holdings in PHP or USD using an explicit FX assumption.

    holdings: sequence of dicts with name, shares, buy_price, current_price,
              and currency (PHP or USD). Prices are *manual inputs*.
    php_per_usd: number of PHP units equal to exactly one USD.
    """
    if base_currency not in CURRENCIES:
        raise ValueError("Base currency must be PHP or USD.")

    rate = _decimal(php_per_usd, "PHP per USD rate")
    if rate <= 0:
        raise ValueError("PHP per USD rate must be greater than zero.")

    if not holdings:
        raise ValueError("Add at least one holding.")

    def fx(currency):
        if currency == base_currency:
            return Decimal("1")
        return rate if currency == "USD" else Decimal("1") / rate

    output = []
    total_cost = Decimal("0")
    total_value = Decimal("0")
    for n, h in enumerate(holdings, start=1):
        if not isinstance(h, dict):
            raise ValueError(f"Row {n} must contain a holding.")
        name = str(h.get("name", "")).strip()
        if not name or name.lower() in ("nan", "none"):
            raise ValueError(f"Row {n}: name is required.")
        currency = str(h.get("currency", "")).strip().upper()
        if currency not in CURRENCIES:
            raise ValueError(f"Row {n}: choose PHP or USD currency.")

        shares = _decimal(h.get("shares"), f"Row {n} shares")
        buy = _decimal(h.get("buy_price"), f"Row {n} average buy price")
        current = _decimal(h.get("current_price"), f"Row {n} current price")
        if shares <= 0:
            raise ValueError(f"Row {n}: shares must be greater than zero.")
        if buy <= 0:
            raise ValueError(f"Row {n}: buy price must be greater than zero.")
        if current < 0:
            raise ValueError(f"Row {n}: current price cannot be negative.")

        cost_native = shares * buy
        value_native = shares * current
        factor = fx(currency)
        cost_base = cost_native * factor
        value_base = value_native * factor
        pnl_base = value_base - cost_base
        pct = (value_base / cost_base - Decimal("1")) * Decimal("100")
        total_cost += cost_base
        total_value += value_base

        output.append({
            "name": name,
            "currency": currency,
            "shares": float(shares),
            "buy_price": float(buy),
            "current_price": float(current),
            "invested_base": float(cost_base),
            "current_value_base": float(value_base),
            "pnl_base": float(pnl_base),
            "return_pct": float(pct),
        })

    if total_value > 0:
        for row in output:
            row["allocation_pct"] = float(
                Decimal(str(row["current_value_base"])) / total_value * Decimal("100")
            )
    else:
        for row in output:
            row["allocation_pct"] = 0.0

    pnl = total_value - total_cost
    return {
        "base_currency": base_currency,
        "php_per_usd": float(rate),
        "invested": float(total_cost),
        "value": float(total_value),
        "pnl": float(pnl),
        "return_pct": float(pnl / total_cost * Decimal("100")),
        "holdings": output,
        "largest_allocation_pct": max(row["allocation_pct"] for row in output),
    }

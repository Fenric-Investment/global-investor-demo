"""Validated, in-memory portfolio file exchange for the Global Investor beta.

CSV: holdings only. JSON: holdings plus reporting-currency and manual FX settings.
Neither format accesses the legacy portfolio.csv or saves a file on the server.
Files are processed in memory; uploaded files reach the Streamlit server process.
"""

import csv
import io
import json
from decimal import Decimal, InvalidOperation

HEADER = ("name", "shares", "buy_price", "current_price", "currency")
MAX_BYTES = 512 * 1024
MAX_HOLDINGS = 200
SNAPSHOT_FORMAT = "fenric-global-investor-portfolio"
SNAPSHOT_VERSION = 1


def _number(value, label, *, positive=False, allow_zero=False):
    if isinstance(value, bool):
        raise ValueError(f"{label} must be a number.")
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError(f"{label} must be a number.") from None
    if not number.is_finite():
        raise ValueError(f"{label} must be finite.")
    if positive and number <= 0:
        raise ValueError(f"{label} must be greater than zero.")
    if allow_zero and number < 0:
        raise ValueError(f"{label} cannot be negative.")
    if abs(number) > Decimal("1000000000000"):
        raise ValueError(f"{label} is outside the supported range.")
    if positive and number < Decimal("0.00000001"):
        raise ValueError(f"{label} is below the supported minimum.")
    return number


def normalize_holdings(holdings):
    """Validate editable holding records and return canonical numeric dictionaries."""
    if not isinstance(holdings, (tuple, list)) or not holdings:
        raise ValueError("Add at least one holding before importing or exporting.")
    if len(holdings) > MAX_HOLDINGS:
        raise ValueError(f"A portfolio may contain at most {MAX_HOLDINGS} rows.")

    result = []
    for row_number, row in enumerate(holdings, 1):
        if not isinstance(row, dict):
            raise ValueError(f"Row {row_number}: invalid holding format.")
        if set(row) != set(HEADER):
            raise ValueError(f"Row {row_number}: expected {', '.join(HEADER)}.")

        name = row["name"]
        if not isinstance(name, str):
            raise ValueError(f"Row {row_number}: holding name must be text.")
        name = name.strip()
        if not name or len(name) > 64 or not name.isprintable():
            raise ValueError(f"Row {row_number}: name must be 1–64 printable characters.")
        # Protect spreadsheets that execute formula-like CSV contents on opening.
        if name[0] in "=+-@" or name.startswith(("\ufeff", "\u200b")):
            raise ValueError(f"Row {row_number}: holding name cannot start with a formula character.")

        currency = row["currency"]
        if not isinstance(currency, str) or currency.strip().upper() not in ("PHP", "USD"):
            raise ValueError(f"Row {row_number}: currency must be PHP or USD.")
        currency = currency.strip().upper()

        shares = _number(row["shares"], f"Row {row_number} shares", positive=True)
        buy = _number(row["buy_price"], f"Row {row_number} buy price", positive=True)
        current = _number(row["current_price"], f"Row {row_number} current price", allow_zero=True)

        result.append({
            "name": name,
            "shares": float(shares),
            "buy_price": float(buy),
            "current_price": float(current),
            "currency": currency,
        })
    return result


def _read_text(file_bytes):
    if not isinstance(file_bytes, bytes):
        raise ValueError("The uploaded file must contain bytes.")
    if not file_bytes or len(file_bytes) > MAX_BYTES:
        raise ValueError("The file is empty or exceeds the 512 KB limit.")
    try:
        return file_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise ValueError("The file must be UTF-8 encoded.") from None


def import_csv(file_bytes):
    """Return validated holdings. Header names must match the beta schema."""
    text = _read_text(file_bytes)
    try:
        reader = csv.DictReader(io.StringIO(text, newline=""), strict=True)
        if reader.fieldnames is None or len(reader.fieldnames) != len(HEADER) or set(reader.fieldnames) != set(HEADER):
            raise ValueError("CSV columns must be: name, shares, buy_price, current_price, currency.")
        records = []
        for row in reader:
            if len(records) >= MAX_HOLDINGS:
                raise ValueError(f"A portfolio may contain at most {MAX_HOLDINGS} rows.")
            if None in row or any(value is None for value in row.values()):
                raise ValueError("CSV contains a row with too many or too few columns.")
            records.append(row)
    except csv.Error:
        raise ValueError("Malformed CSV file.") from None
    return normalize_holdings(records)


def export_csv(holdings):
    """Export validated holdings as UTF-8-BOM CSV for common spreadsheet apps."""
    records = normalize_holdings(holdings)
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=HEADER, lineterminator="\n")
    writer.writeheader()
    writer.writerows(records)
    return buffer.getvalue().encode("utf-8-sig")


def _validate_settings(base_currency, php_per_usd):
    if base_currency not in ("PHP", "USD"):
        raise ValueError("Reporting currency must be PHP or USD.")
    fx = _number(php_per_usd, "PHP per USD exchange-rate assumption", positive=True)
    if fx < Decimal("0.000001") or fx > Decimal("1000000"):
        raise ValueError("FX assumption is outside the supported range.")
    return float(fx)


def export_snapshot(holdings, base_currency, php_per_usd):
    """Export a user-owned JSON file, including manual FX/reporting settings."""
    records = normalize_holdings(holdings)
    fx = _validate_settings(base_currency, php_per_usd)
    snapshot = {
        "format": SNAPSHOT_FORMAT,
        "version": SNAPSHOT_VERSION,
        "holdings": records,
        "base_currency": base_currency,
        "php_per_usd": fx,
        "note": "Manual prices and FX assumptions, not live market data",
    }
    return (json.dumps(snapshot, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")


def import_snapshot(file_bytes):
    """Parse a known-version JSON snapshot; do not accept arbitrary JSON objects."""
    text = _read_text(file_bytes)
    try:
        snapshot = json.loads(text, parse_constant=lambda _: (_ for _ in ()).throw(ValueError("Invalid JSON numeric value.")))
    except (json.JSONDecodeError, ValueError, TypeError):
        raise ValueError("Invalid portfolio snapshot JSON.") from None
    if not isinstance(snapshot, dict) or snapshot.get("format") != SNAPSHOT_FORMAT or type(snapshot.get("version")) is not int or snapshot["version"] != SNAPSHOT_VERSION:
        raise ValueError("Unsupported portfolio snapshot format or version.")
    holdings = normalize_holdings(snapshot.get("holdings"))
    fx = _validate_settings(snapshot.get("base_currency"), snapshot.get("php_per_usd"))
    return {
        "holdings": holdings,
        "base_currency": snapshot["base_currency"],
        "php_per_usd": fx,
    }


def import_portfolio_file(file_bytes, filename):
    """Load known file types only; CSV has no saved FX or reporting settings."""
    if not isinstance(filename, str):
        raise ValueError("Choose a .csv or .json portfolio file.")
    if filename.lower().endswith(".csv"):
        return {"holdings": import_csv(file_bytes), "base_currency": None, "php_per_usd": None}
    if filename.lower().endswith(".json"):
        return import_snapshot(file_bytes)
    raise ValueError("Choose a .csv or .json portfolio file.")

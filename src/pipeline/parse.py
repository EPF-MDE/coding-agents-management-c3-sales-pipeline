"""Field-level parsing for incoming sales rows.

Source systems disagree about formatting, so every raw field goes through
here before anything else touches it.
"""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal

ZERO = Decimal("0.00")

# Amounts arrive in a few shapes depending on the exporter:
#   "42.50"        POS terminals (US-style decimal point)
#   "42,50"        partner exports (European decimal comma)
#   "-8.00"        refunds
#   "1\xa0321,49"  partner exports, amounts >= 1000 (NBSP thousands separator)
# Anything we cannot make sense of is treated as zero rather than crashing
# the nightly run.
_AMOUNT_RE = re.compile(r"[-+]?[0-9]+(?:[.,][0-9]{1,2})?")


def parse_amount(raw: str) -> Decimal:
    """Parse a monetary amount from an exporter's raw string field."""
    if raw is None:
        return ZERO
    # Non-breaking space is used by the partner export as a thousands
    # separator (e.g. "1\xa0321,49"); drop it before matching so the digits
    # on both sides of it are treated as one number.
    cleaned = raw.strip().replace("\xa0", "")
    match = _AMOUNT_RE.search(cleaned)
    if match is None:
        return ZERO
    return Decimal(match.group(0).replace(",", "."))


def parse_date(raw: str) -> date:
    """Parse a transaction date. Exporters use ISO or DD/MM/YYYY."""
    raw = raw.strip()
    if "/" in raw:
        day, month, year = raw.split("/")
        return date(int(year), int(month), int(day))
    return date.fromisoformat(raw)


def parse_quantity(raw: str) -> int:
    raw = raw.strip()
    if not raw:
        return 1
    return int(raw)

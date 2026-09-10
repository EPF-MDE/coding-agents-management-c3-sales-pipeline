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
#   "42.50"      POS terminals (US-style decimal point)
#   "42,50"      partner exports (European decimal comma)
#   "-8.00"      refunds
#   "1 321,49"   partner exports, four figures and up: the thousands group is
#                separated by a NO-BREAK SPACE (U+00A0), as French locales do.
# Anything we cannot make sense of is treated as zero rather than crashing
# the nightly run.

# Separators that only ever group digits, never mark the decimal.
_GROUPING_SPACE = dict.fromkeys(
    (0x0020, 0x00A0, 0x202F, 0x2009, 0x2007, 0x0027, 0x2019), None,  # NBSP & co.
)

_AMOUNT_RE = re.compile(r"[-+]?[0-9]+(?:[.,][0-9]+)*")


def _to_decimal_text(token: str) -> str:
    """Normalise a digits-and-separators token to plain Decimal syntax.

    The last '.' or ',' is the decimal separator when it is followed by one or
    two digits; every other '.' or ',' groups thousands and is dropped.
    """
    head, sep, tail = token.rpartition(".") if "." in token else ("", "", "")
    comma_head, comma_sep, comma_tail = token.rpartition(",")
    if comma_sep and (not sep or token.rindex(",") > token.rindex(".")):
        head, sep, tail = comma_head, comma_sep, comma_tail

    if sep and 1 <= len(tail) <= 2:
        return f"{head.replace('.', '').replace(',', '')}.{tail}"
    return token.replace(".", "").replace(",", "")


def parse_amount(raw: str) -> Decimal:
    """Parse a monetary amount from an exporter's raw string field."""
    if raw is None:
        return ZERO
    match = _AMOUNT_RE.search(raw.strip().translate(_GROUPING_SPACE))
    if match is None:
        return ZERO
    return Decimal(_to_decimal_text(match.group(0)))


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

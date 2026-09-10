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
#   "1 321,49"   partner exports, thousands grouped -- the grouping character
#                is U+00A0 NO-BREAK SPACE, not a plain space
#   "-8.00"      refunds
#
# Two patterns, because an amount either groups its thousands or it does not.
# Three digits after a separator are a thousands group; one or two are the
# decimal part. Both use fullmatch(), never search(): a field we understand
# only in part must not become a number, because a partial parse raises
# nothing and returns something plausible. Anything we cannot make sense of
# is still zero rather than a crash in the nightly run.
#
# Grouping character: dot, comma, or a space that str.strip() will not remove
# from the middle of a field -- plain, NO-BREAK (the partner's), NARROW
# NO-BREAK, THIN, FIGURE.
_GROUP_SEPARATORS = ".,\u0020\u00a0\u202f\u2009\u2007"

_GROUPED_AMOUNT_RE = re.compile(
    r"[-+]?[0-9]{1,3}([" + re.escape(_GROUP_SEPARATORS) + r"])[0-9]{3}"
    r"(?:\1[0-9]{3})*"
    r"(?:([.,])[0-9]{1,2})?"
)
_PLAIN_AMOUNT_RE = re.compile(r"[-+]?[0-9]+(?:[.,][0-9]{1,2})?")


def parse_amount(raw: str) -> Decimal:
    """Parse a monetary amount from an exporter's raw string field."""
    if raw is None:
        return ZERO
    text = raw.strip()

    grouped = _GROUPED_AMOUNT_RE.fullmatch(text)
    if grouped:
        group_sep, decimal_sep = grouped.group(1), grouped.group(2)
        if decimal_sep == group_sep:
            # e.g. "1.321.49" -- we cannot tell a group from a decimal part.
            return ZERO
        text = text.replace(group_sep, "")
    elif not _PLAIN_AMOUNT_RE.fullmatch(text):
        return ZERO

    return Decimal(text.replace(",", "."))


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

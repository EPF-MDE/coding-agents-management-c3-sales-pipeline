"""Field-level parsing for incoming sales rows.

Source systems disagree about formatting, so every raw field goes through
here before anything else touches it.
"""

from __future__ import annotations

import logging
import re
from datetime import date
from decimal import Decimal

logger = logging.getLogger(__name__)

ZERO = Decimal("0.00")

# Amounts arrive in a few shapes depending on the exporter:
#   "42.50"        POS terminals (US-style decimal point)
#   "42,50"        partner exports (European decimal comma)
#   "-8.00"        refunds
#   "1 321,49"     partner exports, amounts >= 1000: a grouping separator
#                  (regular or non-breaking space) between digit groups,
#                  ahead of the decimal comma
# Grouping separators are stripped before matching; the regex itself only
# understands a single decimal separator.
# Anything we cannot make sense of is treated as zero rather than crashing
# the nightly run.
_AMOUNT_RE = re.compile(r"[-+]?[0-9]+(?:[.,][0-9]{1,2})?")
_GROUPING_SEPARATOR_RE = re.compile(r"\s+")


def parse_amount(raw: str) -> Decimal:
    """Parse a monetary amount from an exporter's raw string field."""
    if raw is None:
        return ZERO
    cleaned = _GROUPING_SEPARATOR_RE.sub("", raw.strip())
    match = _AMOUNT_RE.search(cleaned)
    if match is None:
        return ZERO
    if match.span() != (0, len(cleaned)):
        logger.warning(
            "parse_amount: %r matched only %r after stripping grouping "
            "separators; treating as unparseable",
            raw,
            match.group(0),
        )
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

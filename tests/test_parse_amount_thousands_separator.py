"""Regression test for BUG-REPORT.md: S-014 monthly revenue mismatch.

Root cause: parse_amount's regex does not recognise the non-breaking space
used as a thousands separator in French partner exports (e.g. "1 321,49"
meaning 1321.49 euros). It matches only the digits before the separator,
silently truncating the amount to "1".
"""
from decimal import Decimal

from pipeline.parse import parse_amount


def test_parse_amount_handles_thousands_separator():
    # Non-breaking space (\xa0) as thousands separator, French format.
    assert parse_amount("1\xa0321,49") == Decimal("1321.49")


def test_parse_amount_handles_thousands_separator_no_decimals():
    assert parse_amount("1\xa0197,00") == Decimal("1197.00")


def test_parse_amount_still_handles_plain_values():
    # Make sure the fix doesn't break the common case.
    assert parse_amount("91,83") == Decimal("91.83")
    assert parse_amount("42.50") == Decimal("42.50")
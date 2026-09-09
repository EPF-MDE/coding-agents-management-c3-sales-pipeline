"""Regression tests for the S-014 August discrepancy reported in BUG-REPORT.md.

This file is the red command:

    pytest tests/test_bug_s014.py -v

It fails on the original code and passes once `pipeline.parse` understands
thousands separators.
"""

from decimal import Decimal
from pathlib import Path

import pytest

from pipeline import ingest, load, report, transform
from pipeline.parse import parse_amount

RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"

# Finance's figure for store S-014, August 2026, reconciled against till
# receipts (BUG-REPORT.md). The pipeline reported 50043.47.
FINANCE_TOTAL_S014 = Decimal("56232.09")

NBSP = "\u00a0"


def test_s014_august_total_matches_finance(tmp_path):
    """The symptom, straight from the bug report."""
    rows = ingest.read_all(RAW_DIR)
    records = transform.transform_all(rows)
    conn = load.connect(tmp_path / "regression.db")
    load.load(records, conn)

    assert report.store_total(conn, "S-014") == FINANCE_TOTAL_S014


def test_no_amount_field_is_only_partly_understood():
    """Every amount in the raw exports must round-trip.

    A parser that reads "1 321,49" as 1 does not fail; it returns a number
    that looks plausible. This asserts nothing is silently truncated.
    """
    offenders = [
        (row.txn_id, row.amount)
        for row in ingest.read_all(RAW_DIR)
        if parse_amount(row.amount) == Decimal(0) or _digits_dropped(row.amount)
    ]
    assert offenders == []


def _digits_dropped(raw: str) -> bool:
    parsed = "".join(c for c in str(parse_amount(raw)) if c.isdigit()).lstrip("0")
    original = "".join(c for c in raw if c.isdigit()).lstrip("0")
    return parsed != original


@pytest.mark.parametrize(
    "raw, expected",
    [
        (f"1{NBSP}321,49", "1321.49"),  # the partner's format, as it is in the CSV
        ("1 321,49", "1321.49"),        # plain space grouping
        ("1.321,49", "1321.49"),        # European dot grouping
        ("1,321.49", "1321.49"),        # US comma grouping
        ("1234.56", "1234.56"),         # POS four-figure amount, ungrouped
        ("42,50", "42.50"),             # unchanged: European decimal comma
        ("42.50", "42.50"),             # unchanged: US decimal point
        ("-8.00", "-8.00"),             # unchanged: refund
    ],
)
def test_thousands_separators_are_not_truncated(raw, expected):
    assert parse_amount(raw) == Decimal(expected)


@pytest.mark.parametrize("raw", ["12abc34", "n/a 99", "1 2 3", "42.50.60"])
def test_a_partial_parse_is_refused_rather_than_truncated(raw):
    """The structural defect: `.search()` accepted a prefix of a field it did
    not understand. A value we only partly understand must not become a number.
    """
    assert parse_amount(raw) == Decimal("0.00")

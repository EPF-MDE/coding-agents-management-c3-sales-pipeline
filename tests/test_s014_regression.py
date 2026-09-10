"""Regression tests for the S-014 August revenue shortfall (BUG-REPORT.md).

The partner exporter writes thousands with a NO-BREAK SPACE (U+00A0):
    "1 321,49"
`parse_amount` used to stop at the first group of digits and return
Decimal("1"), silently losing the rest of every four-figure sale.
"""

from __future__ import annotations

from decimal import Decimal

from pipeline import ingest, report, transform
from pipeline.load import connect, load
from pipeline.parse import parse_amount

NBSP = " "  # NO-BREAK SPACE, what the partner exporter actually writes

# Reconciled against the till receipts, per BUG-REPORT.md.
EXPECTED_S014_AUGUST = Decimal("56232.09")


def test_parse_amount_handles_nbsp_thousands_separator():
    assert parse_amount(f"1{NBSP}321,49") == Decimal("1321.49")


def test_parse_amount_handles_other_grouping_shapes():
    assert parse_amount("1 321,49") == Decimal("1321.49")  # plain space
    assert parse_amount(f"12{NBSP}345{NBSP}678,90") == Decimal("12345678.90")
    assert parse_amount(f"-1{NBSP}070,51") == Decimal("-1070.51")


def test_parse_amount_still_handles_the_simple_shapes():
    assert parse_amount("42.50") == Decimal("42.50")
    assert parse_amount("42,50") == Decimal("42.50")
    assert parse_amount("-8.00") == Decimal("-8.00")
    assert parse_amount("") == Decimal("0.00")
    assert parse_amount("n/a") == Decimal("0.00")


def test_s014_august_total_matches_finance(tmp_path):
    """End-to-end over the real data/raw/ exports."""
    records = transform.transform_all(ingest.read_all())
    conn = connect(tmp_path / "warehouse.db")
    load(records, conn)

    s014 = [r for r in records if r.store_id == "S-014"]
    assert len(s014) == 420, "transaction count should be unaffected"
    assert report.store_total(conn, "S-014") == EXPECTED_S014_AUGUST

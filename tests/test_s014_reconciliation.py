"""Feedback loop for BUG-REPORT.md — store S-014 is ~11% light for August.

Nine hand-built partner rows. No warehouse, no clock, no network: we call
parse + transform directly and sum ``net_amount``, which is the exact SUM
that ``pipeline.report.store_total`` runs over the same records.

Finance's clues, reproduced here:
  - the transaction COUNT is right         -> test_no_rows_are_dropped   (green)
  - the money is low, most rows a little   -> test_s014_reconciles_...   (RED)

Mechanical hypothesis loop — edit ONE thing in ``_ROWS``, rerun (~1s):

  * Thousands separator (P-06/07/08 use a non-breaking space to group
    thousands): change P-06's amount from "1 000,00" to "1000,00".
    The total moves by exactly +999.00 -> that row's amount is being
    truncated at the separator. This is the live hypothesis.
  * Discount double-applied: set every discount_pct to "". The gap stays
    ~4200 wide -> discounts are not the cause.
  * store_id casing / whitespace: P-09 already arrives as " s-014 " and
    still lands in the S-014 bucket (test_no_rows_are_dropped) -> not it.
  * Rows dropped as duplicates / by a date filter: count is 9 here and 420
    in Finance's data; transform_all applies no date filter -> not it.
"""

from decimal import Decimal

from pipeline.ingest import RawRow
from pipeline.parse import parse_amount
from pipeline.transform import transform_all

NBSP = " "  # the partner's regional thousands separator
STORE = "S-014"

# (txn_id, amount, quantity, discount_pct); txn_date is filled in fixed below.
_ROWS = [
    ("P-01", "100,00", "1", ""),
    ("P-02", "50,00", "1", "10"),
    ("P-03", "200,00", "1", "25"),
    ("P-04", "12,34", "1", ""),
    ("P-05", "8,00", "2", ""),
    ("P-06", f"1{NBSP}000,00", "1", ""),
    ("P-07", f"2{NBSP}500,00", "1", "20"),
    ("P-08", f"1{NBSP}234,56", "1", ""),
    ("P-09", "300,00", "3", ""),
]

# Hand-computed net per row, then summed:
#   100.00 + 45.00 + 150.00 + 12.34 + 8.00
#         + 1000.00 + 2000.00 + 1234.56 + 300.00
EXPECTED_TOTAL = Decimal("4849.90")


def partner_rows() -> list[RawRow]:
    rows = []
    for i, (txn_id, amount, qty, disc) in enumerate(_ROWS):
        store_id = " s-014 " if txn_id == "P-09" else STORE
        rows.append(
            RawRow(
                source="partner_export_2026-08",
                txn_id=txn_id,
                store_id=store_id,
                txn_date=f"2026-08-{i + 1:02d}",
                amount=amount,
                quantity=qty,
                discount_pct=disc,
            )
        )
    return rows


def s014_total(records) -> Decimal:
    return sum((r.net_amount for r in records if r.store_id == STORE), Decimal("0.00"))


def test_no_rows_are_dropped():
    records = transform_all(partner_rows())
    assert len(records) == 9
    assert sum(1 for r in records if r.store_id == STORE) == 9


def test_s014_reconciles_to_hand_computed_total():
    records = transform_all(partner_rows())
    assert s014_total(records) == EXPECTED_TOTAL


def test_parse_amount_keeps_the_grouped_value():
    assert parse_amount(f"1{NBSP}000,00") == Decimal("1000.00")

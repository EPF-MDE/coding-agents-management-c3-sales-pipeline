"""Regression tests for the S-014 August discrepancy reported in BUG-REPORT.md.

This file is the red command:

    pytest tests/test_bug_s014.py -v
"""

from decimal import Decimal
from pathlib import Path

from pipeline import ingest, load, report, transform

RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"

# Finance's figure for store S-014, August 2026, reconciled against till
# receipts (BUG-REPORT.md). The pipeline reported 50043.47.
FINANCE_TOTAL_S014 = Decimal("56232.09")


def test_s014_august_total_matches_finance(tmp_path):
    """The symptom, straight from the bug report."""
    rows = ingest.read_all(RAW_DIR)
    records = transform.transform_all(rows)
    conn = load.connect(tmp_path / "regression.db")
    load.load(records, conn)

    assert report.store_total(conn, "S-014") == FINANCE_TOTAL_S014

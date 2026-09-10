"""End-to-end checks over the real fixture data."""

from decimal import Decimal
from pathlib import Path

from pipeline import ingest, load, report, transform

RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"


def run(tmp_path):
    rows = ingest.read_all(RAW_DIR)
    records = transform.transform_all(rows)
    conn = load.connect(tmp_path / "test.db")
    stats = load.load(records, conn)
    return rows, records, stats, conn


def test_every_raw_row_reaches_the_warehouse(tmp_path):
    rows, records, stats, conn = run(tmp_path)
    assert len(records) == len(rows)
    assert stats.inserted == len(rows)
    count = conn.execute("SELECT COUNT(*) FROM sales").fetchone()[0]
    assert count == len(rows)


def test_no_rows_are_dropped_as_duplicates(tmp_path):
    _, _, stats, _ = run(tmp_path)
    assert stats.duplicates_skipped == 0


def test_every_store_reports_some_revenue(tmp_path):
    _, _, _, conn = run(tmp_path)
    totals = report.all_store_totals(conn)
    assert len(totals) == 14
    assert all(total > 0 for _, total in totals)


def test_daily_revenue_covers_the_whole_month(tmp_path):
    _, _, _, conn = run(tmp_path)
    days = report.daily_revenue(conn, "S-014")
    assert len(days) == 31


def test_s014_august_total_matches_finance_reconciliation(tmp_path):
    """BUG-REPORT.md: finance reconciled S-014's till receipts to 56 232,09 EUR."""
    _, _, _, conn = run(tmp_path)
    total = report.store_total(conn, "S-014")
    assert total == Decimal("56232.09")

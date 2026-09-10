"""Regression test for the August-2026 S-014 revenue undercount.

Finance (Claire) reconciled store S-014's till receipts for August 2026 at
56 232,09 EUR. The pipeline's own report says 50 043,47 EUR for the same
store/month, a shortfall of 6 188,62 EUR, even though both sides agree on
the transaction count (420).

Root cause: five transactions in data/raw/partner_export_2026-08.csv have
amounts >= 1000 that use a non-breaking-space thousands separator, e.g.
"1\xa0321,49". pipeline.parse.parse_amount's regex does not recognise that
separator and silently truncates the value to "1".

This test does NOT hardcode Claire's numbers. It recomputes the store's
August total directly from the raw CSV using an amount parser written
independently of pipeline.parse (so it can't share the same bug), and
compares that to whatever pipeline.report.store_total() actually returns
after a full ingest -> transform -> load run. The two must agree to the
cent; if they don't, the pipeline is silently losing money somewhere in
that path.
"""

from __future__ import annotations

import re
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from pipeline import ingest, load, report, transform

RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"
STORE = "S-014"
MONTH_PREFIX = "2026-08"
CENT = Decimal("0.01")


def _independent_amount(raw: str) -> Decimal:
    """Parse a monetary string from scratch, deliberately NOT reusing
    pipeline.parse.parse_amount, so this check can't inherit its bug.

    Handles the documented exporter formats:
      - plain "42.50"
      - European decimal comma "42,50"
      - thousands separators (regular space, NBSP, or dot) combined with
        either decimal marker, e.g. "1 321,49" / "1\xa0321,49"
    """
    s = raw.strip()
    sign = ""
    if s and s[0] in "+-":
        sign, s = s[0], s[1:]

    # Strip whitespace used as a thousands separator (regular space or NBSP).
    s = s.replace("\xa0", "").replace(" ", "")

    if not re.fullmatch(r"[0-9.,]+", s):
        raise ValueError(f"cannot parse amount: {raw!r}")

    # The last "." or "," is the decimal marker (followed by 1-2 digits);
    # anything else is a thousands separator and gets dropped.
    last_sep = max(s.rfind("."), s.rfind(","))
    if last_sep == -1 or len(s) - last_sep - 1 > 2:
        integer_part, frac = s, "00"
    else:
        integer_part, frac = s[:last_sep], s[last_sep + 1 :]
    integer_part = re.sub(r"[.,]", "", integer_part)
    return Decimal(sign + integer_part + "." + frac)


def _independent_discount(raw: str) -> Decimal:
    raw = (raw or "").strip()
    if not raw:
        return Decimal("0")
    return Decimal(raw.replace(",", "."))


def _independent_store_total(store_id: str, month_prefix: str) -> tuple[Decimal, int]:
    total = Decimal("0.00")
    count = 0
    for row in ingest.read_all(RAW_DIR):
        if row.store_id.strip().upper() != store_id:
            continue
        if not row.txn_date.strip().startswith(month_prefix):
            continue
        gross = _independent_amount(row.amount)
        discount = _independent_discount(row.discount_pct)
        factor = (Decimal("100") - discount) / Decimal("100")
        net = (gross * factor).quantize(CENT, rounding=ROUND_HALF_UP)
        total += net
        count += 1
    return total, count


def _pipeline_store_total(tmp_path: Path, store_id: str) -> tuple[Decimal, int]:
    rows = ingest.read_all(RAW_DIR)
    records = transform.transform_all(rows)
    conn = load.connect(tmp_path / "test.db")
    load.load(records, conn)
    total = report.store_total(conn, store_id)
    count = conn.execute(
        "SELECT COUNT(*) FROM sales WHERE store_id = ?", (store_id,)
    ).fetchone()[0]
    return total, count


def test_s014_august_total_matches_independent_recompute(tmp_path):
    independent_total, independent_count = _independent_store_total(STORE, MONTH_PREFIX)
    pipeline_total, pipeline_count = _pipeline_store_total(tmp_path, STORE)

    assert independent_count == pipeline_count, (
        f"transaction count mismatch: independent recompute saw "
        f"{independent_count}, pipeline loaded {pipeline_count}"
    )
    assert independent_total == pipeline_total, (
        f"pipeline report total for {STORE} in {MONTH_PREFIX} is "
        f"{pipeline_total} EUR but an independent recompute from the raw "
        f"CSV gives {independent_total} EUR "
        f"(delta {independent_total - pipeline_total} EUR)"
    )

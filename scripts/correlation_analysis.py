#!/usr/bin/env python3
"""Per-transaction correlation analysis for the S-014 August-2026 undercount.

For every S-014 transaction dated August 2026, this script:

  1. Recomputes the transaction's net amount independently, reusing the
     parser in ``tests/test_s014_regression.py`` (``_independent_amount`` /
     ``_independent_discount``) so the check can't share a bug with
     ``pipeline.parse``.
  2. Runs the real pipeline (ingest -> transform -> load) and looks up the
     net amount it actually stored for that same transaction.
  3. Marks the row "juste" (correct) or "fausse" (wrong) depending on
     whether the two agree to the cent.
  4. Prints a correlation table: how many wrong rows fall among
     transactions with a discount vs without, and among transactions
     >= 1000 EUR vs < 1000 EUR (using the true, independently-parsed gross
     amount for the bucketing).

This is meant to be run twice, to compare before/after the parse_amount
fix for S-014's non-breaking-space thousands separator (see DIAGNOSIS.md):

    # After the fix (current tree)
    python scripts/correlation_analysis.py

    # Before the fix
    git checkout c3c4f4f -- src/pipeline/parse.py
    python scripts/correlation_analysis.py
    git checkout HEAD -- src/pipeline/parse.py
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
TESTS = ROOT / "tests"
for p in (SRC, TESTS):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from pipeline import ingest, load, transform
from test_s014_regression import _independent_amount, _independent_discount

RAW_DIR = ROOT / "data" / "raw"
STORE = "S-014"
MONTH_PREFIX = "2026-08"
CENT = Decimal("0.01")
THRESHOLD = Decimal(1000)


@dataclass
class RowResult:
    txn_id: str
    source: str
    txn_date: str
    true_gross: Decimal
    discount_pct: Decimal
    independent_net: Decimal
    pipeline_net: Decimal | None
    correct: bool


def analyze(raw_dir: Path = RAW_DIR, store: str = STORE, month_prefix: str = MONTH_PREFIX) -> list[RowResult]:
    """Recompute + compare every store/month transaction, row by row."""
    raw_rows = ingest.read_all(raw_dir)
    records = transform.transform_all(raw_rows)

    conn = load.connect(":memory:")
    load.load(records, conn)

    pipeline_net_by_txn: dict[str, Decimal] = {
        txn_id: Decimal(net)
        for txn_id, net in conn.execute(
            "SELECT txn_id, net_amount FROM sales WHERE store_id = ?", (store,)
        )
    }
    conn.close()

    results: list[RowResult] = []
    for row in raw_rows:
        if row.store_id.strip().upper() != store:
            continue
        if not row.txn_date.strip().startswith(month_prefix):
            continue

        true_gross = _independent_amount(row.amount)
        discount_pct = _independent_discount(row.discount_pct)
        factor = (Decimal(100) - discount_pct) / Decimal(100)
        independent_net = (true_gross * factor).quantize(CENT, rounding=ROUND_HALF_UP)

        pipeline_net = pipeline_net_by_txn.get(row.txn_id)
        correct = pipeline_net is not None and pipeline_net == independent_net

        results.append(
            RowResult(
                txn_id=row.txn_id,
                source=row.source,
                txn_date=row.txn_date,
                true_gross=true_gross,
                discount_pct=discount_pct,
                independent_net=independent_net,
                pipeline_net=pipeline_net,
                correct=correct,
            )
        )

    return results


def _segment_stats(results: list[RowResult]) -> tuple[int, int]:
    total = len(results)
    wrong = sum(1 for r in results if not r.correct)
    return total, wrong


def print_report(results: list[RowResult]) -> None:
    total, wrong = _segment_stats(results)

    print(f"=== Corrélation S-014 / {MONTH_PREFIX} ===")
    print(f"Transactions analysées : {total}")
    print(f"Lignes fausses (net pipeline != net recalculé indépendamment) : {wrong}")
    print()

    segments = {
        "Avec remise (> 0%)": [r for r in results if r.discount_pct > 0],
        "Sans remise (0%)": [r for r in results if r.discount_pct == 0],
        f">= {THRESHOLD} EUR": [r for r in results if r.true_gross >= THRESHOLD],
        f"< {THRESHOLD} EUR": [r for r in results if r.true_gross < THRESHOLD],
    }

    header = f"{'Segment':<22} | {'Total':>6} | {'Fausses':>7} | {'% fausses':>9}"
    print(header)
    print("-" * len(header))
    for label, rows in segments.items():
        seg_total, seg_wrong = _segment_stats(rows)
        pct = (seg_wrong / seg_total * 100) if seg_total else 0.0
        print(f"{label:<22} | {seg_total:>6} | {seg_wrong:>7} | {pct:>8.2f}%")
    print()

    wrong_rows = [r for r in results if not r.correct]
    if not wrong_rows:
        print(
            "Aucune ligne fausse : le montant net du pipeline correspond au "
            f"recalcul indépendant pour les {total} transactions."
        )
        return

    print(f"Détail des {len(wrong_rows)} ligne(s) fausse(s) :")
    detail_header = (
        f"{'txn_id':<12} {'source':<24} {'date':<12} {'brut réel':>12} "
        f"{'remise%':>8} {'net attendu':>12} {'net pipeline':>13} {'écart':>10}"
    )
    print(detail_header)
    print("-" * len(detail_header))
    for r in wrong_rows:
        pipeline_net_str = "manquant" if r.pipeline_net is None else f"{r.pipeline_net:.2f}"
        delta = "n/a" if r.pipeline_net is None else f"{r.independent_net - r.pipeline_net:.2f}"
        print(
            f"{r.txn_id:<12} {r.source:<24} {r.txn_date:<12} {r.true_gross:>12.2f} "
            f"{r.discount_pct:>7.2f}% {r.independent_net:>12.2f} {pipeline_net_str:>13} {delta:>10}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--raw-dir", type=Path, default=RAW_DIR, help="Répertoire des exports bruts (défaut: data/raw)"
    )
    parser.add_argument("--store", default=STORE, help="Identifiant du magasin (défaut: S-014)")
    parser.add_argument(
        "--month-prefix", default=MONTH_PREFIX, help="Préfixe de date AAAA-MM (défaut: 2026-08)"
    )
    args = parser.parse_args()

    results = analyze(args.raw_dir, args.store, args.month_prefix)
    if not results:
        print(f"Aucune transaction trouvée pour {args.store} / {args.month_prefix}.")
        return 1

    print_report(results)
    return 0 if all(r.correct for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())

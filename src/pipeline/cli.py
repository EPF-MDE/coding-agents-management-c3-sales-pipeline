"""Command line entry point.

    python -m pipeline run
    python -m pipeline report --store S-014
    python -m pipeline totals
"""

from __future__ import annotations

import argparse
from pathlib import Path

from . import ingest, load, report, transform


def cmd_run(args: argparse.Namespace) -> int:
    db_path = Path(args.db)
    if db_path.exists():
        db_path.unlink()
    raw = ingest.read_all()
    records = transform.transform_all(raw)
    conn = load.connect(db_path)
    stats = load.load(records, conn)
    print(f"read      {len(raw)} raw rows")
    print(f"inserted  {stats.inserted}")
    print(f"duplicates skipped {stats.duplicates_skipped}")
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    conn = load.connect(Path(args.db))
    for day, total in report.daily_revenue(conn, args.store):
        print(f"{day}  {total:>12}")
    print(f"{'TOTAL':<10}  {report.store_total(conn, args.store):>12}")
    return 0


def cmd_totals(args: argparse.Namespace) -> int:
    conn = load.connect(Path(args.db))
    for store, total in report.all_store_totals(conn):
        print(f"{store}  {total:>12}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pipeline")
    parser.add_argument("--db", default="warehouse.db")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("run").set_defaults(func=cmd_run)

    report_parser = sub.add_parser("report")
    report_parser.add_argument("--store", required=True)
    report_parser.set_defaults(func=cmd_report)

    sub.add_parser("totals").set_defaults(func=cmd_totals)

    args = parser.parse_args(argv)
    return args.func(args)

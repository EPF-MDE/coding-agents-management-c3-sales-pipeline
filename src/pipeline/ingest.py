"""Read raw exporter files off disk.

One file per source system per month. Nothing here interprets the values;
the fields come back as strings exactly as the exporter wrote them.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"


@dataclass(frozen=True)
class RawRow:
    source: str
    txn_id: str
    store_id: str
    txn_date: str
    amount: str
    quantity: str
    discount_pct: str


def read_file(path: Path) -> list[RawRow]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return [
            RawRow(
                source=path.stem,
                txn_id=row["txn_id"],
                store_id=row["store_id"],
                txn_date=row["txn_date"],
                amount=row["amount"],
                quantity=row["quantity"],
                discount_pct=row["discount_pct"],
            )
            for row in reader
        ]


def read_all(raw_dir: Path | None = None) -> list[RawRow]:
    raw_dir = raw_dir or RAW_DIR
    rows: list[RawRow] = []
    for path in sorted(raw_dir.glob("*.csv")):
        rows.extend(read_file(path))
    return rows

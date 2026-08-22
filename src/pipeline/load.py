"""Write clean sales records into the warehouse (SQLite for now)."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from .transform import SaleRecord

DEFAULT_DB = Path(__file__).resolve().parents[2] / "warehouse.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS sales (
    txn_id       TEXT NOT NULL,
    store_id     TEXT NOT NULL,
    txn_date     TEXT NOT NULL,
    source       TEXT NOT NULL,
    gross_amount TEXT NOT NULL,
    quantity     INTEGER NOT NULL,
    discount_pct TEXT NOT NULL,
    net_amount   TEXT NOT NULL,
    PRIMARY KEY (store_id, txn_id)
);
"""


@dataclass
class LoadStats:
    inserted: int = 0
    duplicates_skipped: int = 0


def connect(db_path: Path | None = None) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path or DEFAULT_DB)
    conn.executescript(SCHEMA)
    return conn


def load(records: list[SaleRecord], conn: sqlite3.Connection) -> LoadStats:
    stats = LoadStats()
    seen: set[tuple[str, str]] = set()
    for record in records:
        key = (record.store_id, record.txn_id)
        if key in seen:
            stats.duplicates_skipped += 1
            continue
        seen.add(key)
        conn.execute(
            "INSERT OR REPLACE INTO sales VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                record.txn_id,
                record.store_id,
                record.txn_date.isoformat(),
                record.source,
                str(record.gross_amount),
                record.quantity,
                str(record.discount_pct),
                str(record.net_amount),
            ),
        )
        stats.inserted += 1
    conn.commit()
    return stats

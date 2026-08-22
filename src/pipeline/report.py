"""Reporting queries over the warehouse."""

from __future__ import annotations

import sqlite3
from decimal import Decimal


def store_total(conn: sqlite3.Connection, store_id: str) -> Decimal:
    rows = conn.execute(
        "SELECT net_amount FROM sales WHERE store_id = ?", (store_id.upper(),)
    ).fetchall()
    return sum((Decimal(row[0]) for row in rows), Decimal("0.00"))


def daily_revenue(conn: sqlite3.Connection, store_id: str) -> list[tuple[str, Decimal]]:
    rows = conn.execute(
        "SELECT txn_date, net_amount FROM sales WHERE store_id = ? ORDER BY txn_date",
        (store_id.upper(),),
    ).fetchall()
    totals: dict[str, Decimal] = {}
    for txn_date, net in rows:
        totals[txn_date] = totals.get(txn_date, Decimal("0.00")) + Decimal(net)
    return sorted(totals.items())


def all_store_totals(conn: sqlite3.Connection) -> list[tuple[str, Decimal]]:
    rows = conn.execute("SELECT DISTINCT store_id FROM sales ORDER BY store_id").fetchall()
    return [(row[0], store_total(conn, row[0])) for row in rows]

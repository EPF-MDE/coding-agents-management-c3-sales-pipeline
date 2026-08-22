"""Turn raw exporter rows into clean sales records."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from .ingest import RawRow
from .parse import ZERO, parse_amount, parse_date, parse_quantity

CENT = Decimal("0.01")


@dataclass(frozen=True)
class SaleRecord:
    source: str
    txn_id: str
    store_id: str
    txn_date: date
    gross_amount: Decimal
    quantity: int
    discount_pct: Decimal
    net_amount: Decimal


def _discount(raw: str) -> Decimal:
    if not raw or not raw.strip():
        return ZERO
    return parse_amount(raw)


def normalise(row: RawRow) -> SaleRecord:
    gross = parse_amount(row.amount)
    discount_pct = _discount(row.discount_pct)
    factor = (Decimal("100") - discount_pct) / Decimal("100")
    net = (gross * factor).quantize(CENT, rounding=ROUND_HALF_UP)
    return SaleRecord(
        source=row.source,
        txn_id=row.txn_id,
        store_id=row.store_id.strip().upper(),
        txn_date=parse_date(row.txn_date),
        gross_amount=gross,
        quantity=parse_quantity(row.quantity),
        discount_pct=discount_pct,
        net_amount=net,
    )


def transform_all(rows: list[RawRow]) -> list[SaleRecord]:
    return [normalise(row) for row in rows]

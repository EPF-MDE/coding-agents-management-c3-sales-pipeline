from datetime import date
from decimal import Decimal

from pipeline.ingest import RawRow
from pipeline.transform import normalise


def raw(**overrides):
    fields = dict(
        source="test",
        txn_id="T-1",
        store_id="s-001",
        txn_date="2026-08-14",
        amount="100.00",
        quantity="2",
        discount_pct="",
    )
    fields.update(overrides)
    return RawRow(**fields)


def test_store_id_is_normalised():
    assert normalise(raw(store_id=" s-001 ")).store_id == "S-001"


def test_no_discount_leaves_amount_untouched():
    record = normalise(raw(discount_pct=""))
    assert record.net_amount == Decimal("100.00")


def test_discount_is_applied():
    record = normalise(raw(amount="200.00", discount_pct="10"))
    assert record.net_amount == Decimal("180.00")


def test_discount_rounds_to_the_cent():
    record = normalise(raw(amount="99.99", discount_pct="15"))
    assert record.net_amount == Decimal("84.99")


def test_date_is_parsed():
    assert normalise(raw()).txn_date == date(2026, 8, 14)

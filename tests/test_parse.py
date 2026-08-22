from datetime import date
from decimal import Decimal

from pipeline.parse import parse_amount, parse_date, parse_quantity


def test_parses_decimal_point():
    assert parse_amount("42.50") == Decimal("42.50")


def test_parses_decimal_comma():
    assert parse_amount("42,50") == Decimal("42.50")


def test_parses_negative_refund():
    assert parse_amount("-8.00") == Decimal("-8.00")


def test_strips_surrounding_whitespace():
    assert parse_amount("  19.99  ") == Decimal("19.99")


def test_unparseable_amount_becomes_zero():
    assert parse_amount("n/a") == Decimal("0.00")
    assert parse_amount("") == Decimal("0.00")
    assert parse_amount(None) == Decimal("0.00")


def test_parses_iso_date():
    assert parse_date("2026-08-14") == date(2026, 8, 14)


def test_parses_european_date():
    assert parse_date("14/08/2026") == date(2026, 8, 14)


def test_blank_quantity_defaults_to_one():
    assert parse_quantity("") == 1
    assert parse_quantity("3") == 3

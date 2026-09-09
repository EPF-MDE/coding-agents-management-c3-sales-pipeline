from decimal import Decimal
from pipeline.parse import parse_amount


def test_amount_with_space_thousands_separator():
    # Le partenaire exporte parfois "1 321,49" (espace = séparateur de milliers)
    assert parse_amount("1 321,49") == Decimal("1321.49")

from decimal import Decimal
import re

_AMOUNT_RE = re.compile(r"[-+]?[0-9]+(?:[.,][0-9]{1,2})?")

def parse_amount(raw: str) -> Decimal:
    if raw is None:
        return Decimal("0.00")
    match = _AMOUNT_RE.search(raw.strip())
    if match is None:
        return Decimal("0.00")
    return Decimal(match.group(0).replace(",", "."))

# Test cases from the actual CSV
test_values = [
    "91,83",
    "32,02",
    "153,13",
    "109,46",
    "100.00",
    "42.50",
    "42,50"
]

for val in test_values:
    try:
        result = parse_amount(val)
        print(f"Input: {val:10} -> Result: {result}")
    except Exception as e:
        print(f"Input: {val:10} -> Failed with: {e}")

# Diagnosis — store S-014 August revenue is ~6 200 € short

## The command that goes red

```
python -m pytest tests/test_s014_reconciliation.py -q
```

Run against the original code it fails:

- `test_s014_reconciles_to_hand_computed_total` → `Decimal('618.94') != Decimal('4849.90')`
- `test_parse_amount_keeps_the_grouped_value` → `parse_amount('1\xa0000,00') == Decimal('1')`

Run against the fixed code it passes (3 passed). It will be run live in the oral.

## Cause

In the input data of S-014, numbers are encoded in an European format : "1 234,56"
Thousands are grouped with a space, this created a truncation error in 'parse_amount()'.

## Where the finding belongs

In 'parse.py', we can found
```
# Amounts arrive in a few shapes depending on the exporter:
#   "42.50"      POS terminals (US-style decimal point)
#   "42,50"      partner exports (European decimal comma)

#   "-8.00"      refunds
```

Documentation allow the European shape but don't think about the thousands grouped with a space. This is a specification error. But in addition, the function 'parse_amount()' truncate the value without raising an error. So structure of the code should also be corrected.

## Did this take more than 1h30?

It tooks me 2 hours to clearly understand. But in 30 minutes it could be finish with the skills 'diagnosing-bugs'.

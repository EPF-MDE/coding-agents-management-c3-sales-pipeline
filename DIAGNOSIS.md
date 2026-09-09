## 1. One command that goes red on this bug.

```bash
python -m pipeline --db test.db run

# 2. Verify the total for S-014
python -m pipeline --db test.db totals
# → S-014  50043.47   (should be 56232.09)

# 3. Verify the parsing of an isolated amount
python -c "from pipeline.parse import parse_amount; print(parse_amount('1\xa0321,49'))"
# → 1   (should be 1321.49)
```

## 2. The cause


| File | Role in the bug |
|---------|-----------------|
| `parse.py` | **Root cause** — the `_AMOUNT_RE` regex and the `parse_amount()` function |
| `partner_export_2026-08.csv` | Source data containing amounts with a thousands separator |
| `test_parse.py` | No test covering amounts ≥ 1,000 with a separator |

The `transform.py`, `load.py`, `report.py`, and `ingest.py` modules are working correctly — the bug is isolated to the parsing logic.

In `parse.py` L21, the regex:

```python
_AMOUNT_RE = re.compile(r"[-+]?[0-9]+(?:[.,][0-9]{1,2})?")
```

When it encounters `"1\xa0321,49"`:
1. It matches the **first group of digits**: `1`
2. After the `1`, there is `\xa0` (non-breaking space), which is not part of `[0-9]` or `[.,]`
3. The regex stops matching → returns `Decimal("1")`
4. The remainder (`321,49`) is silently ignored


## 3. The fix

### Modification 1: `parse_amount()` in `parse.py`

**Before** applying the regex, remove known thousands separators from the string:

```python
def parse_amount(raw: str) -> Decimal:
    if raw is None:
        return ZERO
    cleaned = raw.strip()
    # Strip thousands separators: non-breaking space (U+00A0),
    # narrow no-break space (U+202F), regular space, underscore
    cleaned = re.sub(r"[\xa0\u202f\s_]", "", cleaned)
    match = _AMOUNT_RE.search(cleaned)
    if match is None:
        return ZERO
    return Decimal(match.group(0).replace(",", "."))
```

## 4. The regression test

```python
def test_s014_total_matches_finance(tmp_path):
    """Regression test: S-014 total must match the reconciled figure."""
    _, _, _, conn = run(tmp_path)
    total = report.store_total(conn, "S-014")
    assert total == Decimal("56232.09")
```

## 5. One sentence on where the finding belongs

This finding belongs in the specification: the exact format of the partner's financial data, including the use of non-breaking spaces as thousands separators, should have been strictly defined in the initial data contract.

## 6. One line: did this take you more than 1h30? 

YES, it took me around 3 hours.
# Diagnosis: S-014 revenue mismatch (BUG-REPORT.md)

## How I found it

Started with the report itself, because it's already done half the work:
count matches, so no rows are missing; it's "a little low" on most days
rather than wrong on one day, so it's not a one-off bad record; and no
errors or alerts fired, so whatever it is fails silently rather than
crashing. That combination — quietly wrong, spread out, never loud — smells
like a parsing issue, not a missing-data or dedup issue.

The README lays out the pipeline as ingest → parse → transform → load →
report, and says explicitly that `parse` is "where [format differences]
get reconciled" for the partner exporter that S-014 sits on. That's the
obvious first place to look, so I read `parse.py` before anything else.

`parse_amount` handles `"42.50"` and `"42,50"` — US point and European
comma. Fine for typical amounts, but I didn't trust it yet, so instead of
reasoning about the regex in my head I went and looked at the actual data
for S-014 (`data/raw/partner_export_2026-08.csv`).

I tried to just sum the raw `amount` column in Python as a sanity check —
`Decimal(amt.replace(',', '.'))` — and it threw `InvalidOperation` on one
of the rows. That crash was the real lead: something in that column isn't
a clean number at all. I printed the offending rows and got things like:

```
{'amount': '1\xa0321,49', ...}
```

`\xa0` — a non-breaking space, invisible in a normal terminal or editor,
used as a thousands separator. Five rows had it, all four-digit amounts.
That's when it clicked: the regex has no concept of a thousands separator,
only a decimal one. I traced `_AMOUNT_RE` by hand against `"1\xa0321,49"`
and confirmed it stops at the first non-digit character it doesn't
recognize, matching just `"1"` and quietly dropping the rest — no error,
because `re.search` only needs to find *a* match, not consume the whole
string.

At that point I had a plausible culprit but wanted proof, not a hunch, so
I wrote a regression test reproducing exactly that string and ran it
against the unmodified code — it failed exactly as predicted
(`Decimal('1')` instead of `Decimal('1321.49')`). Then I recomputed
S-014's full August total from the raw CSV two ways — once with the buggy
parser, once with a fix that strips the separator first — and compared
both to the two numbers in Claire's report. They matched to the cent on
both sides, which is what moved this from "likely cause" to "confirmed
root cause."

## Root cause

`parse_amount()` in [`src/pipeline/parse.py`](src/pipeline/parse.py) cannot handle
the thousands separator used by the partner exporter.

```python
_AMOUNT_RE = re.compile(r"[-+]?[0-9]+(?:[.,][0-9]{1,2})?")

def parse_amount(raw: str) -> Decimal:
    if raw is None:
        return ZERO
    match = _AMOUNT_RE.search(raw.strip())
    if match is None:
        return ZERO
    return Decimal(match.group(0).replace(",", "."))
```

`partner_export_2026-08.csv` (store S-014's only source) writes amounts over
1000 in French formatting: a non-breaking space (`\xa0`) as the thousands
separator and a comma as the decimal separator, e.g. `"1 321,49"` for
€1,321.49. The regex only knows the two documented formats, `"42.50"` and
`"42,50"` — it has no concept of a thousands separator.

`re.search` returns the *first* match, not a full-string match. Walking
`"1\xa0321,49"`:

1. `[0-9]+` greedily consumes `"1"`, then stops at `\xa0` (not a digit).
2. The optional `(?:[.,][0-9]{1,2})?` group looks at `\xa0` next — not `.`
   or `,` — so it doesn't match either.
3. The overall match is just `"1"`.

So `parse_amount("1\xa0321,49")` returns `Decimal("1")` instead of
`Decimal("1321.49")`. Everything after the separator is silently discarded.
No exception is raised, no row is dropped, nothing logs — the regex always
finds *some* match.

## Why it explains every symptom in the report

| Report says | Why |
| --- | --- |
| Only S-014 is wrong | S-014 is the only store on the partner exporter; POS exports don't use this format |
| Transaction count matches (420) | Each row is still ingested — only the *amount* is wrong, not the row count |
| Most days a little low, a few exact | Only days with a ≥1000 transaction are affected |
| No errors, no alerts | The regex always matches something (`"1"` counts), so parsing never fails loudly |
| Pipeline figure is *lower* than finance's | Truncating `1321.49` down to `1` only ever loses money |

Five transactions in the file trigger this: `P-00219`, `P-00272`, `P-00275`,
`P-00298`, `P-00314` — all ≥ €1000.

## Reproduction (red)

A regression test was added at
[`tests/test_parse.py::test_parses_thousands_separator_nbsp`](tests/test_parse.py):

```python
def test_parses_thousands_separator_nbsp():
    assert parse_amount("1\xa0321,49") == Decimal("1321.49")
```

Run it against the current (unfixed) code:

```bash
pytest tests/test_parse.py::test_parses_thousands_separator_nbsp -v
```

Fails on original code:

```
AssertionError: assert Decimal('1') == Decimal('1321.49')
 +  where Decimal('1') = parse_amount('1\xa0321,49')
```

## Verified against the actual figures

Recomputing S-014's August total directly from
`data/raw/partner_export_2026-08.csv`, applying the existing discount logic
from `transform.py`:

- **Buggy `parse_amount`** → store total **50,043.47 €** — matches the
  pipeline's reported (wrong) figure exactly.
- **Fixed `parse_amount`** (thousands separator stripped before matching) →
  store total **56,232.09 €** — matches Claire's finance-reconciled figure
  exactly.

This is the entire discrepancy, not a partial contributor.

## Fix

Strip the space/non-breaking-space thousands separator out of the amount
string before matching, in `parse_amount`:

```python
_THOUSANDS_SEP_RE = re.compile(r"(?<=[0-9])[\s\xa0](?=[0-9]{3}\b)")
_AMOUNT_RE = re.compile(r"[-+]?[0-9]+(?:[.,][0-9]{1,2})?")

def parse_amount(raw: str) -> Decimal:
    if raw is None:
        return ZERO
    cleaned = _THOUSANDS_SEP_RE.sub("", raw.strip())
    match = _AMOUNT_RE.search(cleaned)
    if match is None:
        return ZERO
    return Decimal(match.group(0).replace(",", "."))
```

After applying the fix, the same command turns green:

```bash
pytest tests/test_parse.py::test_parses_thousands_separator_nbsp -v
```

```
tests/test_parse.py::test_parses_thousands_separator_nbsp PASSED
```

## Where this finding belongs

This is a code-structure defect, not a spec or documentation gap: the amount format is correctly identified as `parse.py`'s job by both the README and the code's own comment block, and that comment already lists exactly which formats it must accept — the regex underneath it just doesn't implement one of them.

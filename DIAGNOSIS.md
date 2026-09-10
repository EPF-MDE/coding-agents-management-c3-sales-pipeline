# DIAGNOSIS — S-014 August revenue shortfall

## The one command that goes red

```bash
pytest tests/test_s014_regression.py -q
```

On the original code (4 tests, 3 fail):

```
E   AssertionError: assert Decimal('50043.47') == Decimal('56232.09')
FAILED tests/test_s014_regression.py::test_parse_amount_handles_nbsp_thousands_separator
FAILED tests/test_s014_regression.py::test_parse_amount_handles_other_grouping_shapes
FAILED tests/test_s014_regression.py::test_s014_august_total_matches_finance
3 failed, 1 passed
```

It reproduces Claire's two numbers exactly — `50043.47` computed vs `56232.09`
expected — end to end over the real `data/raw/` exports, through
ingest → transform → load → report.

After the fix: `21 passed` (the 17 original tests plus the 4 new ones).

## The cause

The franchise partner writes thousands with a **NO-BREAK SPACE** (U+00A0):
`"1 321,49"`. `parse_amount`'s regex was `[-+]?[0-9]+(?:[.,][0-9]{1,2})?`, which
has no case for a grouping separator, so `re.search` matched only the leading
`1` and returned `Decimal("1")` — silently, because unparseable amounts are
designed to degrade to zero rather than crash the nightly run. Five of S-014's
420 August rows are four figures, so only those five are wrong and the
transaction count is untouched.

What pointed me at it: Claire's "count is right, amount is low" ruled out
ingestion and de-duplication, so the loss had to be per-row and inside a value.
Diffing the partner CSV against the shape the POS files use
(`grep -vP '^[A-Z]-\d+,S-\d+,\d{4}-\d\d-\d\d,"\d+,\d\d",\d+,\d*$'`) surfaced
exactly five odd rows, all four-figure; `od -c` showed the separator was
`\xc2\xa0`, not a space. The arithmetic then closed the loop: summing the five
truncations after discount gives **6 188,62 €**, which is `56232.09 − 50043.47`
to the cent. One cause, whole discrepancy accounted for.

## What it ruled out

- **Missing or duplicated rows** — 420 records for S-014 both before and after;
  `load` reports 0 duplicates skipped over 2080 rows.
- **The other two source files / the whole report** — `pipeline totals` before
  and after the fix differs on S-014 only; the other thirteen stores are
  byte-identical.
- **The discount maths** — `normalise` applies `(100 - pct)/100` with
  `ROUND_HALF_UP` to the cent; rows with a blank discount and rows with 10/15 %
  are wrong by the same *gross* mechanism, and rows under 1 000 € are exact.
- **Rounding / float drift** — everything is `Decimal` from `parse` to `report`;
  the gap is 6 188,62 €, not cents.
- **Date parsing and the month boundary** — all partner dates are ISO
  `2026-08-xx`; the daily breakdown has the right days, five of them low.
- **`store_id` casing / whitespace, and the SQLite `TEXT` round-trip** —
  `store_total` re-reads the same `Decimal` strings it wrote.
- **The decimal comma itself** — `"91,83"` already parsed correctly; the comma
  was never the problem, the space was.

## The fix

`src/pipeline/parse.py`: strip grouping separators (U+0020, U+00A0, U+202F,
U+2009, U+2007, `'`, U+2019) before matching, widen the regex to accept repeated
separator groups, and normalise the token in `_to_decimal_text` — the last `.`
or `,` is the decimal separator when it is followed by one or two digits, every
other one groups thousands. `"1 321,49" → 1321.49`, `"1.234,56" → 1234.56`,
`"1,234.56" → 1234.56`, while `"42.50"`, `"42,50"`, `"-8.00"`, `""` and `"n/a"`
behave exactly as before.

## Regression test

`tests/test_s014_regression.py`. Watched it fail on the original code by
`git stash push src/pipeline/parse.py`, re-running (3 failed), then
`git stash pop` (21 passed). Two unit tests pin the NBSP and the other grouping
shapes, one pins the shapes that already worked, and one end-to-end test pins
S-014's August total at 56 232,09 € over the real exports.

## Where the finding belongs

The specification: "the partner exports in its own regional format" was never
written down as a concrete list of accepted number shapes, so `parse_amount`
encoded one guess about that format and the silent zero-fallback removed every
signal that the guess was wrong — the fix is a stated input contract per
exporter, and a parse that reports rather than swallows what it cannot read.

## Did this take more than 1h30?

No.

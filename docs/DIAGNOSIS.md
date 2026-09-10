# Command that goes red

`python3 -c "
import sys; sys.path.insert(0, 'src')
from decimal import Decimal
from pipeline.parse import parse_amount

assert parse_amount('1\xa0321,49') == Decimal('1321.49')
"`

This rules out:

- Not a test-mock artifact — it runs against the real August CSVs.
- Not a reporting/aggregation bug — load and report execute normally. The wrong total comes out of the same SQL/aggregation path that produces every other (correct) store's total.
- Not something already fixed — confirms the bug is still live on main right now, not stale from an earlier session.

# The cause

`pipeline.parse.parse_amount`'s regex (`_AMOUNT_RE`) doesn't strip grouping separators, and
silently accepts a **partial** match as if it were the whole number. The partner export (store
S-014 only) writes amounts of 1000 or more with a non-breaking-space grouping separator ahead of
the decimal comma (e.g. `"1\xa0321,49"`), so `re.search` matches only the leading `"1"` — the
rest of the digits are dropped with no error and no warning.

5 of 420 S-014 transactions have this shape. Recomputing just those 5 with the grouping
separator stripped changes the reported August total from `50043.47` to `56232.09` — an exact
cent match to finance's reconciled figure. Other candidate causes (date parsing, rounding mode,
quantity-as-multiplier, duplicate transactions) were checked against the real fixture data and
ruled out; see `docs/SPEC.md` for that analysis.

# The fix

In `src/pipeline/parse.py::parse_amount`:

1. Strip whitespace-family grouping separators (regular space, non-breaking space) from the raw
   string before matching.
2. Require the match to span the entire cleaned string. A match that doesn't now logs a warning
   and falls back to `Decimal("0.00")` instead of being silently trusted — closing the underlying
   "partial match treated as complete" bug, not just this one string shape.

Verified: `tests/test_parse.py` and `tests/test_pipeline.py` cover both the grouping-separator
case and the partial-match/warning case, the full suite is green, and `python -m pipeline
totals` reports `S-014  56232.09`.

# One sentence on where the finding belongs

The full root-cause writeup, ruled-out causes, and unit breakdown live in `docs/SPEC.md`.

# Time consumption

I took me more than 1h30

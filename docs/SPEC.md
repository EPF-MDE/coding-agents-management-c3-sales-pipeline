# Spec: S-014 monthly revenue mismatch

Resolves [`BUG-REPORT.md`](../BUG-REPORT.md).

## Symptom

Claire (Finance) reports the August monthly total for store S-014 as **50 043,47 €** in our
report vs **56 232,09 €** reconciled against till receipts. Transaction count matches (420 = 420).
Every other store matches to the cent. No errors, no alerts.

## Root cause

`pipeline.parse.parse_amount` matches amounts with:

```python
_AMOUNT_RE = re.compile(r"[-+]?[0-9]+(?:[.,][0-9]{1,2})?")
```

This assumes an amount has at most one separator character, which is always the decimal
separator. `data/raw/partner_export_2026-08.csv` (the franchise partner's own export, store
S-014 only) writes amounts of 1000 or more with a **grouping separator** — a non-breaking space
(U+00A0) between digit groups — ahead of the decimal comma, e.g. `"1\xa0321,49"` for 1321.49.

`re.search` on that string matches only `"1"`: `[0-9]+` stops at the non-breaking space, and the
optional decimal group never gets a chance to match because the next character isn't `.` or `,`.
The function doesn't raise or zero out — it silently returns `Decimal("1")`, i.e. the amount is
truncated to its leading digit(s) and treated as fully parsed.

Confirmed against the fixture data: 5 of 420 partner rows have this shape.

| txn_id | raw amount | discount | parsed today | should be |
|---|---|---|---|---|
| P-00219 | `1\xa0321,49` | 0% | 1.00 | 1321.49 |
| P-00272 | `1\xa0613,17` | 0% (blank) | 1.00 | 1613.17 |
| P-00275 | `1\xa0197,00` | 15% | 0.85 | 1017.45 |
| P-00298 | `1\xa0070,51` | 10% | 0.90 | 963.46 |
| P-00314 | `1\xa0503,12` | 15% | 0.85 | 1277.65 |

Recomputing the S-014 total with only these 5 amounts parsed correctly — no other change —
turns `50043.47` into `56232.09`. That is an **exact cent match** to Claire's reconciled figure.
This is the whole bug: one bug, five rows, one exporter, one store.

### Ruled out

Because Claire also noted "most days a little low, a few exactly right" — a pattern that
doesn't obviously fit "5 of 31 days affected, each by a large amount" — the following were
each checked directly against the S-014 fixture data and ruled out as contributing causes:

- **Date parsing / day-shifting**: all 420 partner rows use ISO dates (`YYYY-MM-DD`); none use
  the ambiguous `DD/MM/YYYY` form `parse_date` also accepts. No row can land on the wrong day.
- **Rounding mode**: per-transaction `ROUND_HALF_UP` (current behavior) is the only rounding
  strategy tested — vs. `ROUND_HALF_EVEN`, vs. summing unrounded and rounding once per day —
  that reproduces `56232.09` exactly. The existing rounding approach is correct, not a bug.
- **Amount format**: every row matches a simple `-?[digits/grouping-sep]+,[0-9]{2}` shape except
  the 5 above. No parenthesized negatives, currency symbols, or refunds in S-014 at all.
- **Quantity-as-multiplier**: if `amount` were a per-unit price needing `× quantity`, fixing only
  the 5 grouping-separator rows would not have landed on the exact reconciled total. It does, so
  `amount` is correctly already a line total.
- **Duplicates / identifiers**: 420 unique `txn_id`s, one consistent `store_id`, full existing
  test suite passes on current `main`.

Conclusion: treat the cent-exact reconciliation as decisive. Claire's day-by-day impression is
an approximation from skimming a breakdown, not evidence of a second bug — worth saying plainly
back to her, not silently smoothing over.

## Fix

**Scope**: general but bounded. `pipeline.parse` exists because "source systems disagree about
formatting" (see `README.md`) — grouping separators are a plausible failure mode for any future
exporter, not just this one. Fix the underlying gap in `parse_amount`, not just this one string
shape. Do **not** introduce a per-exporter format table or any new "numeric locale" concept on
`RawRow` — that's more architecture than this bug justifies (see [Domain notes](#domain-notes)).

1. **Strip grouping separators before matching.** Remove whitespace characters — regular space,
   non-breaking space (U+00A0), and other Unicode whitespace — from the raw string before running
   `_AMOUNT_RE` against it. This turns `"1\xa0321,49"` into `"1321,49"`, which the existing regex
   already parses correctly. The decimal separator (`.` or `,`) is untouched.

2. **Stop trusting partial matches.** Today, a match that doesn't cover the whole (cleaned)
   string is silently accepted as if it were complete — that's the actual mechanism of this bug,
   not just the specific NBSP case. After cleaning, require the match to span the entire string.
   If it doesn't:
   - log a warning (stdlib `logging`; not currently used in this codebase — add a module logger
     in `parse.py`) including the raw and cleaned values, so a future case like this shows up in
     run output instead of silently mispricing a store.
   - fall back to `Decimal("0.00")`, same as the existing fully-unparseable path.

   Fully-unparseable input (`"n/a"`, `""`, `None`) keeps returning `0.00` silently, as today —
   that contract ("never crash the nightly run" on genuinely empty/garbage input) is unchanged.
   The new behavior only fires for the previously-unhandled case: *something* matched, but not
   *everything*.

3. **No signature changes.** `parse_amount(raw: str) -> Decimal` keeps its current signature.
   The warning logs the value being parsed, not caller/row context (store, txn_id) — plumbing
   that through would touch `ingest`/`transform` call sites for a case that, once (1) is fixed,
   the current fixture data no longer even exercises. If a future occurrence needs richer
   context to debug, that's a follow-up, not part of this fix.

## Domain notes

Added to `CONTEXT.md`: **grouping separator** (the concept this bug turned on) as distinct from
**decimal separator**, plus **exporter** for the existing-but-unwritten term for a source system.
No ADR: this is a bug fix with a small, reversible logging addition, not an architectural
decision — there's no real trade-off to record.

## Verification (red → green)

Following the project's existing test structure (`tests/test_parse.py` for field-level parsing,
`tests/test_pipeline.py` for end-to-end fixture checks):

1. **Tight red signal** — `tests/test_parse.py`, calling `parse_amount` directly with the real
   offending string:
   ```python
   def test_parses_amount_with_grouping_separator():
       assert parse_amount("1\xa0321,49") == Decimal("1321.49")
   ```
   Fails today (`parse_amount("1\xa0321,49") == Decimal("1")`). No I/O, fastest loop — use this
   while implementing fix step 1.

2. **Partial-match safety net** — `tests/test_parse.py`, a synthetic malformed value that isn't
   fixed by grouping-separator stripping (e.g. a stray trailing character: `"42,50 kr"` already
   passes today by luck since the regex just ignores trailing junk — use something that produces
   a genuine partial match after cleaning, e.g. `"42,5,0"`), asserting it returns `0.00` and
   that a warning was logged (`caplog`). Exercises fix step 2.

3. **Regression guard tied to the incident** — `tests/test_pipeline.py`, run over the real
   `data/raw/` fixture:
   ```python
   def test_s014_total_matches_finance_reconciliation(tmp_path):
       _, _, _, conn = run(tmp_path)
       assert report.store_total(conn, "S-014") == Decimal("56232.09")
   ```
   Fails today (`50043.47`). This is a CLI/fixture-diff-style check against a known-good number
   — the one Claire already hand-verified — so this exact incident can't silently regress.

## Deploy note

`pipeline.load.load` uses `INSERT OR REPLACE` keyed on `(store_id, txn_id)` (`load.py:50`), so no
migration script is needed. After the fix ships, re-running `python -m pipeline run` recomputes
and overwrites every row, including the 5 previously-truncated ones. Not a unit of work — just
an operational step to call out when this ships.

## Units of work

1. **Write the failing tests** (verification items 1–3 above). All three should fail against
   current `main` before any production code changes. This is the red signal.
2. **Fix `parse_amount`: strip grouping separators.** Implements fix step 1. Turns verification
   items 1 and 3 green.
3. **Fix `parse_amount`: partial-match warning + zero-fallback.** Implements fix step 2. Turns
   verification item 2 green. Independent of unit 2 — can be built and tested in isolation using
   any string that produces a partial match after whitespace-stripping.
4. **Ship + deploy note.** Re-run `python -m pipeline run` against production `data/raw/` and
   confirm `python -m pipeline totals` / `python -m pipeline report --store S-014` reflect
   `56232.09`. Reply to Claire with the reconciliation and the caveat about the day-by-day
   pattern (see [Ruled out](#ruled-out)).

## Out of scope

- Per-exporter numeric-format metadata / "locale" concept (ruled out, see Fix scope above).
- Any change to rounding mode or rounding granularity (verified correct as-is).
- Any change to date parsing, quantity handling, or dedup keying (all verified correct for
  this data).
- An ADR (no architectural decision made).

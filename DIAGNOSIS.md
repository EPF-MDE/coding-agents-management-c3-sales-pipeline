# Diagnosis — S-014 monthly revenue shortfall

Re: [`BUG-REPORT.md`](BUG-REPORT.md) — reported total 50 043,47 €, finance 56 232,09 €, gap **6 188,62 €**.

## The one command

```bash
pytest tests/test_bug_s014.py -v
```

- On the original code: **10 failed, 4 passed**.
  Headline: `AssertionError: assert Decimal('50043.47') == Decimal('56232.09')`
- With the fix: **14 passed**. Full suite: **31 passed**.

## The cause

`pipeline.parse.parse_amount` had no notion of a thousands separator, and it used
`re.search()` rather than a full match — so when a field did not fit its pattern it
returned the longest prefix that did, instead of failing. The partner exporter groups
thousands with U+00A0 NO-BREAK SPACE (`'1\xa0321,49'`), which `str.strip()` does not
remove from the middle of a field and which the pattern could not cross, so five
transactions in `partner_export_2026-08.csv` were read as `Decimal('1')` instead of their
true value. Nothing raised, because a truncated parse does not look like a failure — it
looks like a small sale.

**What pointed at it.** After ruling out everything downstream (below), the money had to
be going missing at the point where a raw string becomes a number. I ran a round-trip
audit over all 2 080 raw rows, asking a question that needs no knowledge of the right
answer: *does the regex consume the entire amount field, or only part of it?* Five rows
came back partial — all five in S-014 — and a character census of the amount column across
every file showed exactly one non-digit character that had no business being there:
U+00A0, appearing 5 times.

| txn_id | date | raw field | parsed as | true value |
| --- | --- | --- | --- | --- |
| P-00219 | 2026-08-06 | `1\xa0321,49` | 1 | 1 321,49 |
| P-00272 | 2026-08-12 | `1\xa0613,17` | 1 | 1 613,17 |
| P-00275 | 2026-08-14 | `1\xa0197,00` | 1 | 1 197,00 |
| P-00298 | 2026-08-07 | `1\xa0070,51` | 1 | 1 070,51 |
| P-00314 | 2026-08-28 | `1\xa0503,12` | 1 | 1 503,12 |

**The check that could have refuted this.** If these five rows were the whole cause,
correcting only them must close the gap to *exactly* zero — "nearly right" would mean a
second bug. Correcting only them gives 56 232,09 €, residual **0.00**.

## What it ruled out

Each of these was eliminated by evidence, before the cause was known:

| Hypothesis | Evidence against it |
| --- | --- |
| Rows dropped on ingest | 420 raw rows for S-014, 420 records, 420 in the DB. Matches finance's count. |
| De-duplication discarding rows | `duplicates_skipped == 0` over all 2 080 rows. |
| SQLite storage / float precision | Total *before* the DB (50 043,47) is identical to the total read back out. The DB is not in the path. |
| Report query or `store_id` filtering | Same total in memory and through `report.store_total`; count is correct. |
| Rows landing outside August | All 420 dates are in 2026-08, spread over 31 distinct days. |
| Rounding at the cent | Worst case 0,005 × 420 = **2,10 €**. The gap is 6 188,62 €. Three orders of magnitude out. |
| The discount being misapplied | **Decisive**: gross before any discount is 52 448,67 €, which is *already below* finance's 56 232,09 €. No discount error can produce a total larger than gross, so the error is upstream of the discount, in the amounts themselves. |
| Refunds / sign errors | No negative and no zero amounts in S-014. |
| European decimal comma handled wrongly in general | 415 of 420 partner rows parse correctly. It is not the comma. |
| A whole-report bug | Only S-014 is wrong, and only S-014 comes from `partner_export`. The other 13 stores are unchanged to the cent by the fix. |

One detail in the report is misleading and worth naming: Claire writes that "most days are
a little low, a few are exactly right". The data says the opposite — **5 days are badly
low and the other 26 are exact**. Taken at face value, that sentence points at a small
systematic error on every row (rounding, discount, a rate) and leads away from the cause.
It is an honest impression from someone reading a column of near-matching numbers, not a
measurement.

## The fix

`src/pipeline/parse.py`. Two anchored patterns instead of one loose one — an amount either
groups its thousands or it does not — and `fullmatch()` in place of `search()`:

- Grouping may be `.`, `,`, or a space character (plain, NO-BREAK, NARROW NO-BREAK, THIN,
  FIGURE). Three digits after a separator are a thousands group; one or two are the decimal
  part. Where both a grouping and a decimal separator appear, the last one is the decimal.
- A field that is not fully matched is no longer *partly* parsed. `n/a`, `""` and `None`
  still yield `0.00` as before, so the nightly run still cannot crash on bad input — but a
  value we understand only in part can no longer become a plausible number.

## The regression test

`tests/test_bug_s014.py`, four tests:

1. `test_s014_august_total_matches_finance` — the symptom end to end, against the real
   fixture data, asserting finance's 56 232,09 €. This is the test I could write at minute
   ten, knowing nothing about the cause.
2. `test_no_amount_field_is_only_partly_understood` — the round-trip audit, kept as a test:
   no amount in the raw exports may lose digits in parsing.
3. `test_thousands_separators_are_not_truncated` — the cause, at unit level, across NBSP,
   plain-space, EU-dot and US-comma grouping, plus the existing formats to prove they still
   work.
4. `test_a_partial_parse_is_refused_rather_than_truncated` — the structural defect itself.
   `"n/a 99"` used to parse as `99`.

**Verified red, not assumed red.** `git stash push src/pipeline/parse.py` with the tests
left in place, re-ran: 10 failed, 4 passed. `git stash pop`: 31 passed. Both directions
observed, not inferred.

Note that the original suite passes on the buggy code — 17 tests, all green, all month.
It asserts structure (row counts, 14 stores, 31 days, `total > 0`) and never once asserts
a value, so a 1 321,49 € sale collapsing to 1 € satisfies every one of them.

## Where the finding belongs

The finding belongs in the **specification**: the number formats the partner exporter is
permitted to emit were never written down anywhere, so `pipeline.parse` encoded an
assumption that no reviewer could check against a stated contract — the regex is a faithful
implementation of the three shapes listed in its own docstring, and the docstring was the
only place the input contract existed.

## Time

Did this take more than 1h30? <!-- TODO: your answer, Yes or No -->

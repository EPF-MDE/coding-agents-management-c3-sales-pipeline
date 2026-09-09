# DIAGNOSIS.md

## Cause

`parse.parse_amount` matched its amount regex (`_AMOUNT_RE`) against the raw
field with `.search()` and no thousands-separator handling. The partner
exporter (`data/raw/partner_export_2026-08.csv`, store S-014 only) writes
amounts >= 1000 with a whitespace thousands separator, e.g. `"1\xa0321,49"`
(`\xa0` = non-breaking space). Against that string, `[0-9]+` greedily
consumes only the leading `"1"`, the optional decimal group fails to match
(next character is the space, not `.`/`,`), and `.search()` silently accepts
that shorter match — so the row parses as `Decimal("1")` instead of
`Decimal("1321.49")`, with no exception raised. What pointed at it: row count
matched exactly (420/420, ruling out ingest/load) and the shortfall was
non-uniform across days ("most days a little low, a few exactly right" per
the bug report) rather than proportional to a shared computation like
discount or rounding — which meant the mechanism had to be conditional on
something about specific rows, not a systemic transform bug. Dumping every
S-014 `amount` field and flagging non-numeric characters found exactly 5 rows
with a `\xa0` separator, all with values >= 1000; recomputing those 5 rows by
hand and summing (correct − buggy) across all 420 rows reproduced the
reported gap exactly: `6188.62`, matching `56232.09 − 50043.47` to the cent.

## Where the finding belongs

This belongs in the code's structure, specifically as a stricter contract in
`pipeline.parse` (the module `README.md` already designates as "the one
place US/partner formats are reconciled") — not in the specification or an
instruction document, because the defect is not a missing rule about what
formats to support (the partner's thousands-separator format was already
known and partially handled for the decimal-comma case) but an incomplete
implementation of a rule that already existed; the fix is a parsing
correctness fix, not a new requirement.

## Time taken

More than 1h30 counting my own environment/tooling setup; under 1h30 measured
from Ticket 0 (baseline) to this point in the exercise itself.

## Ruled out

| Candidate | Why ruled out |
| --- | --- |
| Ingest/load dropping or duplicating rows | `python -m pipeline run` reports 2080/2080 rows read/inserted, 0 duplicates skipped; direct query confirms 420 rows and 420 distinct `txn_id` for S-014, matching the source CSV's 420 data rows exactly. |
| Discount application wrong (applied twice, or as fraction not percent) | Would affect every discounted row proportionally to `discount_pct`, and would also affect POS stores via the same shared `transform` code path — but POS stores reconcile to the cent. Hand-checked several S-014 rows against `gross * (100 - disc) / 100`; all matched. |
| Rounding (`ROUND_HALF_UP` to the cent) | Maximum possible drift is 0.005 €/row × 420 rows ≈ 2.10 €, three orders of magnitude below the observed 6188.62 € gap. |
| Date-driven mis-bucketing (`parse_date`) | Ticket 1's failing assertion is on `store_total`, a date-independent sum; a bucketing bug could reshuffle the daily breakdown but could not change the total. |
| `parse_amount` mishandling decimal-comma format (`"42,50"`) on ordinary rows | Traced several plain comma-decimal values by hand through `_AMOUNT_RE`; all parsed correctly. This ruled out the *decimal* separator as the fault and narrowed the search to what differed on the handful of wrong rows — magnitude (>= 1000, needing a thousands separator) turned out to be it. |

Full evidence trail (row dumps, exact commands, intermediate hypotheses) is
in `NOTES.md`.

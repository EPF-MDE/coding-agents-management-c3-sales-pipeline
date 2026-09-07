# Diagnosis — S-014 August revenue mismatch

## Cause

The August 2026 report for store S-014 undercounts revenue by 6188.62 EUR because `parse_amount` (src/pipeline/parse.py) fails silently on amounts using a non-breaking-space thousands separator, which only `partner_export_2026-08.csv` (S-014's sole data source) uses. The regex stops at the first digit group, so a value like "1 321,49" (with that separator) parses as 1.00 instead of 1321.49 — a loss of exactly the delta reported, on exactly the 5 transactions ≥ 1000 EUR out of S-014's 420 August transactions.

What pointed at it: an independent recompute from the raw CSV (bypassing parse.py/transform.py entirely) reproduced Claire's exact delta without using her figure. Filtering S-014's transactions by attribute showed 100% of rows ≥ 1000 EUR were wrong and 0% of rows < 1000 EUR were wrong — discount presence did not correlate (4/234 with discount wrong vs 1/186 without), ruling that out before accepting the amount-size hypothesis.

## Where this finding belongs

The structure of the code — `parse_amount`'s regex needs to strip or accept the thousands separator used in this export format before matching, and the new regression test (tests/test_s014_regression.py) now guards this at the seam between raw ingestion and reporting, independent of any single store's format.

## Time

No — under 1h30.

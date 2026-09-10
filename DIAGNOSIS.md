# Diagnosis — S-014 August revenue mismatch

## Cause

S-014's August total undercounted revenue by exactly €6,188.62 because `parse_amount`
in `src/pipeline/parse.py` truncated any amount using a non-breaking-space thousands
separator (e.g. `"1\xa0321,49"`) at the first unrecognized character, silently
returning just the leading digit (`1`) instead of the full value. This only affected
the 5 transactions in `partner_export_2026-08.csv` above €1,000 — the only exporter
that formats large amounts this way, which is why no other store or file was
affected. The matching transaction count (420=420) and the fully-passing test suite
ruled out a missing-row bug and pointed toward a per-transaction parsing defect;
isolating the 5 highest-value transactions and comparing the pre-discount gross to
Claire's figure confirmed the amount, and a monkeypatch removing the separator
reproduced her exact total to the cent.

## The fix

`parse_amount` now strips both `\xa0` (non-breaking space) and ordinary spaces from
the raw string before matching, so grouped-thousands values like `"1 321,49"` parse
as `1321.49` instead of stopping at `1`. The change is a single added line; the
regex, the comma-to-dot conversion, and the `None`/no-match fallback are unchanged.

## Regression test

`tests/test_pipeline.py::test_s014_august_total_matches_finance` asserts S-014's
August total equals `Decimal("56232.09")` through the real ingest → transform → load
pipeline. Verified red on the original code (stashing the fix reproduces the original
`50043.47` failure) and green after the fix.

## Where this belongs

Structure of the code: `parse_amount` should fail loudly — raise, not silently return
a truncated value — whenever it cannot consume the entire cleaned string, because
relying on a written instruction to "remember to test edge cases" is exactly the kind
of non-deterministic safeguard that failed to catch this the first time.

## Time

About 1h, under the 1h30 budget.

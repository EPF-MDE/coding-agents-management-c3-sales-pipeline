# Diagnosis — S-014 monthly revenue mismatch

## Cause

`parse_amount` in `src/pipeline/parse.py` uses a regex
(`[-+]?[0-9]+(?:[.,][0-9]{1,2})?`) that does not recognise the non-breaking
space (`\xa0`) used as a thousands separator in the `partner_export` source
file (French format, e.g. `"1 321,49"` meaning 1321.49 euros). The regex
matches only the digits before the separator, so any amount of 1000 or
above is silently truncated (`"1 321,49"` → `1`) instead of raising an
error. S-014 is the only store fed by `partner_export_2026-08.csv`, which
is why it is the only one affected.

## What pointed me at it

The bug report ruled out missing rows and duplicates (transaction count
matched, `duplicates_skipped == 0`). Comparing `quantity` distributions
between `partner_export` and the POS sources ruled out the unused
`quantity` column as a cause, since POS sources ignore it too and are
unaffected. Manually re-running `python -m pipeline report --store S-014`
reproduced the exact buggy total (50043.47). Isolating failing rows during
manual parsing surfaced `ConversionSyntax` errors on values containing
`\xa0`, which directly pointed to the thousands-separator handling in
`parse_amount`.

## Ruled out

- Missing or duplicated transactions (count and dedup stats match).
- The discount formula itself (applied uniformly, other stores with
  discounts reconcile exactly).
- The unused `quantity` column (POS sources also ignore it and are correct).

## Where this finding belongs

This belongs in the code structure: `parse_amount`'s regex should be
extended to recognise thousands separators (space and non-breaking space),
which is what the fix does; it is not a specification or documentation gap,
since the module's own comment already anticipated multiple exporter
formats but missed this one.

## Time

Did this take more than 1h30: YES
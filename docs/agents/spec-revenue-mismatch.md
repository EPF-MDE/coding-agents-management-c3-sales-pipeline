# Specification: Fix Revenue Mismatch for Store S-014

## Problem Statement

The monthly revenue report for store S-014 is showing a total of 50,043.47 €, which does not match the expected financial total of 56,230.09 €. The transaction count is correct (420), indicating that all transactions are being processed, but the monetary values are being miscalculated.

## Solution

The solution involves identifying why the partner export format is being parsed or transformed incorrectly. The investigation will focus on whether the decimal separator (comma vs. dot) or other regional formatting in the `partner_export_2026-08.csv` file is causing the pipeline to misinterpret the transaction amounts.

## User Stories

1. As a finance officer, I want the monthly revenue report to be accurate for all stores, so that I can close the monthly books without discrepancies.
2. As a data engineer, I want the pipeline to robustly handle different regional number formats from various source systems, so that data integrity is maintained across all imports.
3. As a developer, I want a regression test in place, so that future changes to the parsing logic do not reintroduce this discrepancy.

## Implementation Decisions

- **Investigation of Parsing Logic**: Audit `src/pipeline/parse.py` to determine how numeric fields are being cast from strings. Specifically, check if the logic assumes a dot separator and fails to handle the comma separator used in the partner export.
- **Investigation of Transformation Logic**: Audit `src/pipeline/transform.py` to ensure that the `SaleRecord` creation correctly preserves the precision of the parsed amount.
- **Data Verification**: Use the `gh` CLI or Python scripts to inspect the raw content of `data/raw/partner_export_2026-08.csv` to confirm the exact character usage for decimals.
- **Fix implementation**: Implement a locale-aware or robust numeric parser that can handle the variation in decimal separators between the different source systems.

## Testing Decisions

- **Regression Test**: A new test case will be added to the test suite (likely `tests/test_parse.py`) that specifically uses a sample of the partner export data.
- **Test Assertions**: The test will assert that the total revenue calculated from these specific records matches the expected value from the finance report.
- **Verification**: The test must be shown to fail on the current codebase and pass after the fix is applied.

## Out of Scope

- Modifying the source systems or the `partner_export` generation process.
- Changing the database schema for `warehouse.db`.
- Implementing support for any new source systems beyond what is already present.

## Further Notes

The investigation should prioritize determining if the error is a simple parsing failure (e.g., `123,45` being read as `123`) or a more complex transformation error.

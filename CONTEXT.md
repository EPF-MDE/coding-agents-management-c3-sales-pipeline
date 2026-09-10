# Sales Pipeline

Ingests per-store sales transactions from multiple exporters, normalises their disagreeing field formats, and loads clean records into the warehouse for reporting.

## Language

**Exporter**:
A source system that writes one raw CSV per month into `data/raw/`. Each exporter has its own numeric and date formatting conventions that `pipeline.parse` must reconcile.
_Avoid_: Source, feed, system

**Decimal separator**:
The character marking the boundary between the whole and fractional part of an amount (`.` or `,`, e.g. the `,` in `"42,50"`).
_Avoid_: Decimal point, comma

**Grouping separator**:
An optional character (or whitespace, including a non-breaking space) an exporter inserts between digit groups in a large amount, distinct from the decimal separator (e.g. the non-breaking space in `"1 321,49"`, which reads as `1321.49`). A grouping separator that isn't stripped before parsing looks like a decimal separator to a naive parser and causes the amount to be truncated at the first group.
_Avoid_: Thousands separator (implies a fixed group size)

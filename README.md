# sales-pipeline

A small retail sales pipeline: **ingest → transform → load → report**.

Fourteen stores, one month of transactions, three source systems.

## Running it

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

pytest                                  # the test suite
python -m pipeline run                  # rebuild warehouse.db from data/raw/
python -m pipeline totals               # monthly net revenue per store
python -m pipeline report --store S-014 # daily breakdown for one store
```

## How it fits together

| Module | Responsibility |
| --- | --- |
| `pipeline.ingest` | Read the raw CSV exports. Every field comes back as a string, exactly as the exporter wrote it. |
| `pipeline.parse` | Field-level parsing. Source systems disagree about formatting, so amounts, dates and quantities are normalised here. |
| `pipeline.transform` | Raw rows → `SaleRecord`. Applies the discount and computes the net amount. |
| `pipeline.load` | Writes records into SQLite, de-duplicating on `(store_id, txn_id)`. |
| `pipeline.report` | Reporting queries: store totals, daily revenue. |

## Source systems

Three exporters write into `data/raw/`, one file per source per month:

- `pos_north_2026-08.csv` — in-house POS terminals, stores S-001 to S-007
- `pos_south_2026-08.csv` — in-house POS terminals, stores S-008 to S-013
- `partner_export_2026-08.csv` — the franchise partner's own system, store S-014

The partner is not on our POS software and exports in its own regional format.
`pipeline.parse` is where that gets reconciled.

## There is an open bug

See [`BUG-REPORT.md`](BUG-REPORT.md).

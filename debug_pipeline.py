from pathlib import Path
from decimal import Decimal
from src.pipeline.ingest import read_file
from src.pipeline.transform import transform_all

def debug_pipeline():
    file_path = Path("data/raw/partner_export_2026-08.csv")

    if not file_path.exists():
        print(f"Error: {file_path} not found.")
        return

    print(f"Debugging pipeline for: {file_path}")
    rows = read_file(file_path)
    records = transform_all(rows)

    print(f"{'txn_id':<10} | {'gross':<10} | {'disc%':<6} | {'net':<10}")
    print("-" * 45)

    total_net = Decimal("0.00")
    for r in records:
        print(f"{r.txn_id:<10} | {r.gross_amount:<10} | {r.discount_pct:<6} | {r.net_amount:<10}")
        total_net += r.net_amount

    print("-" * 45)
    print(f"Total Net Amount: {total_net}")

if __name__ == "__main__":
    debug_pipeline()

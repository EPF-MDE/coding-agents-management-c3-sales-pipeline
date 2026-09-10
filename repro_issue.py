from pathlib import Path
from decimal import Decimal
from src.pipeline.ingest import read_file
from src.pipeline.transform import transform_all

def reproduce_issue():
    # The path to the problematic file
    file_path = Path("data/raw/partner_export_2026-08.csv")

    if not file_path.exists():
        print(f"Error: {file_path} not found.")
        return

    print(f"Reading {file_path}...")
    rows = read_file(file_path)

    print(f"Loaded {len(rows)} rows.")

    print("Transforming rows...")
    records = transform_all(rows)

    print("Calculating total net amount...")
    total_net = sum((r.net_amount for r in records), Decimal("0.00"))

    expected_total = Decimal("56230.09")

    print(f"Calculated Total Net: {total_net}")
    print(f"Expected Total Net:   {expected_total}")

    if total_net == expected_total:
        print("SUCCESS: Total matches expected value.")
    else:
        diff = total_net - expected_total
        print(f"FAILURE: Total mismatch! Difference: {diff}")
        # We expect a failure here based on the bug report
        exit(1)

if __name__ == "__main__":
    reproduce_issue()

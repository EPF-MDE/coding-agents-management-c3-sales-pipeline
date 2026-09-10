from pathlib import Path
from decimal import Decimal
from src.pipeline.ingest import read_file
from src.pipeline.transform import transform_all

def check_consistency():
    raw_dir = Path("data/raw")
    all_files = list(raw_dir.glob("*.csv"))

    target_store = "S-014"

    partner_file = raw_dir / "partner_export_2026-08.csv"

    partner_total = Decimal("0.00")
    if partner_file.exists():
        print(f"Analyzing {partner_file}...")
        rows = read_file(partner_file)
        records = transform_all(rows)
        partner_total = sum((r.net_amount for r in records if r.store_id == target_store), Decimal("0.00"))
    else:
        print("Partner export file not found.")

    global_total = Decimal("0.00")
    print("Analyzing all files in data/raw/...")
    for csv_file in all_files:
        print(f"  Processing {csv_file.name}...")
        rows = read_file(csv_file)
        records = transform_all(rows)
        global_total += sum((r.net_amount for r in records if r.store_id == target_store), Decimal("0.00"))

    print("-" * 30)
    print(f"Store: {target_store}")
    print(f"Total from partner_export only: {partner_total}")
    print(f"Total from all files:           {global_total}")
    print(f"Difference (Global - Partner):  {global_total - partner_total}")
    print("-" * 30)

    if global_total == partner_total:
        print("SUCCESS: No extra revenue found in other files for S-014.")
    else:
        print("FAILURE: Extra revenue found in other files for S-014!")

if __name__ == "__main__":
    check_consistency()

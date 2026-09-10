import csv
import re

pattern = re.compile(r"^-?[0-9]+[.,][0-9]{1,2}$")

with open("data/raw/partner_export_2026-08.csv", newline="", encoding="utf-8") as f:
    for row in csv.DictReader(f):
        if row["store_id"] != "S-014":
            continue
        if not pattern.match(row["amount"]):
            print(row["txn_id"], repr(row["amount"]))
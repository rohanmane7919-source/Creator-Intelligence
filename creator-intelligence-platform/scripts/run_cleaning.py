"""Usage (from the project root):
    python scripts\\run_cleaning.py
    python scripts\\run_cleaning.py data\\raw\\other_file.csv
Reads the raw CSV (never modified) and writes to data/processed/.
"""
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.cleaning import clean_dataset  # noqa: E402

raw_path = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "data" / "raw" / "social_media_dataset.csv"
out_dir = ROOT / "data" / "processed"
out_dir.mkdir(parents=True, exist_ok=True)

raw = pd.read_csv(raw_path, low_memory=False)
clean, report = clean_dataset(raw)
report["source_file"] = raw_path.name

clean.to_csv(out_dir / "posts_clean.csv", index=False)
with open(out_dir / "quality_report.json", "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2, default=str)

print(f"Rows in : {report['rows_in']}")
print(f"Rows out: {report['rows_out']}")
print("Removed :", report["rows_removed"])
print("Creator-id consistency:", report["creator_id_consistency"])
print("creator_id matches content_id pattern (%):", report["creator_id_hash_match_pct"])
print("Category mapping:")
for k, v in report["category_mapping_counts"].items():
    print(f"   {k}: {v}")
print("Flags:", report["flags"])
print("Date range:", report["date_range"])
print("\nWARNINGS:" if report["warnings"] else "\nNo warnings.")
for w in report["warnings"]:
    print(" -", w)
print("\nSaved: data/processed/posts_clean.csv and quality_report.json")
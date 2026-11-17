"""Usage: python scripts/inspect_dataset.py data/raw/YOUR_FILE.csv > dataset_report.txt"""
import sys
import pandas as pd

path = sys.argv[1]
df = pd.read_csv(path, low_memory=False)

print("SHAPE:", df.shape)
print("\nCOLUMNS AND TYPES:")
print(df.dtypes)
print("\nFIRST 5 ROWS:")
print(df.head().to_string())
print("\nMISSING VALUES:")
print(df.isna().sum()[df.isna().sum() > 0])
print("\nDUPLICATE ROWS:", df.duplicated().sum())
print("\nNUMERIC SUMMARY:")
print(df.describe().T.to_string())
print("\nLOW-CARDINALITY COLUMNS (possible categories or labels):")
for c in df.columns:
    if df[c].nunique() <= 20:
        print(f"\n{c}:\n{df[c].value_counts(dropna=False).to_string()}")

import os
import pandas as pd

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPTS_DIR)
DATA_DIR = os.path.join(ROOT_DIR, "data")

input_csv = os.path.join(DATA_DIR, "instagram_posts.csv") if os.path.exists(os.path.join(DATA_DIR, "instagram_posts.csv")) else "instagram_posts.csv"
output_csv = os.path.join(DATA_DIR, "instagram_posts_cleaned.csv")

df = pd.read_csv(input_csv)
print("Loaded shape:", df.shape)
df = df.drop_duplicates()
df.to_csv(output_csv, index=False, encoding="utf-8-sig")
print("Saved cleaned dataset to:", output_csv)
from pathlib import Path
import pandas as pd

path = Path(__file__).resolve().parent.parent / "data" / "processed" / "posts_clean.csv"
df = pd.read_csv(path)
df["post_date"] = pd.to_datetime(df["post_date"], errors="coerce")

print("=== CREATORS ===")
print("Unique creators:", df["creator_id"].nunique())
ppc = df.groupby("creator_id").size()
print("Posts per creator:\n", ppc.describe())
print("Creators with >=2 / >=10 / >=30 posts:",
      (ppc >= 2).sum(), (ppc >= 10).sum(), (ppc >= 30).sum())

print("\n=== ATTRIBUTE CONSISTENCY PER CREATOR ===")
for col in ["creator_name", "platform", "category_clean"]:
    n = (df.groupby("creator_id")[col].nunique() > 1).sum()
    print(f"Creators with more than one {col}: {n}")

print("\n=== FOLLOWER COUNT OVER TIME ===")
g = df.groupby("creator_id")["follower_count"].nunique()
print("Creators whose follower_count takes >1 distinct value:", (g > 1).sum())

print("\n=== DATES ===")
print("Missing/invalid dates:", df["post_date"].isna().sum())
print("Date range:", df["post_date"].min(), "to", df["post_date"].max())
print("Distinct posting days:", df["post_date"].dt.date.nunique())

print("\n=== DUPLICATES ===")
print("Duplicate content_id:", df["content_id"].duplicated().sum())

print("\n=== FLAGS ===")
print(df[["flag_likes_exceed_views", "flag_interactions_exceed_followers"]].apply(pd.Series.value_counts))

print("\n=== SPONSORSHIP vs DISCLOSURE ===")
print(pd.crosstab(df["is_sponsored"], df["disclosure_type"]))

print("\n=== CATEGORIES / PLATFORMS ===")
print(df["category_clean"].value_counts(dropna=False))
print(df["category_mapping"].value_counts(dropna=False))
print(df["platform"].value_counts())

print("\n=== NUMERIC SUMMARY ===")
cols = ["views", "likes", "shares", "comments_count", "follower_count",
        "engagement_rate_views_pct", "engagement_rate_followers_pct", "reach_rate_pct"]
print(df[cols].describe().T)
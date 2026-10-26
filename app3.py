import pandas as pd

POSTS_CSV = "instagram_posts.csv"       # Your existing 1,009-row dataset
PROFILES_CSV = "creator_profiles.csv"   # Apify profile-scraper output
OUTPUT_CSV = "posts_enriched.csv"

posts = pd.read_csv(POSTS_CSV)
profiles = pd.read_csv(PROFILES_CSV)

# Normalize usernames so the join is stable.
posts["ownerUsername"] = posts["ownerUsername"].astype("string").str.strip().str.lower()
profiles["username"] = profiles["username"].astype("string").str.strip().str.lower()

# Keep useful creator-level fields. Rename them to avoid ambiguous column names.
profile_fields = {
    "username": "ownerUsername",
    "biography": "creatorBio",
    "category": "creatorCategory",
    "followersCount": "creatorFollowers",
    "followingCount": "creatorFollowing",
    "postsCount": "creatorPostCount",
    "isVerified": "creatorIsVerified",
    "isPrivate": "creatorIsPrivate",
    "externalUrl": "creatorWebsite",
}

# Keep only fields that actually exist in this Actor's export.
profile_fields = {
    source: target
    for source, target in profile_fields.items()
    if source in profiles.columns
}

profiles_small = profiles[list(profile_fields)].rename(columns=profile_fields)

# Ensure one profile row per username before merging.
profiles_small = profiles_small.drop_duplicates("ownerUsername", keep="last")

enriched = posts.merge(
    profiles_small,
    on="ownerUsername",
    how="left",
    validate="many_to_one",
)

# Convert numeric fields safely; missing values remain NaN.
for column in [
    "likesCount",
    "commentsCount",
    "videoViewCount",
    "videoPlayCount",
    "creatorFollowers",
]:
    if column in enriched.columns:
        enriched[column] = pd.to_numeric(enriched[column], errors="coerce")

# Engagement per post. This is a public-data proxy, not campaign performance.
if {"likesCount", "commentsCount"}.issubset(enriched.columns):
    enriched["postEngagement"] = (
        enriched["likesCount"].fillna(0)
        + enriched["commentsCount"].fillna(0)
    )

if {"postEngagement", "creatorFollowers"}.issubset(enriched.columns):
    enriched["postEngagementRate"] = (
        enriched["postEngagement"]
        / enriched["creatorFollowers"].replace(0, pd.NA)
    )

# Parse post timestamp and calculate age relative to the newest timestamp in this file.
if "timestamp" in enriched.columns:
    enriched["timestamp"] = pd.to_datetime(
        enriched["timestamp"], errors="coerce", utc=True
    )
    reference_time = enriched["timestamp"].max()
    enriched["postAgeDays"] = (
        reference_time - enriched["timestamp"]
    ).dt.total_seconds() / 86_400

enriched.to_csv(OUTPUT_CSV, index=False)

print(f"Saved {len(enriched):,} rows to {OUTPUT_CSV}")
print("Added columns:", [c for c in profiles_small.columns if c != "ownerUsername"])
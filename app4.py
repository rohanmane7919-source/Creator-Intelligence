import os
import pandas as pd
from apify_client import ApifyClient

POSTS_CSV = "instagram_posts.csv"
PROFILES_CSV = "creator_profiles.csv"

# Actor ID from Apify Store. This Actor accepts Instagram usernames/URLs.
ACTOR_ID = "apify/instagram-profile-scraper"


posts = pd.read_csv(POSTS_CSV)

if "ownerUsername" not in posts.columns:
    raise ValueError("The posts CSV must contain an 'ownerUsername' column.")

usernames = (
    posts["ownerUsername"]
    .dropna()
    .astype(str)
    .str.strip()
    .str.lstrip("@")
    .str.lower()
)

# Remove blank values and accidental header rows.
usernames = usernames[
    usernames.ne("")
    & usernames.ne("ownerusername")
].unique().tolist()

if not usernames:
    raise ValueError("No creator usernames found in ownerUsername.")

print(f"Fetching profiles for {len(usernames)} creators...")

client = ApifyClient(token)

# Actor input schema: usernames plus a cap on profiles to fetch.
run = client.actor(ACTOR_ID).call(
    run_input={
        "usernames": usernames,
        "maxItems": len(usernames),
    }
)

dataset_id = run.default_dataset_id
if not dataset_id:
    raise RuntimeError(f"No dataset ID returned. Run: {run}")

items = list(client.dataset(dataset_id).iterate_items())

if not items:
    raise RuntimeError(
        "Actor returned no profile rows. Check the Actor input schema, "
        "run status, and Apify run logs."
    )

profiles = pd.DataFrame(items)
profiles.to_csv(PROFILES_CSV, index=False)

print(f"Saved {len(profiles)} profile rows to {PROFILES_CSV}")
print("Returned columns:", profiles.columns.tolist())
import os
import sys
import argparse
import pandas as pd
from typing import Optional, Dict, Any, List
from creator_recommender import CreatorRecommender, PROFILES_CSV, POSTS_CSV

try:
    from apify_client import ApifyClient
    APIFY_AVAILABLE = True
except ImportError:
    APIFY_AVAILABLE = False

PROFILE_ACTOR_ID = "apify/instagram-profile-scraper"

def add_new_creator(
    username: str,
    api_token: Optional[str] = None,
    bio: Optional[str] = None,
    category: Optional[str] = None,
    full_name: Optional[str] = None,
    followers: Optional[float] = None,
    following: Optional[float] = None,
    avg_likes: Optional[float] = None,
    avg_comments: Optional[float] = None,
    engagement_rate: Optional[float] = None,
    captions: Optional[str] = None,
    hashtags: Optional[str] = None,
    is_verified: bool = False,
    profiles_csv: str = PROFILES_CSV
) -> Dict[str, Any]:
    """
    Adds a new creator to both the profiles CSV database and the ML vector index.
    
    If api_token (or APIFY_TOKEN in environment) is available, it will automatically
    scrape the creator's live profile from Instagram via Apify.
    
    If no token is provided, manual parameters (bio, category, followers, etc.) are used.
    
    Returns the indexed creator profile record.
    """
    clean_username = username.strip().lower().lstrip("@")
    if not clean_username:
        raise ValueError("Invalid username provided.")

    token = api_token or os.environ.get("APIFY_TOKEN")
    scraped_data: Dict[str, Any] = {}

    # 1. Attempt live scraping if Apify token is available
    if token and APIFY_AVAILABLE:
        print(f"[*] Contacting Apify to scrape live profile for @{clean_username}...")
        try:
            client = ApifyClient(token)
            run = client.actor(PROFILE_ACTOR_ID).call(
                run_input={"usernames": [clean_username], "maxItems": 1}
            )
            dataset_id = run.get("defaultDatasetId") or getattr(run, "default_dataset_id", None)
            if dataset_id:
                items = list(client.dataset(dataset_id).iterate_items())
                if items:
                    scraped_data = items[0]
                    print(f"[+] Successfully scraped live profile for @{clean_username}!")
                else:
                    print(f"[-] No profile data returned by Apify for @{clean_username}. Falling back to provided inputs.")
        except Exception as e:
            print(f"[!] Apify live scraping encountered an error: {e}")
            print("[*] Falling back to manual / provided profile attributes.")
    elif not token:
        print(f"[*] No APIFY_TOKEN provided. Using supplied attributes for @{clean_username}.")

    # 2. Extract & consolidate attributes (prefer scraped data, fallback to manual inputs)
    final_full_name = scraped_data.get("fullName") or full_name or clean_username
    final_bio = scraped_data.get("biography") or bio or ""
    final_category = scraped_data.get("businessCategoryName") or scraped_data.get("categoryName") or category or "General"
    final_followers = scraped_data.get("followersCount") or followers or 0.0
    final_following = scraped_data.get("followsCount") or following or 0.0
    final_posts_count = scraped_data.get("postsCount") or 0
    final_verified = scraped_data.get("verified", is_verified)

    # 3. Append / Update in creator_profiles.csv
    csv_row = {
        "username": clean_username,
        "fullName": final_full_name,
        "biography": final_bio,
        "businessCategoryName": final_category,
        "followersCount": float(final_followers),
        "followsCount": float(final_following),
        "postsCount": float(final_posts_count),
        "verified": bool(final_verified)
    }

    if os.path.exists(profiles_csv):
        df_profiles = pd.read_csv(profiles_csv)
        # Drop existing entry for this user if updating
        if "username" in df_profiles.columns:
            df_profiles = df_profiles[df_profiles["username"].astype(str).str.lower() != clean_username]
        df_profiles = pd.concat([df_profiles, pd.DataFrame([csv_row])], ignore_index=True)
    else:
        df_profiles = pd.DataFrame([csv_row])

    df_profiles.to_csv(profiles_csv, index=False)
    print(f"[+] Saved @{clean_username} into {profiles_csv}")

    # 4. Update the ML vector recommender index
    recommender = CreatorRecommender()
    if not recommender.load_index():
        recommender.build_creator_catalog()

    creator_record = {
        "username": clean_username,
        "fullName": final_full_name,
        "bio": final_bio,
        "category": final_category,
        "followers": float(final_followers),
        "avg_likes": avg_likes or 0.0,
        "avg_comments": avg_comments or 0.0,
        "engagement_rate": engagement_rate or 0.0,
        "aggregated_captions": captions or "",
        "aggregated_hashtags": hashtags or "",
        "is_verified": bool(final_verified)
    }

    recommender.add_or_update_creator(creator_record)

    print(f"\n==================================================")
    print(f"  CREATOR @{clean_username} IS NOW INDEXED & LIVE!  ")
    print(f"  Name: {final_full_name}")
    print(f"  Category: {final_category}")
    print(f"  Followers: {int(final_followers):,}")
    print(f"==================================================\n")

    return creator_record

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Add a new creator to the intelligence catalog & ML index.")
    parser.add_argument("username", type=str, help="Instagram username handle (e.g. mkbhd, fit_sarah)")
    parser.add_argument("--token", type=str, help="Apify API Token (optional if APIFY_TOKEN env var is set)")
    parser.add_argument("--name", type=str, help="Full name or channel name")
    parser.add_argument("--bio", type=str, help="Creator bio description")
    parser.add_argument("--category", type=str, help="Content category / niche (e.g. Fitness, Tech, Travel)")
    parser.add_argument("--followers", type=float, default=0, help="Total follower count")
    parser.add_argument("--eng_rate", type=float, default=0.0, help="Engagement rate (e.g. 0.035 for 3.5%)")
    parser.add_argument("--captions", type=str, default="", help="Sample post captions or keywords")
    parser.add_argument("--hashtags", type=str, default="", help="Relevant hashtags (e.g. #tech #gadgets)")

    args = parser.parse_args()

    record = add_new_creator(
        username=args.username,
        api_token=args.token,
        full_name=args.name,
        bio=args.bio,
        category=args.category,
        followers=args.followers,
        engagement_rate=args.eng_rate,
        captions=args.captions,
        hashtags=args.hashtags
    )

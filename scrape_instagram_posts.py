import os
import pandas as pd
from apify_client import ApifyClient

ACTOR_ID = "streamers/youtube-scraper"

run_input = {
    "directUrls": ["https://www.instagram.com/humansofny/"],
    "resultsType": "posts",
    "resultsLimit": 100
}

def scrape_instagram():
    client = ApifyClient(APIFY_TOKEN)

    print("Starting Instagram scraper...")

    run = client.actor(ACTOR_ID).call(run_input=run_input)

    if run is None:
        raise RuntimeError("Apify Actor run failed.")

    # Run object attributes use snake_case
    dataset_id = run.default_dataset_id

    items = list(client.dataset(dataset_id).iterate_items())

    if not items:
        print("No posts found.")
        return

    df = pd.json_normalize(items)
    output_file = "instagram_posts.csv"
    df.to_csv(output_file, index=False, encoding="utf-8-sig",mode = 'a')

    print(f"Scraped {len(df)} posts.")
    print(f"CSV saved to: {os.path.abspath(output_file)}")
    print("Columns:", list(df.columns))

if __name__ == "__main__":
    scrape_instagram()
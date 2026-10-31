import os
import pandas as pd
from apify_client import ApifyClient

# Set APIFY_TOKEN in your environment, using a newly generated token.
ACTOR_ID = "streamers/youtube-scraper"

run_input = {
    "startUrls": [
        {"url": "https://www.youtube.com/@YouTube/videos"}
    ],
    "maxResults": 100,
    "maxResultsShorts": 0,
    "maxResultStreams": 0,
}

def scrape_youtube():
    if not APIFY_TOKEN:
        raise RuntimeError("Set the APIFY_TOKEN environment variable first.")

    client = ApifyClient(APIFY_TOKEN)
    print("Starting YouTube scraper...")

    run = client.actor(ACTOR_ID).call(run_input=run_input)
    if run is None:
        raise RuntimeError("Apify Actor run failed.")

    dataset_id = run.default_dataset_id
    items = list(client.dataset(dataset_id).iterate_items())
    if not items:
        print("No videos found.")
        return

    df = pd.json_normalize(items)
    output_file = "youtube_videos_new.csv"
    df.to_csv(output_file, index=False, encoding="utf-8-sig")

    print(f"Scraped {len(df)} items.")
    print(f"CSV saved to: {os.path.abspath(output_file)}")
    print("Columns:", list(df.columns))

if __name__ == "__main__":
    scrape_youtube()
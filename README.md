# Creator-Intelligence

An intelligent data collection and machine learning pipeline to recommend creators to users and brands.

## Project Structure & File Guide

### Data Collection & Scraping Scripts
- **[`scrape_instagram_posts.py`](file:///home/omkar/Desktop/creator-intelligence/scrape_instagram_posts.py)** *(formerly `app.py`)*: Uses Apify to scrape post-level metadata (captions, likes, comments, timestamps, hashtags) for target Instagram creator accounts into `instagram_posts.csv`.
- **[`scrape_instagram_profiles.py`](file:///home/omkar/Desktop/creator-intelligence/scrape_instagram_profiles.py)** *(formerly `app4.py`)*: Extracts unique creator handles from `instagram_posts.csv` and scrapes creator-level profile metadata (bio, follower count, business category, verification status) into `creator_profiles.csv`.
- **[`scrape_youtube_videos.py`](file:///home/omkar/Desktop/creator-intelligence/scrape_youtube_videos.py)** *(formerly `app2.py`)*: Uses Apify to scrape YouTube video titles, views, likes, descriptions, and channel stats into `youtube_videos_new.csv`.

### Data Cleaning & Enrichment
- **[`clean_instagram_posts.py`](file:///home/omkar/Desktop/creator-intelligence/clean_instagram_posts.py)** *(formerly `insta.py`)*: Deduplicates and cleans raw Instagram post records into `instagram_posts_cleaned.csv`.
- **[`enrich_instagram_posts.py`](file:///home/omkar/Desktop/creator-intelligence/enrich_instagram_posts.py)** *(formerly `app3.py`)*: Merges Instagram posts with creator profile data, computing engagement rate, post engagement score, and post age into `posts_enriched.csv`.
- **[`inspect_youtube_videos.py`](file:///home/omkar/Desktop/creator-intelligence/inspect_youtube_videos.py)** *(formerly `youtube.py`)*: Inspects and prints summary statistics for YouTube video datasets.

### Exploration & Notebooks
- **[`explore_instagram_posts.ipynb`](file:///home/omkar/Desktop/creator-intelligence/explore_instagram_posts.ipynb)** *(formerly `insta.ipynb`)*: Jupyter notebook for exploratory data analysis on Instagram posts.

### Data Files
- **[`creator_profiles.csv`](file:///home/omkar/Desktop/creator-intelligence/creator_profiles.csv)**: Creator-level profile metrics (followers, bio, category, verified status).
- **[`instagram_posts.csv`](file:///home/omkar/Desktop/creator-intelligence/instagram_posts.csv)**: Post-level Instagram data.
- **[`instagram_posts_cleaned.csv`](file:///home/omkar/Desktop/creator-intelligence/instagram_posts_cleaned.csv)**: Cleaned Instagram post data.
- **[`youtube_videos.csv`](file:///home/omkar/Desktop/creator-intelligence/youtube_videos.csv)** / **[`youtube_videos_new.csv`](file:///home/omkar/Desktop/creator-intelligence/youtube_videos_new.csv)**: YouTube video and channel data.
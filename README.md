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

### Machine Learning & Recommendation
- **[`creator_recommender.py`](file:///home/omkar/Desktop/creator-intelligence/creator_recommender.py)**: Embedding-based recommendation engine. Uses TF-IDF & Cosine Similarity with multi-factor scoring (relevance + engagement rate + follower tiers) to recommend creators by natural language query or find creators similar to a given handle.
- **[`add_new_creator.py`](file:///home/omkar/Desktop/creator-intelligence/add_new_creator.py)**: Dynamic ingestion script. Scrapes a new creator via Apify (or accepts profile inputs) and immediately updates both `creator_profiles.csv` and the vector index without requiring full model retraining.
- **[`test_recommender.py`](file:///home/omkar/Desktop/creator-intelligence/test_recommender.py)**: Comprehensive evaluation suite measuring Precision@K, Mean Reciprocal Rank (MRR), lookalike co-domain accuracy, and filter compliance.

### Data Files
- **[`top_insta_influencers_data.csv`](file:///home/omkar/Desktop/creator-intelligence/top_insta_influencers_data.csv)**: Top 200 global Instagram influencers with engagement rates, followers, and country.
- **[`creator_profiles.csv`](file:///home/omkar/Desktop/creator-intelligence/creator_profiles.csv)**: Creator-level profile metrics (followers, bio, category, verified status).
- **[`instagram_posts.csv`](file:///home/omkar/Desktop/creator-intelligence/instagram_posts.csv)**: Post-level Instagram data.
- **[`instagram_posts_cleaned.csv`](file:///home/omkar/Desktop/creator-intelligence/instagram_posts_cleaned.csv)**: Cleaned Instagram post data.
- **[`youtube_videos.csv`](file:///home/omkar/Desktop/creator-intelligence/youtube_videos.csv)** / **[`youtube_videos_new.csv`](file:///home/omkar/Desktop/creator-intelligence/youtube_videos_new.csv)**: YouTube video and channel data.

---

## How to Run the Application

### 1. Launch the Interactive Web Platform (FastAPI UI)
Start the complete web application directly:
```bash
python main.py
```
Open **[http://127.0.0.1:8000](http://127.0.0.1:8000)** in your browser to explore creators, run natural language queries, discover lookalikes, and dynamically add new creators! Interactive Swagger API docs are available at **[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)**.

---

## Command Line Usage

### 2. Recommend Creators by Natural Language Query
Search for creators matching a specific campaign, niche, or topic:
```bash
python creator_recommender.py --query "emotional storytelling and street portrait photography"
python creator_recommender.py --query "smartphones gadgets tech reviews" --tier "Micro"
```

### 2. Find Creators Similar to a Target Creator
Discover lookalike creators matching an existing creator's tone and audience:
```bash
python creator_recommender.py --similar humansofny
```

### 3. Dynamically Add a New Influencer
Add any new creator (live via Apify or manual input). They become immediately searchable without retraining:
```bash
# Using Apify live scraping (requires APIFY_TOKEN):
python add_new_creator.py mkbhd --token your_apify_token

# Or manual input:
python add_new_creator.py fit_sarah \
  --name "Sarah Fitness" \
  --category "Fitness & Health" \
  --bio "HIIT workouts, healthy meal prep, daily motivation" \
  --followers 120000 \
  --eng_rate 0.048 \
  --hashtags "#fitness #workout #mealprep #health"
```
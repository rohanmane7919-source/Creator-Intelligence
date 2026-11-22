# Creator Intelligence Platform

Production-grade Creator Discovery, Real-time Lookalike Recommendation Engine, and AI Campaign Advisor.

## Overview

Creator Intelligence provides brand marketers and agencies with semantic creator discovery, automated lookalike matching, an AI campaign advisor, and adaptive personal recommendations.

## Core Features

- Professional Light UI: Modern, clean interface designed for marketing clarity without visual clutter or dark neon themes.
- Unified User Dashboard: Real-time influencer search and interactive AI chatbot seamlessly integrated into a single view.
- Adaptive 5-Creator Recommendation System: Returns exactly 5 personalized creator recommendations that evolve with every search query and conversation topic.
- AI Campaign Advisor: Powered by LLM reasoning with catalog grounding to suggest creators, optimize outreach, and synthesize campaign goals.
- Multi-Role Authentication: Dedicated portals and controls for Brands/Users, Content Creators, and Administrators.
- Cloud Database Architecture (`database.py`): Cloud persistence using Supabase PostgreSQL for users, search history, chat logs, user preferences, and creator catalog records.
- Automated Schema Provisioner (`databasecreator`): Programmatic database initializer utilizing binary PostgreSQL connectors (`psycopg2-binary`) to provision all tables and security policies automatically.
- Autonomous Recommendation Service (`recommendation.py`): Vector retrieval pipeline combining TF-IDF cosine similarity, normalized engagement rates, and personalized context queries.

## Project Architecture & Directory Structure

```
creator-intelligence/
├── data/                               # Datasets, catalogs, and data artifacts
│   ├── creator_profiles.csv            # Creator master catalog
│   ├── instagram_posts.csv             # Raw Instagram post data
│   ├── instagram_posts_cleaned.csv     # Cleaned Instagram post data
│   ├── top_insta_influencers_data.csv  # Kaggle top influencers dataset
│   ├── youtube_videos.csv              # YouTube videos dataset
│   └── youtube_videos_new.csv          # Enriched YouTube videos dataset
├── scripts/                            # Data processing & setup scripts
│   ├── databasecreator.py              # Automated Supabase database & schema initializer
│   ├── clean_instagram_posts.py        # Post deduplication & cleaning utility
│   ├── enrich_instagram_posts.py       # Dataset enrichment script
│   ├── inspect_youtube_videos.py       # Dataset inspection script
│   ├── scrape_instagram_posts.py       # Apify Instagram post scraper
│   ├── scrape_instagram_profiles.py    # Apify Instagram profile scraper
│   ├── scrape_youtube_videos.py        # Apify YouTube scraper
│   └── explore_instagram_posts.ipynb   # Exploratory data analysis notebook
├── src/                                # Core backend and ML recommendation engine
│   ├── __init__.py                     # Source package initialization
│   ├── add_new_creator.py              # Dynamic creator profile ingestion service
│   ├── creator_knowledge.py            # Global influencer domain knowledge mappings
│   ├── creator_recommender.py          # TF-IDF vector similarity & lookalike engine
│   ├── database.py                     # Supabase PostgreSQL database operations
│   └── recommendation.py               # Recommendation service & scoring pipeline
├── static/                             # Frontend static assets
│   ├── css/
│   │   └── style.css                   # Custom responsive CSS design system
│   └── js/
│       ├── app.js                      # User dashboard application logic
│       └── home.js                     # Home landing page interactive logic
├── templates/                          # Jinja2 HTML templates
│   ├── admin.html                      # Administrator dashboard & telemetry
│   ├── creator.html                    # Content creator portal
│   ├── home.html                       # Public landing page with live sandbox
│   ├── index.html                      # Authenticated discovery dashboard
│   └── login.html                      # Multi-role authentication page
├── tests/                              # Automated test suites
│   ├── __init__.py
│   └── test_recommender.py             # Precision & ranking benchmark tests
├── .env.example                        # Example environment variables
├── .gitignore                          # Git ignore configuration
├── main.py                             # Main application entrypoint (FastAPI server)
├── README.md                           # Documentation
└── requirements.txt                    # Project dependencies
```

## Supabase Database Setup

### Option 1: Automated Setup via `scripts/databasecreator.py`

Run the `databasecreator.py` script with your Supabase direct connection string:

```bash
python scripts/databasecreator.py postgresql://postgres:[YOUR-PASSWORD]@db.[YOUR-PROJECT-REF].supabase.co:5432/postgres
```

Or set `DATABASE_URL` in your `.env` file and execute:

```bash
python scripts/databasecreator.py
```

The script will connect using binary PostgreSQL drivers, create all 5 tables, disable row-level security for public API access, and seed the default accounts (`user`, `creator`, `admin`).

### Option 2: Manual Setup via Supabase SQL Editor

Paste and run the following SQL statements in the SQL Editor of your Supabase dashboard:

```sql
CREATE TABLE IF NOT EXISTS users_ci (
    id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    email TEXT DEFAULT '',
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'user',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS search_history (
    id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    user_id BIGINT REFERENCES users_ci(id) ON DELETE CASCADE,
    query TEXT NOT NULL,
    category TEXT DEFAULT '',
    result_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS user_preferences (
    user_id BIGINT PRIMARY KEY REFERENCES users_ci(id) ON DELETE CASCADE,
    summary_text TEXT DEFAULT '',
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS chat_messages (
    id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    user_id BIGINT REFERENCES users_ci(id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS creators (
    id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    full_name TEXT DEFAULT '',
    bio TEXT DEFAULT '',
    category TEXT DEFAULT '',
    followers DOUBLE PRECISION DEFAULT 0,
    engagement_rate DOUBLE PRECISION DEFAULT 0,
    follower_tier TEXT DEFAULT 'Unknown',
    avg_likes DOUBLE PRECISION DEFAULT 0,
    profile_pic_url TEXT DEFAULT '',
    is_verified INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE users_ci DISABLE ROW LEVEL SECURITY;
ALTER TABLE search_history DISABLE ROW LEVEL SECURITY;
ALTER TABLE user_preferences DISABLE ROW LEVEL SECURITY;
ALTER TABLE chat_messages DISABLE ROW LEVEL SECURITY;
ALTER TABLE creators DISABLE ROW LEVEL SECURITY;
```

### Table Summary

| Table Name | Description | Key Columns |
|---|---|---|
| `users_ci` | User credentials and roles | `id`, `username`, `email`, `password_hash`, `role`, `created_at` |
| `search_history` | Log of search queries made by users | `id`, `user_id`, `query`, `category`, `result_count`, `created_at` |
| `user_preferences` | Aggregated user interest summaries for AI suggestions | `user_id`, `summary_text`, `updated_at` |
| `chat_messages` | Chat conversation messages between users and AI advisor | `id`, `user_id`, `role`, `content`, `created_at` |
| `creators` | Creator profiles, metrics, and catalog data | `id`, `username`, `full_name`, `bio`, `category`, `followers`, `engagement_rate`, `follower_tier`, `avg_likes`, `profile_pic_url`, `is_verified`, `created_at` |

## Environment Configuration

Create a `.env` file in the project root:

```env
GROQ_API_KEY=your_groq_api_key_here
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_anon_key_here
DATABASE_URL=postgresql://postgres:your_password@db.your-project.supabase.co:5432/postgres
```

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the Web Application
```bash
python main.py
```
Access the application at http://127.0.0.1:8000.

### 3. Default Demo Accounts

| Role | Username | Password | Default Portal |
|---|---|---|---|
| Brand / User | `user` | `user123` | Discovery & AI Chat Dashboard (`/`) |
| Creator | `creator` | `creator123` | Creator Profile & Lookalikes (`/creator`) |
| Administrator | `admin` | `admin123` | Admin Telemetry & Indexing Console (`/admin`) |

### 4. Recommendation Workflow

1. Initial Login: Users without search history receive 5 curated, top-performing creators across diverse catalog categories.
2. Search Execution: Queries are stored in Supabase, matching creators are presented in the discovery list, and the 5 recommendations adapt immediately.
3. Conversational Advisory: Interacting with the AI advisor updates user preference keywords and synthesizes recommendations in real time.

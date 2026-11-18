# Creator Intelligence Platform

Production-grade Creator Discovery, Real-time Lookalike Recommendation Engine, and AI Campaign Advisor.

## Overview

Creator Intelligence provides brand marketers and agencies with semantic creator discovery, automated lookalike matching, an AI campaign advisor, and adaptive personal recommendations.

## Core Features

- **Professional Light UI**: Modern, clean interface designed for marketing clarity without visual clutter or dark neon themes.
- **Unified User Dashboard**: Real-time influencer search and interactive AI chatbot seamlessly integrated into a single view.
- **Adaptive 5-Creator Recommendation System**: Returns exactly 5 personalized creator recommendations that evolve with every search query and conversation topic.
- **AI Campaign Advisor**: Powered by LLM reasoning with catalog grounding to suggest creators, optimize outreach, and synthesize campaign goals.
- **Multi-Role Authentication**: Dedicated portals and controls for Brands/Users, Content Creators, and Administrators.
- **Decoupled Database Architecture (`database.py`)**: Pure DAO service layer wrapping SQLite for users, search history, chat logs, user profile summaries, and creator catalog records.
- **Autonomous Recommendation Service (`recommendation.py`)**: Vector retrieval pipeline combining TF-IDF cosine similarity, normalized engagement rates, and personalized context queries.

## Architecture & File Guide

- `main.py`: FastAPI server exposing authentication routes, search API, chat completions endpoint, and dashboard views.
- `database.py`: Database operations module managing SQLite schema, user authentication, search history logging, chat records, and creator profiles.
- `recommendation.py`: Recommendation engine computing query relevance, lookalike similarity, and user-adaptive 5-card recommendations.
- `creator_recommender.py`: Core vector catalog and TF-IDF similarity model.
- `add_new_creator.py`: Live ingestion pipeline to scrape or manually register and index new influencers into the vector store.
- `requirements.txt`: Python package dependencies.
- `templates/`:
  - `login.html`: Multi-role login and registration portal with 1-click demo logins.
  - `index.html`: Unified Brand/User dashboard containing search discovery, filters, personalized recommendations, and the AI chatbot.
  - `creator.html`: Creator portal displaying profile metrics, editable credentials, and lookalike peer benchmarks.
  - `admin.html`: Administrator console featuring platform telemetry, search audit logs, user management, and creator indexing.
- `static/`:
  - `css/style.css`: Clean, professional design system with light color palette and typography.
  - `js/app.js`: Modular client logic managing search execution, recommendation refreshes, chat message streaming, and profile modals.

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the Web Application
```bash
python main.py
```
Access the application at [http://127.0.0.1:8000](http://127.0.0.1:8000).

### 3. Default Demo Accounts

| Role | Username | Password | Default Portal |
|---|---|---|---|
| Brand / User | `user` | `user123` | Discovery & AI Chat Dashboard (`/`) |
| Creator | `creator` | `creator123` | Creator Profile & Lookalikes (`/creator`) |
| Administrator | `admin` | `admin123` | Admin Telemetry & Indexing Console (`/admin`) |

You can also use the 1-click demo login buttons directly on the login page or register a new user account.

### 4. Recommendation Workflow

1. **Initial Login**: Users without search history receive 5 curated, top-performing creators across diverse catalog categories.
2. **Search Execution**: Queries are stored in the database, matching creators are presented in the discovery list, and the 5 recommendations adapt immediately.
3. **Conversational Advisory**: Interacting with the AI advisor updates user preference keywords and synthesizes the recommendations in real time.

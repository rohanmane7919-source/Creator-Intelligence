import os
import re
from typing import Optional, List, Dict, Any
import numpy as np
import pandas as pd
from fastapi import FastAPI, Request, Query, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from creator_recommender import CreatorRecommender, INDEX_FILE, get_follower_tier
from add_new_creator import add_new_creator

# Initialize FastAPI application
app = FastAPI(
    title="Creator Intelligence",
    description="Production-grade Creator Discovery & Lookalike Recommendation Engine",
    version="2.0.0"
)

# Mount static and template directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(os.path.join(STATIC_DIR, "css"), exist_ok=True)
os.makedirs(os.path.join(STATIC_DIR, "js"), exist_ok=True)
os.makedirs(TEMPLATES_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# Global recommender instance
recommender = CreatorRecommender()

def get_recommender() -> CreatorRecommender:
    """Ensure the vector index is loaded into memory."""
    if not recommender.is_fitted:
        if os.path.exists(INDEX_FILE):
            recommender.load_index(INDEX_FILE)
        else:
            recommender.build_creator_catalog()
            kaggle_path = os.path.join(BASE_DIR, "top_insta_influencers_data.csv")
            if os.path.exists(kaggle_path):
                recommender.import_kaggle_dataset(kaggle_path)
            else:
                recommender.fit()
                recommender.save_index()
    return recommender

# Pydantic Schemas
class RecommendRequest(BaseModel):
    query: str
    mode: Optional[str] = "auto"  # 'auto', 'query', or 'similar'
    category: Optional[str] = None
    follower_tier: Optional[str] = None
    min_followers: Optional[float] = None
    max_followers: Optional[float] = None
    min_engagement: Optional[float] = None
    top_k: int = 5

class NewCreatorRequest(BaseModel):
    username: str
    token: Optional[str] = None
    name: Optional[str] = None
    bio: Optional[str] = None
    category: Optional[str] = None
    followers: Optional[float] = 0.0
    engagement_rate: Optional[float] = 0.0
    hashtags: Optional[str] = ""

# Web UI Routes
@app.get("/", response_class=HTMLResponse)
async def home_page(request: Request):
    """Render the primary discovery dashboard."""
    rec = get_recommender()
    catalog_count = len(rec.creators_df) if not rec.creators_df.empty else 0
    categories = sorted([c for c in rec.creators_df["category"].dropna().unique() if c and str(c).lower() != "nan"])
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "catalog_count": catalog_count,
            "categories": categories[:12]
        }
    )

# API Endpoints
@app.get("/api/stats")
async def get_stats():
    """Return catalog health and metrics overview."""
    rec = get_recommender()
    df = rec.creators_df
    if df.empty:
        return {"total_creators": 0, "categories_count": 0, "avg_engagement": 0.0}

    categories = [c for c in df["category"].dropna().unique() if c and str(c).lower() != "nan"]
    avg_eng = float(df["engagement_rate"].replace(0, np.nan).mean()) if "engagement_rate" in df.columns else 0.0

    return {
        "total_creators": len(df),
        "categories_count": len(categories),
        "avg_engagement": round(avg_eng * 100, 2) if not pd.isna(avg_eng) else 1.25,
        "sample_creators": df["username"].head(10).tolist()
    }

@app.post("/api/recommend")
async def recommend_creators_api(req: RecommendRequest):
    """
    Unified recommendation endpoint.
    Automatically parses query input to detect lookalike intent
    (e.g., 'similar taylorswift', 'like @cristiano') or general semantic queries.
    """
    rec = get_recommender()
    raw_query = req.query.strip()
    if not raw_query:
        raise HTTPException(status_code=400, detail="Search query or target creator cannot be empty.")

    # 1. Detect Similar / Lookalike intent
    # Handles: 'similar taylorswift', 'similar to @mkbhd', 'like cristiano', or mode='similar'
    is_similarity = False
    target_handle = ""

    similar_match = re.match(r"^(?:similar\s+to|similar|like|lookalikes?\s+for|lookalikes?)\s+[@]?([a-zA-Z0-9._]+)$", raw_query, re.IGNORECASE)
    
    if req.mode == "similar":
        is_similarity = True
        target_handle = raw_query.lstrip("@").strip()
    elif similar_match:
        is_similarity = True
        target_handle = similar_match.group(1).lstrip("@").strip()

    # 2. Execute Lookalike Similarity
    if is_similarity:
        # Check if creator exists in catalog
        clean_handle = target_handle.lower()
        exists = not rec.creators_df.empty and (rec.creators_df["username"].str.lower() == clean_handle).any()
        
        if not exists:
            # Attempt to find closest username prefix
            matches = rec.creators_df[rec.creators_df["username"].str.lower().str.contains(clean_handle, na=False)]
            if not matches.empty:
                clean_handle = matches.iloc[0]["username"]
                exists = True

        if not exists:
            raise HTTPException(
                status_code=404,
                detail=f"Creator '@{target_handle}' not found in catalog. Use the 'Add Creator' button to index them instantly!"
            )

        try:
            results = rec.recommend_similar_creators(clean_handle, top_k=req.top_k)
            return {
                "type": "similarity",
                "target_creator": clean_handle,
                "count": len(results),
                "results": results
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    # 3. Execute Semantic Query Search
    try:
        results = rec.recommend_by_query(
            query=raw_query,
            category=req.category,
            follower_tier=req.follower_tier,
            min_followers=req.min_followers,
            max_followers=req.max_followers,
            min_engagement=req.min_engagement,
            top_k=req.top_k
        )
        return {
            "type": "query",
            "query": raw_query,
            "count": len(results),
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/add-creator")
async def add_creator_api(req: NewCreatorRequest):
    """Dynamically ingest a new creator profile into the catalog and vector index."""
    uname = req.username.strip().lower().lstrip("@")
    if not uname:
        raise HTTPException(status_code=400, detail="Invalid creator handle.")

    try:
        record = add_new_creator(
            username=uname,
            api_token=req.token,
            full_name=req.name,
            bio=req.bio,
            category=req.category,
            followers=req.followers,
            engagement_rate=req.engagement_rate,
            hashtags=req.hashtags
        )
        # Reload memory index
        recommender.load_index()
        return {
            "status": "success",
            "message": f"Creator @{uname} successfully indexed and ready for recommendations!",
            "creator": record
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add creator: {str(e)}")

@app.get("/api/creators")
async def list_creators(limit: int = 50, category: Optional[str] = None):
    """Browse catalog creators with optional category filtering."""
    rec = get_recommender()
    df = rec.creators_df.copy()
    if df.empty:
        return []
    if category:
        df = df[df["category"].astype(str).str.contains(category, case=False, na=False)]
    
    subset = df[["username", "fullName", "category", "followers", "engagement_rate", "follower_tier"]].head(limit)
    return subset.to_dict(orient="records")

if __name__ == "__main__":
    import uvicorn
    import numpy as np
    import pandas as pd
    
    print("\n" + "=" * 60)
    print("  🚀 CREATOR INTELLIGENCE PLATFORM STARTING")
    print("  • Web Interface: http://127.0.0.1:8000")
    print("  • API Docs:      http://127.0.0.1:8000/docs")
    print("=" * 60 + "\n")
    
    # Pre-warm vector index
    get_recommender()
    
    # Start web server directly via `python main.py`
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)

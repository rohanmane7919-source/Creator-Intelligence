import os
import re
from typing import Optional, List, Dict, Any
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Request, Response, HTTPException, Depends
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(BASE_DIR, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from src import database, recommendation
from src.add_new_creator import add_new_creator

try:
    from groq import Groq
    groq_api_key = os.getenv("GROQ_API_KEY")
    groq_client = Groq(api_key=groq_api_key) if groq_api_key else None
except Exception:
    groq_client = None

app = FastAPI(
    title="Creator Intelligence",
    version="3.0.0"
)

@app.middleware("http")
async def add_no_cache_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(os.path.join(STATIC_DIR, "css"), exist_ok=True)
os.makedirs(os.path.join(STATIC_DIR, "js"), exist_ok=True)
os.makedirs(TEMPLATES_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

@app.on_event("startup")
def on_startup():
    database.init_db()
    engine = recommendation.get_engine()
    if not engine.creators_df.empty:
        existing = database.get_all_creators(limit=5)
        if not existing:
            creators_list = engine.creators_df.to_dict(orient="records")
            database.sync_creators_from_catalog(creators_list)

def get_current_user(request: Request) -> Optional[Dict[str, Any]]:
    user_id_cookie = request.cookies.get("session_user_id")
    if not user_id_cookie:
        return None
    try:
        user_id = int(user_id_cookie)
        return database.get_user_by_id(user_id)
    except (ValueError, TypeError):
        return None

class LoginRequest(BaseModel):
    username: str
    password: str
    role: Optional[str] = None

class SignupRequest(BaseModel):
    username: str
    password: str
    email: Optional[str] = ""
    role: Optional[str] = "user"

class SearchRequest(BaseModel):
    query: Optional[str] = ""
    mode: Optional[str] = "auto"
    category: Optional[str] = None
    follower_tier: Optional[str] = None
    min_followers: Optional[float] = None
    max_followers: Optional[float] = None
    min_engagement: Optional[float] = None
    top_k: int = 8

class ChatRequest(BaseModel):
    message: str

class CreatorUpdateRequest(BaseModel):
    username: str
    full_name: Optional[str] = None
    bio: Optional[str] = None
    category: Optional[str] = None
    followers: Optional[float] = None
    engagement_rate: Optional[float] = None

class AdminAddCreatorRequest(BaseModel):
    username: str
    name: Optional[str] = None
    bio: Optional[str] = None
    category: Optional[str] = None
    followers: Optional[float] = 0.0
    engagement_rate: Optional[float] = 0.0
    token: Optional[str] = None

def get_featured_creators_catalog(limit: int = 8) -> List[Dict[str, Any]]:
    featured = []
    try:
        db_creators = database.get_all_creators(limit=limit * 3)
        if db_creators:
            for c in db_creators:
                uname = str(c.get("username", "")).strip().lstrip("@")
                if not uname or uname.lower() == "nan":
                    continue
                f_num = float(c.get("followers") or 0)
                e_num = float(c.get("engagement_rate") or 0)
                bio = str(c.get("bio") or "")
                if len(bio) > 130:
                    bio = bio[:127] + "..."
                featured.append({
                    "username": uname,
                    "full_name": str(c.get("full_name") or uname),
                    "category": str(c.get("category") or "Creator"),
                    "followers": int(f_num),
                    "followers_formatted": recommendation.format_number(f_num),
                    "engagement_rate": e_num,
                    "engagement_formatted": recommendation.format_engagement(e_num),
                    "follower_tier": str(c.get("follower_tier") or recommendation.get_follower_tier(f_num)),
                    "bio": bio,
                    "profile_pic_url": str(c.get("profile_pic_url") or ""),
                    "is_verified": bool(c.get("is_verified"))
                })
                if len(featured) >= limit:
                    break
    except Exception:
        pass

    if not featured:
        try:
            engine = recommendation.get_engine()
            if not engine.creators_df.empty:
                for _, row in engine.creators_df.head(limit).iterrows():
                    featured.append(recommendation.clean_creator_output(row.to_dict()))
        except Exception:
            pass

    return featured

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    user = get_current_user(request)
    if user:
        if user["role"] == "admin":
            return RedirectResponse(url="/admin", status_code=302)
        elif user["role"] == "creator":
            return RedirectResponse(url="/creator", status_code=302)
        return RedirectResponse(url="/dashboard", status_code=302)
    return templates.TemplateResponse(request=request, name="login.html", context={})

@app.post("/api/login")
async def api_login(req: LoginRequest, response: Response):
    user = database.authenticate_user(req.username, req.password, req.role)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username, password, or role selection.")
    response.set_cookie(
        key="session_user_id",
        value=str(user["id"]),
        max_age=86400 * 7,
        httponly=True,
        samesite="lax",
        path="/"
    )
    redirect_map = {"admin": "/admin", "creator": "/creator", "user": "/dashboard"}
    target_url = redirect_map.get(user["role"], "/dashboard")
    return {"status": "success", "user": user, "redirect_url": target_url}

@app.post("/api/signup")
async def api_signup(req: SignupRequest, response: Response):
    existing = database.get_user_by_username(req.username)
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists. Please choose another or login.")
    user = database.create_user(
        username=req.username,
        password=req.password,
        role=req.role or "user",
        email=req.email or ""
    )
    if not user:
        raise HTTPException(status_code=500, detail="Failed to create user account.")
    response.set_cookie(
        key="session_user_id",
        value=str(user["id"]),
        max_age=86400 * 7,
        httponly=True,
        samesite="lax",
        path="/"
    )
    redirect_map = {"admin": "/admin", "creator": "/creator", "user": "/dashboard"}
    target_url = redirect_map.get(user["role"], "/dashboard")
    return {"status": "success", "user": user, "redirect_url": target_url}

@app.get("/logout")
async def logout(response: Response):
    resp = RedirectResponse(url="/login", status_code=302)
    resp.delete_cookie(key="session_user_id", path="/")
    return resp

@app.post("/api/logout")
async def api_logout(response: Response):
    response.delete_cookie(key="session_user_id", path="/")
    return {"status": "success"}

ALLOWED_CATEGORIES = ["Fashion", "Beauty", "Technology", "Fitness"]

@app.get("/", response_class=HTMLResponse)
@app.get("/home", response_class=HTMLResponse)
async def home_page_view(request: Request):
    user = get_current_user(request)
    engine = recommendation.get_engine()
    catalog_count = len(engine.creators_df) if not engine.creators_df.empty else 0
    categories = ALLOWED_CATEGORIES
    stats = database.get_system_stats()
    featured = get_featured_creators_catalog(limit=8)

    return templates.TemplateResponse(
        request=request,
        name="home.html",
        context={
            "user": user,
            "catalog_count": catalog_count,
            "categories": categories,
            "featured_creators": featured,
            "stats": stats
        }
    )

@app.get("/dashboard", response_class=HTMLResponse)
async def user_dashboard_view(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    if user["role"] == "admin":
        return RedirectResponse(url="/admin", status_code=302)
    if user["role"] == "creator":
        return RedirectResponse(url="/creator", status_code=302)

    engine = recommendation.get_engine()
    catalog_count = len(engine.creators_df) if not engine.creators_df.empty else 0
    categories = ALLOWED_CATEGORIES
    summary = database.get_user_summary(user["id"])

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "user": user,
            "catalog_count": catalog_count,
            "categories": categories,
            "user_summary": summary
        }
    )

@app.get("/creator", response_class=HTMLResponse)
async def creator_dashboard(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    
    creator_record = database.get_creator_by_username(user["username"])
    if not creator_record:
        all_creators = database.get_all_creators(limit=1)
        if all_creators:
            creator_record = all_creators[0]
        else:
            creator_record = {
                "username": user["username"],
                "full_name": user["username"].capitalize(),
                "bio": "Content creator profile",
                "category": "Digital Creator",
                "followers": 150000,
                "engagement_rate": 0.035,
                "follower_tier": "Mid-Tier (100K-500K)",
                "avg_likes": 5000
            }

    lookalikes = []
    try:
        engine = recommendation.get_engine()
        if not engine.creators_df.empty and (engine.creators_df["username"].str.lower() == creator_record["username"].lower()).any():
            raw_sim = engine.recommend_similar_creators(creator_record["username"], top_k=5)
            lookalikes = [recommendation.clean_creator_output(r, f"Niche peer for @{creator_record['username']}") for r in raw_sim]
    except Exception:
        lookalikes = recommendation.get_curated_baseline(top_k=5)

    return templates.TemplateResponse(
        request=request,
        name="creator.html",
        context={
            "user": user,
            "creator": creator_record,
            "lookalikes": lookalikes
        }
    )

@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    if user["role"] != "admin":
        return RedirectResponse(url="/", status_code=302)

    stats = database.get_system_stats()
    recent_searches = database.get_all_searches(limit=15)
    users_list = database.get_all_users()
    creators_list = database.get_all_creators(limit=25)

    return templates.TemplateResponse(
        request=request,
        name="admin.html",
        context={
            "user": user,
            "stats": stats,
            "recent_searches": recent_searches,
            "users_list": users_list,
            "creators_list": creators_list
        }
    )

@app.get("/api/current-user")
async def api_current_user(request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    summary = database.get_user_summary(user["id"])
    return {"user": user, "summary": summary}

@app.get("/api/recommendations")
async def api_recommendations(request: Request):
    user = get_current_user(request)
    user_id = user["id"] if user else 1
    recs = recommendation.get_user_recommendations(user_id=user_id, top_k=5)
    summary = database.get_user_summary(user_id) if user else ""
    return {
        "status": "success",
        "recommendations": recs,
        "count": len(recs),
        "user_summary": summary
    }

@app.post("/api/search")
async def api_search(req: SearchRequest, request: Request):
    user = get_current_user(request)
    user_id = user["id"] if user else 1
    search_res = recommendation.search_influencers(
        query=req.query or "",
        mode=req.mode or "auto",
        category=req.category,
        follower_tier=req.follower_tier,
        min_followers=req.min_followers,
        max_followers=req.max_followers,
        min_engagement=req.min_engagement,
        top_k=req.top_k or 8
    )
    q_to_record = (req.query or "").strip()
    cat_to_record = (req.category or "").strip()
    if q_to_record or cat_to_record:
        database.record_user_search(
            user_id=user_id,
            query=q_to_record or cat_to_record,
            category=cat_to_record,
            result_count=search_res.get("count", 0)
        )
    updated_recs = recommendation.get_user_recommendations(user_id=user_id, top_k=5)
    summary = database.get_user_summary(user_id) if user else ""
    search_res["updated_user_recommendations"] = updated_recs
    search_res["user_summary"] = summary
    return search_res

@app.post("/api/chat")
async def api_chat(req: ChatRequest, request: Request):
    user = get_current_user(request)
    user_id = user["id"] if user else 1
    raw_message = req.message.strip()
    if not raw_message:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    past_chats = database.get_user_chat_history(user_id, limit=8)
    existing_summary = database.get_user_summary(user_id)
    recent_searches = database.get_user_recent_searches(user_id, limit=4)

    search_hits = recommendation.search_influencers(raw_message, top_k=3)
    suggested_influencers = search_hits.get("results", [])

    catalog_context = ""
    if suggested_influencers:
        candidate_lines = []
        for c in suggested_influencers:
            suitability_line = recommendation.generate_suitability_reason(c, raw_message)
            c["match_reason"] = suitability_line
            candidate_lines.append(
                f"- @{c['username']} ({c.get('full_name', '')}, {c.get('category')}, {c.get('followers_formatted')} followers, {c.get('engagement_formatted')} eng): {suitability_line}"
            )
        catalog_context = "Verified catalog candidates:\n" + "\n".join(candidate_lines)

    system_instruction = (
        "You are the Creator Intelligence AI Matchmaker and advisor. "
        "Your mission is to help the user identify and select the best creators for their needs.\n"
        "STRICT REQUIREMENTS:\n"
        "1. For EVERY creator recommended, you MUST include exactly one dedicated line explaining why this creator is suitable for the user (audience fit, engagement strength, content specialty).\n"
        "2. Format each recommended creator as a bullet:\n"
        "• @handle (Category) - [One-line reason why this creator is suitable for you]\n"
        "3. Recommend 2 to 3 relevant creators from the verified catalog candidates.\n"
        "4. Keep the total answer concise, direct, and without conversational filler."
    )
    if existing_summary:
        system_instruction += f"\nUser interest profile: {existing_summary}."
    if catalog_context:
        system_instruction += f"\n{catalog_context}"

    ai_reply = ""
    if groq_client:
        clean_history = []
        last_role = None
        for msg in past_chats:
            r = msg.get("role")
            c = str(msg.get("content", "")).strip()
            if r in ["user", "assistant"] and c:
                if r != last_role:
                    clean_history.append({"role": r, "content": c})
                    last_role = r

        if clean_history and clean_history[-1]["role"] == "user":
            clean_history.pop()

        chat_messages_payload = [{"role": "system", "content": system_instruction}]
        chat_messages_payload.extend(clean_history)
        chat_messages_payload.append({"role": "user", "content": raw_message})

        for model_name in ["qwen/qwen3.8-27b", "openai/gpt-oss-120b"]:
            try:
                completion = groq_client.chat.completions.create(
                    model=model_name,
                    messages=chat_messages_payload,
                    max_tokens=220,
                    temperature=0.4,
                    timeout=8.0
                )
                txt = str(completion.choices[0].message.content).strip()
                if txt:
                    ai_reply = txt
                    break
            except Exception:
                continue

    if not ai_reply:
        if suggested_influencers:
            lines = []
            for c in suggested_influencers[:3]:
                suitability = c.get("match_reason") or recommendation.generate_suitability_reason(c, raw_message)
                lines.append(f"• @{c['username']} ({c.get('category')}): {suitability}")
            ai_reply = "Here are the best creators matching your criteria:\n" + "\n".join(lines)
        else:
            ai_reply = f"For '{raw_message}', prioritize creators with verified domain expertise and engagement above 2.5% for optimal conversion."

    database.save_chat_message(user_id, "user", raw_message)
    database.save_chat_message(user_id, "assistant", ai_reply)
    database.record_user_search(
        user_id=user_id,
        query=raw_message,
        category="",
        result_count=len(suggested_influencers)
    )

    words = re.findall(r"\b[A-Za-z]{3,}\b", raw_message)
    skip = {"what", "which", "some", "with", "have", "from", "that", "this", "want", "look", "looking", "find", "need", "like", "also", "hello", "help", "who", "are", "the", "best", "for", "please", "show", "give", "tell", "top"}
    meaningful = [w.capitalize() for w in words if w.lower() not in skip]
    if existing_summary:
        old_words = [w.strip() for w in existing_summary.split(",") if w.strip()]
        for ow in old_words:
            if ow not in meaningful:
                meaningful.append(ow)
    summary_topics = list(dict.fromkeys(meaningful))[:5]
    updated_summary = ", ".join(summary_topics) if summary_topics else existing_summary
    if updated_summary:
        database.update_user_summary(user_id, updated_summary)

    updated_recs = recommendation.get_user_recommendations(user_id, top_k=5)

    return {
        "status": "success",
        "reply": ai_reply,
        "recommendations": suggested_influencers[:3],
        "updated_user_recommendations": updated_recs,
        "summary": updated_summary
    }

@app.get("/api/chat/history")
async def api_chat_history(request: Request):
    user = get_current_user(request)
    user_id = user["id"] if user else 1
    history = database.get_user_chat_history(user_id, limit=30)
    return {"history": history}

@app.post("/api/creator/update")
async def api_update_creator(req: CreatorUpdateRequest, request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    if user["role"] not in ["creator", "admin"]:
        raise HTTPException(status_code=403, detail="Forbidden")

    success = database.update_creator_profile(
        username=req.username,
        full_name=req.full_name,
        bio=req.bio,
        category=req.category,
        followers=req.followers,
        engagement_rate=req.engagement_rate
    )
    if not success:
        raise HTTPException(status_code=404, detail="Creator not found")
    return {"status": "success", "message": "Creator profile updated successfully"}

@app.post("/api/admin/add-creator")
async def api_admin_add_creator(req: AdminAddCreatorRequest, request: Request):
    user = get_current_user(request)
    if not user or user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin authorization required")

    uname = req.username.strip().lower().lstrip("@")
    if not uname:
        raise HTTPException(status_code=400, detail="Invalid username")

    try:
        record = add_new_creator(
            username=uname,
            api_token=req.token,
            full_name=req.name,
            bio=req.bio,
            category=req.category,
            followers=req.followers,
            engagement_rate=req.engagement_rate
        )
        recommendation.get_engine().load_index()
        database.sync_creators_from_catalog([record])
        return {"status": "success", "message": f"Creator @{uname} successfully indexed", "creator": record}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/creator/{username}")
async def api_get_creator_details(username: str):
    clean_username = username.strip().lower().lstrip("@")
    if not clean_username:
        raise HTTPException(status_code=400, detail="Invalid username")

    creator_record = database.get_creator_by_username(clean_username)

    engine = recommendation.get_engine()
    df_match = {}
    if not engine.creators_df.empty:
        matches = engine.creators_df[engine.creators_df["username"].str.lower() == clean_username]
        if not matches.empty:
            df_match = matches.iloc[0].to_dict()

    if not creator_record and not df_match:
        raise HTTPException(status_code=404, detail=f"Creator '@{clean_username}' not found")

    def _val(v, default=0.0):
        if v is None or pd.isna(v):
            return default
        try:
            return float(v)
        except Exception:
            return default

    def _val_int(v, default=0):
        if v is None or pd.isna(v):
            return default
        try:
            return int(float(v))
        except Exception:
            return default

    raw_f = (creator_record.get("followers") if creator_record else None) or df_match.get("followers") or df_match.get("followersCount")
    f_num = _val(raw_f, 0.0)

    raw_eng = (creator_record.get("engagement_rate") if creator_record else None) or df_match.get("engagement_rate")
    eng_num = _val(raw_eng, 0.0)

    raw_likes = (creator_record.get("avg_likes") if creator_record else None) or df_match.get("avg_likes")
    avg_likes_num = _val(raw_likes, 0.0)

    raw_comments = df_match.get("avg_comments")
    avg_comments_num = _val(raw_comments, 0.0)

    raw_posts = df_match.get("posts_count") or df_match.get("postsCount")
    posts_count_num = _val_int(raw_posts, 0)

    raw_name = (creator_record.get("full_name") if creator_record else None) or df_match.get("fullName") or df_match.get("full_name")
    full_name = str(raw_name) if raw_name and not pd.isna(raw_name) else clean_username.capitalize()

    raw_bio = (creator_record.get("bio") if creator_record else None) or df_match.get("biography") or df_match.get("bio")
    bio = str(raw_bio) if raw_bio and not pd.isna(raw_bio) else ""

    raw_cat = (creator_record.get("category") if creator_record else None) or df_match.get("category")
    category = str(raw_cat).strip() if raw_cat and not pd.isna(raw_cat) and str(raw_cat).lower() != "nan" else "Creator"

    tier = str(
        (creator_record.get("follower_tier") if creator_record else None)
        or df_match.get("follower_tier")
        or recommendation.get_follower_tier(f_num)
    )
    is_verified = bool(
        (creator_record.get("is_verified") if creator_record else False)
        or df_match.get("verified")
        or df_match.get("is_verified")
    )
    profile_pic = str(
        (creator_record.get("profile_pic_url") if creator_record else None)
        or df_match.get("profilePicUrl")
        or df_match.get("profile_pic_url")
        or ""
    )

    lookalikes = []
    try:
        if not engine.creators_df.empty:
            raw_sim = engine.recommend_similar_creators(clean_username, top_k=4)
            lookalikes = [recommendation.clean_creator_output(r, "Niche lookalike") for r in raw_sim if r.get("username", "").lower() != clean_username]
    except Exception:
        pass

    creator_details = {
        "username": clean_username,
        "full_name": full_name,
        "bio": bio,
        "category": category,
        "followers": int(f_num),
        "followers_formatted": recommendation.format_number(f_num),
        "engagement_rate": eng_num,
        "engagement_formatted": recommendation.format_engagement(eng_num),
        "follower_tier": tier,
        "avg_likes": int(avg_likes_num),
        "avg_likes_formatted": recommendation.format_number(avg_likes_num),
        "avg_comments": int(avg_comments_num),
        "avg_comments_formatted": recommendation.format_number(avg_comments_num),
        "posts_count": posts_count_num,
        "is_verified": is_verified,
        "profile_pic_url": profile_pic,
        "instagram_url": f"https://www.instagram.com/{clean_username}/",
        "lookalikes": lookalikes[:4]
    }

    return {"status": "success", "creator": creator_details}

@app.get("/api/stats")
async def api_stats():
    return database.get_system_stats()

@app.get("/api/creators")
async def api_creators(limit: int = 50, category: Optional[str] = None):
    return database.get_all_creators(limit=limit, category=category)

if __name__ == "__main__":
    import uvicorn
    recommendation.get_engine()
    database.init_db()
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)

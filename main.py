import os
import re
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Request, Response, HTTPException, Depends
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

import database
import recommendation
from add_new_creator import add_new_creator

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

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    user = get_current_user(request)
    if user:
        if user["role"] == "admin":
            return RedirectResponse(url="/admin", status_code=302)
        elif user["role"] == "creator":
            return RedirectResponse(url="/creator", status_code=302)
        return RedirectResponse(url="/", status_code=302)
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
    redirect_map = {"admin": "/admin", "creator": "/creator", "user": "/"}
    target_url = redirect_map.get(user["role"], "/")
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
    redirect_map = {"admin": "/admin", "creator": "/creator", "user": "/"}
    target_url = redirect_map.get(user["role"], "/")
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

@app.get("/", response_class=HTMLResponse)
async def home_dashboard(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    if user["role"] == "admin":
        return RedirectResponse(url="/admin", status_code=302)
    if user["role"] == "creator":
        return RedirectResponse(url="/creator", status_code=302)

    engine = recommendation.get_engine()
    catalog_count = len(engine.creators_df) if not engine.creators_df.empty else 0
    categories = sorted([c for c in engine.creators_df["category"].dropna().unique() if c and str(c).lower() != "nan"])
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

@app.get("/dashboard", response_class=HTMLResponse)
async def user_dashboard_view(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    engine = recommendation.get_engine()
    catalog_count = len(engine.creators_df) if not engine.creators_df.empty else 0
    categories = sorted([c for c in engine.creators_df["category"].dropna().unique() if c and str(c).lower() != "nan"])
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
    if req.query and req.query.strip():
        database.record_user_search(
            user_id=user_id,
            query=req.query.strip(),
            category=req.category or "",
            result_count=search_res.get("count", 0)
        )
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

    system_instruction = (
        "You are the Creator Intelligence AI Advisor. Answer user questions about influencer marketing, "
        "creator discovery, campaign strategy, and brand partnerships. Provide concise, expert, actionable advice "
        "in 1-2 short paragraphs. Cite recommended creators when appropriate."
    )
    if existing_summary:
        system_instruction += f"\nKnown user campaign preferences: {existing_summary}."
    if recent_searches:
        s_list = [s["query"] for s in recent_searches if s.get("query")]
        if s_list:
            system_instruction += f"\nUser recent search topics: {', '.join(s_list[:4])}."

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
                    max_tokens=300,
                    temperature=0.7,
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
            names = ", ".join([f"@{i['username']} ({i['category']})" for i in suggested_influencers[:3]])
            ai_reply = (
                f"Based on your query regarding '{raw_message}', consider collaborating with: {names}. "
                "These creators demonstrate strong audience trust in this segment. Review their past brand partnerships "
                "and average engagement to ensure ideal campaign alignment."
            )
        else:
            ai_reply = (
                f"Regarding '{raw_message}', prioritize creators who maintain an active community dialogue. "
                "Focus on mid-tier creators with engagement rates exceeding 2.5% for authentic conversions."
            )

    database.save_chat_message(user_id, "user", raw_message)
    database.save_chat_message(user_id, "assistant", ai_reply)

    combined_text = f"{raw_message} {existing_summary}".strip()
    words = re.findall(r"\b[A-Za-z]{3,}\b", combined_text)
    skip = {"what", "which", "some", "with", "have", "from", "that", "this", "want", "look", "looking", "find", "need", "like", "also", "hello", "help", "who", "are", "the", "best", "for"}
    meaningful = [w.capitalize() for w in words if w.lower() not in skip]
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

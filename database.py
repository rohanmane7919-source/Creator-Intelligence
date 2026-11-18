import os
import hashlib
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "").strip()

_supabase_client: Optional[Client] = None

def _get_client() -> Optional[Client]:
    global _supabase_client
    if _supabase_client is not None:
        return _supabase_client
    url = os.getenv("SUPABASE_URL", "").strip()
    key = os.getenv("SUPABASE_KEY", "").strip()
    if not url or not key:
        return None
    try:
        _supabase_client = create_client(url, key)
        return _supabase_client
    except Exception:
        return None

def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def init_db():
    client = _get_client()
    if not client:
        return

    default_accounts = [
        ("user", "user@example.com", "user123", "user"),
        ("creator", "creator@example.com", "creator123", "creator"),
        ("admin", "admin@example.com", "admin123", "admin")
    ]
    for uname, email, pwd, role in default_accounts:
        try:
            res = client.table("users_ci").select("id").eq("username", uname).limit(1).execute()
            if not res.data:
                client.table("users_ci").insert({
                    "username": uname,
                    "email": email,
                    "password_hash": _hash_password(pwd),
                    "role": role
                }).execute()
        except Exception:
            continue

def create_user(username: str, password: str, role: str = "user", email: str = "") -> Optional[Dict[str, Any]]:
    clean_username = username.strip().lower()
    if not clean_username or not password:
        return None
    valid_roles = ["user", "creator", "admin"]
    assigned_role = role.lower() if role.lower() in valid_roles else "user"
    client = _get_client()
    if not client:
        return None
    try:
        res = client.table("users_ci").insert({
            "username": clean_username,
            "email": email.strip(),
            "password_hash": _hash_password(password),
            "role": assigned_role
        }).execute()
        if res.data and len(res.data) > 0:
            return res.data[0]
        return None
    except Exception:
        return None

def authenticate_user(username: str, password: str, role: Optional[str] = None) -> Optional[Dict[str, Any]]:
    clean_username = username.strip().lower()
    hashed = _hash_password(password)
    client = _get_client()
    if not client:
        return None
    try:
        query = client.table("users_ci").select("id, username, email, role, created_at").eq("username", clean_username).eq("password_hash", hashed)
        if role:
            query = query.eq("role", role.lower())
        res = query.limit(1).execute()
        if res.data and len(res.data) > 0:
            return res.data[0]
        return None
    except Exception:
        return None

def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    client = _get_client()
    if not client:
        return None
    try:
        res = client.table("users_ci").select("id, username, email, role, created_at").eq("id", user_id).limit(1).execute()
        if res.data and len(res.data) > 0:
            return res.data[0]
        return None
    except Exception:
        return None

def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    clean_username = username.strip().lower()
    client = _get_client()
    if not client:
        return None
    try:
        res = client.table("users_ci").select("id, username, email, role, created_at").eq("username", clean_username).limit(1).execute()
        if res.data and len(res.data) > 0:
            return res.data[0]
        return None
    except Exception:
        return None

def get_all_users() -> List[Dict[str, Any]]:
    client = _get_client()
    if not client:
        return []
    try:
        res = client.table("users_ci").select("id, username, email, role, created_at").order("id", desc=True).execute()
        return res.data if res.data else []
    except Exception:
        return []

def record_user_search(user_id: int, query: str, category: str = "", result_count: int = 0) -> bool:
    clean_query = query.strip()
    if not clean_query:
        return False
    client = _get_client()
    if not client:
        return False
    try:
        client.table("search_history").insert({
            "user_id": user_id,
            "query": clean_query,
            "category": category,
            "result_count": result_count
        }).execute()
        return True
    except Exception:
        return False

def get_user_recent_searches(user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
    client = _get_client()
    if not client:
        return []
    try:
        res = client.table("search_history").select("id, query, category, result_count, created_at").eq("user_id", user_id).order("id", desc=True).limit(limit).execute()
        return res.data if res.data else []
    except Exception:
        return []

def get_all_searches(limit: int = 50) -> List[Dict[str, Any]]:
    client = _get_client()
    if not client:
        return []
    try:
        res = client.table("search_history").select("id, user_id, query, category, result_count, created_at").order("id", desc=True).limit(limit).execute()
        searches = res.data if res.data else []
        if searches:
            user_ids = list({s["user_id"] for s in searches if s.get("user_id")})
            if user_ids:
                u_res = client.table("users_ci").select("id, username").in_("id", user_ids).execute()
                u_map = {u["id"]: u["username"] for u in (u_res.data or [])}
                for s in searches:
                    s["username"] = u_map.get(s["user_id"], f"user_{s['user_id']}")
        return searches
    except Exception:
        return []

def save_chat_message(user_id: int, role: str, content: str) -> bool:
    clean_content = content.strip()
    if not clean_content:
        return False
    client = _get_client()
    if not client:
        return False
    try:
        client.table("chat_messages").insert({
            "user_id": user_id,
            "role": role,
            "content": clean_content
        }).execute()
        return True
    except Exception:
        return False

def get_user_chat_history(user_id: int, limit: int = 20) -> List[Dict[str, Any]]:
    client = _get_client()
    if not client:
        return []
    try:
        res = client.table("chat_messages").select("id, role, content, created_at").eq("user_id", user_id).order("id", desc=True).limit(limit).execute()
        data = res.data if res.data else []
        data.reverse()
        return data
    except Exception:
        return []

def update_user_summary(user_id: int, summary_text: str) -> bool:
    client = _get_client()
    if not client:
        return False
    try:
        client.table("user_preferences").upsert({
            "user_id": user_id,
            "summary_text": summary_text.strip()
        }).execute()
        return True
    except Exception:
        return False

def get_user_summary(user_id: int) -> str:
    client = _get_client()
    if not client:
        return ""
    try:
        res = client.table("user_preferences").select("summary_text").eq("user_id", user_id).limit(1).execute()
        if res.data and len(res.data) > 0:
            return str(res.data[0].get("summary_text") or "")
        return ""
    except Exception:
        return ""

def sync_creators_from_catalog(creators: List[Dict[str, Any]]) -> int:
    if not creators:
        return 0
    client = _get_client()
    if not client:
        return 0
    records = []
    for c in creators:
        uname = str(c.get("username", "")).strip().lower().lstrip("@")
        if not uname:
            continue
        followers_val = float(c.get("followers") or c.get("followersCount") or 0.0)
        eng_val = float(c.get("engagement_rate") or 0.0)
        records.append({
            "username": uname,
            "full_name": str(c.get("full_name") or c.get("fullName") or uname),
            "bio": str(c.get("bio") or c.get("biography") or ""),
            "category": str(c.get("category") or "Uncategorized"),
            "followers": followers_val,
            "engagement_rate": eng_val,
            "follower_tier": str(c.get("follower_tier") or "Unknown"),
            "avg_likes": float(c.get("avg_likes") or 0.0),
            "profile_pic_url": str(c.get("profile_pic_url") or c.get("profilePicUrl") or ""),
            "is_verified": 1 if c.get("is_verified") or c.get("verified") else 0
        })
    count = 0
    batch_size = 50
    for i in range(0, len(records), batch_size):
        batch = records[i:i + batch_size]
        try:
            client.table("creators").upsert(batch, on_conflict="username").execute()
            count += len(batch)
        except Exception:
            continue
    return count

def get_all_creators(limit: int = 100, category: Optional[str] = None) -> List[Dict[str, Any]]:
    client = _get_client()
    if not client:
        return []
    try:
        query = client.table("creators").select("*")
        if category:
            query = query.ilike("category", f"%{category}%")
        res = query.order("followers", desc=True).limit(limit).execute()
        return res.data if res.data else []
    except Exception:
        return []

def get_creator_by_username(username: str) -> Optional[Dict[str, Any]]:
    clean_username = username.strip().lower().lstrip("@")
    client = _get_client()
    if not client:
        return None
    try:
        res = client.table("creators").select("*").eq("username", clean_username).limit(1).execute()
        if res.data and len(res.data) > 0:
            return res.data[0]
        return None
    except Exception:
        return None

def update_creator_profile(username: str, full_name: Optional[str] = None, bio: Optional[str] = None, category: Optional[str] = None, followers: Optional[float] = None, engagement_rate: Optional[float] = None) -> bool:
    clean_username = username.strip().lower().lstrip("@")
    client = _get_client()
    if not client:
        return False
    try:
        res = client.table("creators").select("*").eq("username", clean_username).limit(1).execute()
        if not res.data or len(res.data) == 0:
            return False
        existing = res.data[0]
        new_full_name = full_name if full_name is not None else existing.get("full_name", "")
        new_bio = bio if bio is not None else existing.get("bio", "")
        new_category = category if category is not None else existing.get("category", "")
        new_followers = followers if followers is not None else existing.get("followers", 0.0)
        new_engagement = engagement_rate if engagement_rate is not None else existing.get("engagement_rate", 0.0)

        tier = existing.get("follower_tier", "Unknown")
        if new_followers is not None:
            if new_followers < 10000:
                tier = "Nano (<10K)"
            elif new_followers < 100000:
                tier = "Micro (10K-100K)"
            elif new_followers < 500000:
                tier = "Mid-Tier (100K-500K)"
            elif new_followers < 1000000:
                tier = "Macro (500K-1M)"
            else:
                tier = "Mega (1M+)"

        client.table("creators").update({
            "full_name": new_full_name,
            "bio": new_bio,
            "category": new_category,
            "followers": new_followers,
            "engagement_rate": new_engagement,
            "follower_tier": tier
        }).eq("username", clean_username).execute()
        return True
    except Exception:
        return False

def get_system_stats() -> Dict[str, Any]:
    client = _get_client()
    if not client:
        return {
            "total_users": 0,
            "total_creators": 0,
            "total_searches": 0,
            "total_chats": 0
        }
    try:
        u_res = client.table("users_ci").select("id", count="exact").limit(1).execute()
        c_res = client.table("creators").select("id", count="exact").limit(1).execute()
        s_res = client.table("search_history").select("id", count="exact").limit(1).execute()
        m_res = client.table("chat_messages").select("id", count="exact").limit(1).execute()
        return {
            "total_users": u_res.count if u_res.count is not None else len(u_res.data or []),
            "total_creators": c_res.count if c_res.count is not None else len(c_res.data or []),
            "total_searches": s_res.count if s_res.count is not None else len(s_res.data or []),
            "total_chats": m_res.count if m_res.count is not None else len(m_res.data or [])
        }
    except Exception:
        return {
            "total_users": 0,
            "total_creators": 0,
            "total_searches": 0,
            "total_chats": 0
        }

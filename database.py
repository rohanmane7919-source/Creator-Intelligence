import sqlite3
import os
import hashlib
from typing import Optional, List, Dict, Any

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "creator_intelligence.db")

def _get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def init_db():
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS search_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            query TEXT NOT NULL,
            category TEXT DEFAULT '',
            result_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_preferences (
            user_id INTEGER PRIMARY KEY,
            summary_text TEXT DEFAULT '',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS creators (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            full_name TEXT DEFAULT '',
            bio TEXT DEFAULT '',
            category TEXT DEFAULT '',
            followers REAL DEFAULT 0,
            engagement_rate REAL DEFAULT 0,
            follower_tier TEXT DEFAULT 'Unknown',
            avg_likes REAL DEFAULT 0,
            profile_pic_url TEXT DEFAULT '',
            is_verified INTEGER DEFAULT 0
        )
    """)
    conn.commit()

    default_accounts = [
        ("user", "user@example.com", "user123", "user"),
        ("creator", "creator@example.com", "creator123", "creator"),
        ("admin", "admin@example.com", "admin123", "admin")
    ]
    for uname, email, pwd, role in default_accounts:
        cursor.execute("SELECT id FROM users WHERE username = ?", (uname,))
        if not cursor.fetchone():
            cursor.execute(
                "INSERT INTO users (username, email, password_hash, role) VALUES (?, ?, ?, ?)",
                (uname, email, _hash_password(pwd), role)
            )
    conn.commit()
    conn.close()

def create_user(username: str, password: str, role: str = "user", email: str = "") -> Optional[Dict[str, Any]]:
    clean_username = username.strip().lower()
    if not clean_username or not password:
        return None
    valid_roles = ["user", "creator", "admin"]
    assigned_role = role.lower() if role.lower() in valid_roles else "user"
    conn = _get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO users (username, email, password_hash, role) VALUES (?, ?, ?, ?)",
            (clean_username, email.strip(), _hash_password(password), assigned_role)
        )
        conn.commit()
        user_id = cursor.lastrowid
        conn.close()
        return {"id": user_id, "username": clean_username, "email": email.strip(), "role": assigned_role}
    except sqlite3.IntegrityError:
        conn.close()
        return None

def authenticate_user(username: str, password: str, role: Optional[str] = None) -> Optional[Dict[str, Any]]:
    clean_username = username.strip().lower()
    hashed = _hash_password(password)
    conn = _get_connection()
    cursor = conn.cursor()
    if role:
        cursor.execute(
            "SELECT id, username, email, role, created_at FROM users WHERE username = ? AND password_hash = ? AND role = ?",
            (clean_username, hashed, role.lower())
        )
    else:
        cursor.execute(
            "SELECT id, username, email, role, created_at FROM users WHERE username = ? AND password_hash = ?",
            (clean_username, hashed)
        )
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None

def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, email, role, created_at FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, email, role, created_at FROM users WHERE username = ?", (username.strip().lower(),))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_all_users() -> List[Dict[str, Any]]:
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, email, role, created_at FROM users ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def record_user_search(user_id: int, query: str, category: str = "", result_count: int = 0) -> bool:
    clean_query = query.strip()
    if not clean_query:
        return False
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO search_history (user_id, query, category, result_count) VALUES (?, ?, ?, ?)",
        (user_id, clean_query, category, result_count)
    )
    conn.commit()
    conn.close()
    return True

def get_user_recent_searches(user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, query, category, result_count, created_at FROM search_history WHERE user_id = ? ORDER BY id DESC LIMIT ?",
        (user_id, limit)
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_all_searches(limit: int = 50) -> List[Dict[str, Any]]:
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.id, s.user_id, u.username, s.query, s.category, s.result_count, s.created_at
        FROM search_history s
        LEFT JOIN users u ON s.user_id = u.id
        ORDER BY s.id DESC
        LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def save_chat_message(user_id: int, role: str, content: str) -> bool:
    clean_content = content.strip()
    if not clean_content:
        return False
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO chat_messages (user_id, role, content) VALUES (?, ?, ?)",
        (user_id, role, clean_content)
    )
    conn.commit()
    conn.close()
    return True

def get_user_chat_history(user_id: int, limit: int = 20) -> List[Dict[str, Any]]:
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, role, content, created_at FROM (
            SELECT id, role, content, created_at FROM chat_messages
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT ?
        ) ORDER BY id ASC
    """, (user_id, limit))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def update_user_summary(user_id: int, summary_text: str) -> bool:
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO user_preferences (user_id, summary_text, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(user_id) DO UPDATE SET
            summary_text = excluded.summary_text,
            updated_at = CURRENT_TIMESTAMP
    """, (user_id, summary_text.strip()))
    conn.commit()
    conn.close()
    return True

def get_user_summary(user_id: int) -> str:
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT summary_text FROM user_preferences WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return str(row["summary_text"]) if row and row["summary_text"] else ""

def sync_creators_from_catalog(creators: List[Dict[str, Any]]) -> int:
    if not creators:
        return 0
    conn = _get_connection()
    cursor = conn.cursor()
    count = 0
    for c in creators:
        uname = str(c.get("username", "")).strip().lower().lstrip("@")
        if not uname:
            continue
        cursor.execute("""
            INSERT INTO creators (username, full_name, bio, category, followers, engagement_rate, follower_tier, avg_likes, profile_pic_url, is_verified)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(username) DO UPDATE SET
                full_name = excluded.full_name,
                bio = excluded.bio,
                category = excluded.category,
                followers = excluded.followers,
                engagement_rate = excluded.engagement_rate,
                follower_tier = excluded.follower_tier,
                avg_likes = excluded.avg_likes,
                profile_pic_url = excluded.profile_pic_url,
                is_verified = excluded.is_verified
        """, (
            uname,
            str(c.get("full_name") or c.get("fullName") or uname),
            str(c.get("bio") or c.get("biography") or ""),
            str(c.get("category") or "Uncategorized"),
            float(c.get("followers") or c.get("followersCount") or 0.0),
            float(c.get("engagement_rate") or 0.0),
            str(c.get("follower_tier") or "Unknown"),
            float(c.get("avg_likes") or 0.0),
            str(c.get("profile_pic_url") or c.get("profilePicUrl") or ""),
            1 if c.get("is_verified") or c.get("verified") else 0
        ))
        count += 1
    conn.commit()
    conn.close()
    return count

def get_all_creators(limit: int = 100, category: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = _get_connection()
    cursor = conn.cursor()
    if category:
        cursor.execute(
            "SELECT * FROM creators WHERE category LIKE ? ORDER BY followers DESC LIMIT ?",
            (f"%{category}%", limit)
        )
    else:
        cursor.execute(
            "SELECT * FROM creators ORDER BY followers DESC LIMIT ?",
            (limit,)
        )
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_creator_by_username(username: str) -> Optional[Dict[str, Any]]:
    clean_username = username.strip().lower().lstrip("@")
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM creators WHERE username = ?", (clean_username,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def update_creator_profile(username: str, full_name: Optional[str] = None, bio: Optional[str] = None, category: Optional[str] = None, followers: Optional[float] = None, engagement_rate: Optional[float] = None) -> bool:
    clean_username = username.strip().lower().lstrip("@")
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM creators WHERE username = ?", (clean_username,))
    existing = cursor.fetchone()
    if not existing:
        conn.close()
        return False
    
    new_full_name = full_name if full_name is not None else existing["full_name"]
    new_bio = bio if bio is not None else existing["bio"]
    new_category = category if category is not None else existing["category"]
    new_followers = followers if followers is not None else existing["followers"]
    new_engagement = engagement_rate if engagement_rate is not None else existing["engagement_rate"]

    tier = existing["follower_tier"]
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

    cursor.execute("""
        UPDATE creators
        SET full_name = ?, bio = ?, category = ?, followers = ?, engagement_rate = ?, follower_tier = ?
        WHERE username = ?
    """, (new_full_name, new_bio, new_category, new_followers, new_engagement, tier, clean_username))
    conn.commit()
    conn.close()
    return True

def get_system_stats() -> Dict[str, Any]:
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as count FROM users")
    total_users = cursor.fetchone()["count"]
    cursor.execute("SELECT COUNT(*) as count FROM creators")
    total_creators = cursor.fetchone()["count"]
    cursor.execute("SELECT COUNT(*) as count FROM search_history")
    total_searches = cursor.fetchone()["count"]
    cursor.execute("SELECT COUNT(*) as count FROM chat_messages")
    total_chats = cursor.fetchone()["count"]
    conn.close()
    return {
        "total_users": total_users,
        "total_creators": total_creators,
        "total_searches": total_searches,
        "total_chats": total_chats
    }

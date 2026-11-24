import os
import re
from typing import Optional, List, Dict, Any
import pandas as pd
import numpy as np

try:
    from . import database
    from .creator_recommender import CreatorRecommender, INDEX_FILE, get_follower_tier, PROFILES_CSV, POSTS_CSV
except ImportError:
    import database
    from creator_recommender import CreatorRecommender, INDEX_FILE, get_follower_tier, PROFILES_CSV, POSTS_CSV

recommender_instance: Optional[CreatorRecommender] = None

def get_engine() -> CreatorRecommender:
    global recommender_instance
    if recommender_instance is None:
        recommender_instance = CreatorRecommender()
        index_path = INDEX_FILE
        if os.path.exists(index_path):
            recommender_instance.load_index(index_path)
        else:
            recommender_instance.build_creator_catalog(profiles_path=PROFILES_CSV, posts_path=POSTS_CSV)
            recommender_instance.fit()
            recommender_instance.save_index(index_path)
    return recommender_instance

def format_number(val: float) -> str:
    if not val or pd.isna(val) or val <= 0:
        return "0"
    if val >= 1_000_000_000:
        return f"{val / 1_000_000_000:.1f}B"
    if val >= 1_000_000:
        return f"{val / 1_000_000:.1f}M"
    if val >= 1_000:
        return f"{val / 1_000:.1f}K"
    return str(int(val))

def format_engagement(val: float) -> str:
    if not val or pd.isna(val) or val <= 0:
        return "0.0%"
    pct = val * 100 if val <= 1.0 else val
    return f"{pct:.2f}%"

def generate_suitability_reason(row: Dict[str, Any], query: str = "") -> str:
    """Generates a dedicated, single-line explanation of why this creator is suitable for the user."""
    cat = str(row.get("category") or "General")
    cat_l = cat.lower()
    eng_val = float(row.get("engagement_rate", 0) or 0)
    eng = row.get("engagement_formatted") or format_engagement(eng_val)
    f_val = float(row.get("followers", 0) or 0)
    followers = row.get("followers_formatted") or format_number(f_val)
    bio = str(row.get("bio") or row.get("biography") or "").strip()
    bio_l = bio.lower()

    if "tech" in cat_l:
        if bool(re.search(r"\bai\b", bio_l)) or "neural" in bio_l or "deep learning" in bio_l:
            return f"Suitable for AI, software innovation, and deep-tech education reaching {followers} tech professionals."
        return f"Suitable for in-depth tech teardowns, trusted hardware benchmarks, and gadget reviews with {eng} engagement."
    elif "fit" in cat_l or "sport" in cat_l:
        if "olympia" in bio_l or "bodybuild" in bio_l or "heavy" in bio_l or "strength" in bio_l:
            return f"Suitable for high-intensity bodybuilding, heavy lifting, and athletic performance campaigns with {followers} followers."
        return f"Suitable for accessible workout routines, fat-loss challenges, and active community fitness motivation ({eng} engagement)."
    elif "beauty" in cat_l or "cosmetic" in cat_l:
        if "skincare" in bio_l or "serum" in bio_l or "barrier" in bio_l or "sunscreen" in bio_l:
            return f"Suitable for skincare education, ingredient breakdowns, and glowing skin routines with {followers} fans."
        return f"Suitable for transformative makeup artistry, glam tutorials, and high-impact cosmetic testing ({eng} engagement)."
    elif "fashion" in cat_l or "model" in cat_l:
        if "couture" in bio_l or "runway" in bio_l or "luxury" in bio_l or "paris" in bio_l:
            return f"Suitable for luxury fashion houses, haute couture styling, and runway-tier brand partnerships."
        return f"Suitable for modern streetwear, trendy outfit lookbooks, and aesthetic lifestyle styling ({eng} engagement)."
    elif eng_val >= 0.04:
        return f"Suitable for high-conversion ROI campaigns driven by an outstanding {eng} audience engagement rate."
    else:
        return f"Suitable for targeted {cat} partnerships with an active audience of {followers} followers and {eng} engagement."

def clean_creator_output(row: Dict[str, Any], reason: str = "") -> Dict[str, Any]:
    followers_num = float(row.get("followers", 0) or 0)
    eng_num = float(row.get("engagement_rate", 0) or 0)
    final_reason = reason.strip() if reason and reason.strip() else generate_suitability_reason(row)
    return {
        "username": str(row.get("username", "")).strip().lstrip("@"),
        "full_name": str(row.get("full_name") or row.get("fullName") or row.get("username", "")),
        "category": str(row.get("category") or "General"),
        "bio": str(row.get("bio") or row.get("biography") or ""),
        "followers": int(followers_num),
        "followers_formatted": format_number(followers_num),
        "engagement_rate": float(eng_num),
        "engagement_formatted": format_engagement(eng_num),
        "follower_tier": str(row.get("follower_tier") or get_follower_tier(followers_num)),
        "profile_pic_url": str(row.get("profilePicUrl") or row.get("profile_pic_url") or ""),
        "match_reason": final_reason
    }

def search_influencers(
    query: str = "",
    mode: str = "auto",
    category: Optional[str] = None,
    follower_tier: Optional[str] = None,
    min_followers: Optional[float] = None,
    max_followers: Optional[float] = None,
    min_engagement: Optional[float] = None,
    top_k: int = 8
) -> Dict[str, Any]:
    engine = get_engine()
    raw_query = str(query or "").strip()
    df = engine.creators_df

    if df.empty:
        return {"type": "empty", "results": [], "count": 0}

    is_similarity = False
    target_handle = ""
    similar_match = re.match(r"^(?:similar\s+to|similar|like|lookalikes?\s+for|lookalikes?)\s+[@]?([a-zA-Z0-9._]+)$", raw_query, re.IGNORECASE)

    if mode == "similar":
        is_similarity = True
        target_handle = raw_query.lstrip("@").strip()
    elif similar_match:
        is_similarity = True
        target_handle = similar_match.group(1).lstrip("@").strip()

    if is_similarity:
        clean_handle = target_handle.lower()
        exists = (df["username"].str.lower() == clean_handle).any()
        if not exists:
            matches = df[df["username"].str.lower().str.contains(clean_handle, na=False)]
            if not matches.empty:
                clean_handle = matches.iloc[0]["username"]
                exists = True
        if not exists:
            return {
                "type": "similarity_error",
                "message": f"Creator '@{target_handle}' not found in catalog.",
                "results": [],
                "count": 0
            }
        raw_results = engine.recommend_similar_creators(clean_handle, top_k=top_k)
        formatted = [clean_creator_output(r, f"Similar content to @{clean_handle}") for r in raw_results]
        return {
            "type": "similarity",
            "target_creator": clean_handle,
            "results": formatted[:top_k],
            "count": len(formatted[:top_k])
        }

    q_lower = raw_query.lower()
    q_alphanumeric = re.sub(r'[^a-z0-9]', '', q_lower)

    max_eng = df["engagement_rate"].max()
    if max_eng <= 0:
        max_eng = 1.0

    vector_scores = np.zeros(len(df))
    if raw_query and engine.vectorizer and engine.tfidf_matrix is not None:
        try:
            from sklearn.metrics.pairwise import cosine_similarity
            query_vec = engine.vectorizer.transform([raw_query])
            vector_scores = cosine_similarity(query_vec, engine.tfidf_matrix).flatten()
        except Exception:
            vector_scores = np.zeros(len(df))

    scored_candidates = []
    for idx, row in df.iterrows():
        uname = str(row.get("username", "")).lower()
        uname_alpha = re.sub(r'[^a-z0-9]', '', uname)
        fname = str(row.get("fullName", "")).lower()
        cat = str(row.get("category", "")).lower()
        bio = str(row.get("bio", "")).lower()
        f_tier = str(row.get("follower_tier", "")).lower()
        followers_val = float(row.get("followers", 0) or 0)
        eng_val = float(row.get("engagement_rate", 0) or 0)

        if category:
            cat_target = category.lower().strip()
            cat_aliases = {
                "fashion": ["fashion", "style", "apparel", "model", "clothing"],
                "beauty": ["beauty", "makeup", "cosmetics", "skincare", "glam"],
                "technology": ["technology", "tech", "gadget", "software", "code", "ai", "hardware", "engineering"],
                "fitness": ["fitness", "gym", "workout", "bodybuilding", "trainer", "athlet", "sport", "health"]
            }
            aliases = cat_aliases.get(cat_target, [cat_target])
            def match_alias(alias: str) -> bool:
                pattern = rf"\b{re.escape(alias)}\b"
                if len(alias) <= 3:
                    return bool(re.search(pattern, cat) or re.search(pattern, bio))
                return bool(alias in cat or re.search(pattern, bio))

            if not any(match_alias(a) for a in aliases):
                continue
        if follower_tier and follower_tier.lower() not in f_tier:
            continue
        if min_followers is not None and followers_val < min_followers:
            continue
        if max_followers is not None and followers_val > max_followers:
            continue
        if min_engagement is not None and eng_val < min_engagement:
            continue

        keyword_score = 0.0
        reason = "Matched query"

        if q_lower:
            if q_lower == uname or q_lower == f"@{uname}":
                keyword_score += 50.0
                reason = f"Exact creator handle match: @{uname}"
            elif q_alphanumeric and q_alphanumeric == uname_alpha:
                keyword_score += 40.0
                reason = f"Handle match: @{uname}"
            elif q_alphanumeric and len(q_alphanumeric) >= 3 and q_alphanumeric in uname_alpha:
                keyword_score += 25.0
                reason = f"Creator profile: @{uname}"
            elif q_lower in fname:
                keyword_score += 20.0
                reason = f"Creator name match: {row.get('fullName', uname)}"
            elif q_lower in cat:
                keyword_score += 15.0
                reason = f"Niche category match: {row.get('category', 'Creator')}"
            elif q_lower in bio:
                keyword_score += 10.0
                reason = "Content bio keyword match"

            stop_words = {"the", "and", "for", "with", "who", "are", "best", "some", "what", "which", "from", "that", "this", "can", "you", "all", "about", "have", "has", "more", "give", "show", "tell", "find", "good", "most"}
            tokens = [t for t in re.findall(r'[a-z0-9]{3,}', q_lower) if len(t) >= 3 and t not in stop_words]
            for token in tokens:
                if token in uname:
                    keyword_score += 8.0
                elif token in fname:
                    keyword_score += 6.0
                elif token in cat:
                    keyword_score += 5.0
                elif token in bio:
                    keyword_score += 3.0

        v_sim = float(vector_scores[idx]) if idx < len(vector_scores) else 0.0
        eng_norm = min(eng_val / max_eng, 1.0)
        total_score = keyword_score + (v_sim * 10.0) + (eng_norm * 2.0)

        if raw_query:
            if keyword_score > 0 or v_sim > 0.05:
                scored_candidates.append({
                    "score": total_score,
                    "row": row.to_dict(),
                    "reason": reason
                })
        else:
            scored_candidates.append({
                "score": total_score + eng_norm,
                "row": row.to_dict(),
                "reason": "Top creator in selected filter"
            })

    scored_candidates.sort(key=lambda x: x["score"], reverse=True)

    if not scored_candidates and raw_query:
        tokens = [t for t in re.findall(r'[a-z0-9]{3,}', q_lower) if len(t) >= 3 and t not in stop_words]
        for idx, row in df.iterrows():
            bio = str(row.get("bio", "")).lower()
            cat = str(row.get("category", "")).lower()
            for t in tokens:
                if t in bio or t in cat:
                    scored_candidates.append({
                        "score": 1.0,
                        "row": row.to_dict(),
                        "reason": f"Relevant topic match: '{t}'"
                    })
                    break
        scored_candidates.sort(key=lambda x: x["score"], reverse=True)

    results = []
    seen = set()
    for item in scored_candidates:
        r_dict = item["row"]
        uname = str(r_dict.get("username", "")).strip().lower()
        if uname in seen:
            continue
        seen.add(uname)
        results.append(clean_creator_output(r_dict, item["reason"]))
        if len(results) >= top_k:
            break

    return {
        "type": "query",
        "query": raw_query,
        "results": results,
        "count": len(results)
    }

def get_curated_baseline(top_k: int = 5) -> List[Dict[str, Any]]:
    engine = get_engine()
    df = engine.creators_df
    if df.empty:
        return []
    sorted_df = df.sort_values(by=["followers", "engagement_rate"], ascending=[False, False])
    unique_categories = []
    selected_indices = []
    for idx, row in sorted_df.iterrows():
        cat = str(row.get("category", "")).strip()
        if cat and cat not in unique_categories:
            unique_categories.append(cat)
            selected_indices.append(idx)
        if len(selected_indices) >= top_k:
            break
    if len(selected_indices) < top_k:
        for idx in sorted_df.index:
            if idx not in selected_indices:
                selected_indices.append(idx)
            if len(selected_indices) >= top_k:
                break
    results = []
    for idx in selected_indices[:top_k]:
        row_dict = sorted_df.loc[idx].to_dict()
        results.append(clean_creator_output(row_dict, "Trending & highly engaging creator in catalog"))
    return results[:top_k]

def get_user_recommendations(user_id: int, top_k: int = 5) -> List[Dict[str, Any]]:
    searches = database.get_user_recent_searches(user_id, limit=6)
    user_summary = database.get_user_summary(user_id)
    chat_history = database.get_user_chat_history(user_id, limit=4)

    has_activity = bool(searches or user_summary or chat_history)
    if not has_activity:
        return get_curated_baseline(top_k=top_k)

    engine = get_engine()
    df = engine.creators_df
    if df.empty:
        return []

    intents = []
    seen_keys = set()
    for s in searches:
        q = (s.get("query") or "").strip()
        cat = (s.get("category") or "").strip()
        key = (q.lower(), cat.lower())
        if (q or cat) and key not in seen_keys:
            seen_keys.add(key)
            intents.append({"query": q, "category": cat or None, "source": "search"})

    user_msgs = [c.get("content", "").strip() for c in chat_history if c.get("role") == "user" and c.get("content")]
    for msg in reversed(user_msgs):
        if msg and msg.lower() not in [i["query"].lower() for i in intents]:
            intents.append({"query": msg, "category": None, "source": "chat"})

    if user_summary and user_summary.lower() not in [i["query"].lower() for i in intents]:
        intents.append({"query": user_summary, "category": None, "source": "summary"})

    if not intents:
        return get_curated_baseline(top_k=top_k)

    final_picks = []
    seen_usernames = set()

    for intent_idx, intent in enumerate(intents):
        q = intent["query"]
        cat = intent["category"]
        if not q and not cat:
            continue

        clean_handle = q.lstrip("@").strip().lower()
        is_creator_handle = (df["username"].str.lower() == clean_handle).any()

        candidates = []
        if is_creator_handle:
            raw_sim = engine.recommend_similar_creators(clean_handle, top_k=top_k + 2)
            for r in raw_sim:
                if str(r.get("username", "")).lower() != clean_handle:
                    candidates.append({
                        "creator": clean_creator_output(r, f"Similar to @{clean_handle} from recent search"),
                        "score": 10.0
                    })
        else:
            needed = top_k - len(final_picks)
            if needed <= 0:
                break
            alloc = top_k if intent_idx == 0 else max(1, needed)
            res = search_influencers(query=q, category=cat, top_k=alloc + 3)
            reason_label = f"Based on your recent search for '{q}'" if intent["source"] == "search" else f"Personalized for '{q}'"
            for c in res.get("results", []):
                candidates.append({
                    "creator": clean_creator_output(c, reason_label),
                    "score": 5.0 - (intent_idx * 0.5)
                })

        for item in candidates:
            c = item["creator"]
            uname = c["username"].lower()
            if uname not in seen_usernames:
                seen_usernames.add(uname)
                final_picks.append(c)
                if len(final_picks) >= top_k:
                    break

        if len(final_picks) >= top_k:
            break

    if len(final_picks) < top_k:
        fallback = get_curated_baseline(top_k=top_k)
        for fb in fallback:
            uname = fb["username"].lower()
            if uname not in seen_usernames:
                seen_usernames.add(uname)
                final_picks.append(fb)
            if len(final_picks) == top_k:
                break

    return final_picks[:top_k]

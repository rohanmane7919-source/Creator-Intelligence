import os
import re
from typing import Optional, List, Dict, Any
import pandas as pd
import numpy as np

import database
from creator_recommender import CreatorRecommender, INDEX_FILE, get_follower_tier

recommender_instance: Optional[CreatorRecommender] = None

def get_engine() -> CreatorRecommender:
    global recommender_instance
    if recommender_instance is None:
        recommender_instance = CreatorRecommender()
        base_dir = os.path.dirname(os.path.abspath(__file__))
        index_path = os.path.join(base_dir, INDEX_FILE)
        if os.path.exists(index_path):
            recommender_instance.load_index(index_path)
        else:
            recommender_instance.build_creator_catalog()
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

def clean_creator_output(row: Dict[str, Any], reason: str = "") -> Dict[str, Any]:
    followers_num = float(row.get("followers", 0) or 0)
    eng_num = float(row.get("engagement_rate", 0) or 0)
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
        "match_reason": reason
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

        if category and category.lower() not in cat:
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

            tokens = [t for t in re.findall(r'[a-z0-9]{3,}', q_lower) if len(t) >= 3]
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
        tokens = [t for t in re.findall(r'[a-z0-9]{3,}', q_lower) if len(t) >= 3]
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
    searches = database.get_user_recent_searches(user_id, limit=8)
    user_summary = database.get_user_summary(user_id)
    chat_history = database.get_user_chat_history(user_id, limit=6)

    has_activity = bool(searches or user_summary or chat_history)
    if not has_activity:
        return get_curated_baseline(top_k=top_k)

    engine = get_engine()
    if engine.creators_df.empty:
        return []

    tokens = []
    reason_topic = ""
    for idx, s in enumerate(searches):
        q = s.get("query", "").strip()
        if q:
            weight = 3 if idx == 0 else 1
            tokens.extend([q] * weight)
            if not reason_topic:
                reason_topic = q

    if user_summary:
        tokens.append(user_summary)
        if not reason_topic:
            reason_topic = user_summary

    user_msgs = [c.get("content", "") for c in chat_history if c.get("role") == "user"]
    if user_msgs:
        recent_msg = " ".join(user_msgs[-3:])
        tokens.append(recent_msg)
        if not reason_topic:
            reason_topic = user_msgs[-1][:30]

    combined_context = " ".join(tokens).strip()
    if not combined_context:
        return get_curated_baseline(top_k=top_k)

    search_pack = search_influencers(query=combined_context, top_k=15)
    candidates = search_pack.get("results", [])

    seen = set()
    final_picks = []
    for c in candidates:
        uname = c["username"].lower()
        if uname in seen:
            continue
        seen.add(uname)
        c_copy = dict(c)
        c_copy["match_reason"] = f"Personalized for you based on '{reason_topic}'"
        final_picks.append(c_copy)
        if len(final_picks) == top_k:
            break

    if len(final_picks) < top_k:
        fallback = get_curated_baseline(top_k=top_k)
        for fb in fallback:
            uname = fb["username"].lower()
            if uname not in seen:
                seen.add(uname)
                final_picks.append(fb)
            if len(final_picks) == top_k:
                break

    return final_picks[:top_k]

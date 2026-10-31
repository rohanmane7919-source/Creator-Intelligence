import os
import re
import pickle
import numpy as np
import pandas as pd
from typing import List, Dict, Optional, Any
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

INDEX_FILE = "creator_vector_index.pkl"
PROFILES_CSV = "creator_profiles.csv"
POSTS_CSV = "instagram_posts.csv"

def get_follower_tier(followers: float) -> str:
    """Categorize creators by follower count tiers."""
    if pd.isna(followers) or followers <= 0:
        return "Unknown"
    elif followers < 10_000:
        return "Nano (<10K)"
    elif followers < 100_000:
        return "Micro (10K-100K)"
    elif followers < 500_000:
        return "Mid-Tier (100K-500K)"
    elif followers < 1_000_000:
        return "Macro (500K-1M)"
    else:
        return "Mega (1M+)"

def clean_text(text: Any) -> str:
    """Clean and normalize text fields."""
    if not text or pd.isna(text):
        return ""
    text_str = str(text)
    # Remove URL links
    text_str = re.sub(r"https?://\S+|www\.\S+", "", text_str)
    # Normalize extra whitespace
    text_str = re.sub(r"\s+", " ", text_str).strip()
    return text_str

class CreatorRecommender:
    """
    Embedding-based creator recommendation engine.
    Encodes creator content (bio, category, hashtags, captions) into a vector space
    and ranks matches using semantic similarity combined with engagement & audience metrics.
    """

    def __init__(self, vectorizer_max_features: int = 5000):
        self.vectorizer = TfidfVectorizer(
            stop_words="english",
            max_features=vectorizer_max_features,
            ngram_range=(1, 2)
        )
        self.creators_df: pd.DataFrame = pd.DataFrame()
        self.tfidf_matrix = None
        self.is_fitted = False

    def build_creator_catalog(
        self,
        profiles_path: str = PROFILES_CSV,
        posts_path: str = POSTS_CSV
    ) -> pd.DataFrame:
        """
        Loads creator profiles and posts, cleans them, aggregates content at the creator level,
        and computes creator performance metrics (average likes, comments, engagement rate).
        """
        if not os.path.exists(profiles_path):
            raise FileNotFoundError(f"Profiles file not found: {profiles_path}")

        profiles = pd.read_csv(profiles_path)

        # Normalize usernames
        profiles["username"] = profiles["username"].astype(str).str.strip().str.lower().str.lstrip("@")
        profiles = profiles.drop_duplicates(subset=["username"], keep="last")

        # Map possible column name variations
        col_mappings = {
            "biography": "bio",
            "businessCategoryName": "category",
            "categoryName": "category",
            "followersCount": "followers",
            "followsCount": "following",
            "postsCount": "posts_count",
            "verified": "is_verified",
            "isBusinessAccount": "is_business"
        }
        for src, target in col_mappings.items():
            if src in profiles.columns and target not in profiles.columns:
                profiles[target] = profiles[src]

        # Aggregate post data if available
        post_agg = pd.DataFrame()
        if os.path.exists(posts_path):
            posts = pd.read_csv(posts_path)
            # Remove duplicated header rows
            if "ownerUsername" in posts.columns:
                posts = posts[posts["ownerUsername"].astype(str).str.lower() != "ownerusername"]
                posts["ownerUsername"] = posts["ownerUsername"].astype(str).str.strip().str.lower().str.lstrip("@")

                # Ensure numeric metrics
                for col in ["likesCount", "commentsCount", "videoViewCount"]:
                    if col in posts.columns:
                        posts[col] = pd.to_numeric(posts[col], errors="coerce").fillna(0)

                # Group by creator
                def join_non_null(series, max_items=25):
                    valid = [clean_text(x) for x in series.dropna().astype(str) if x.strip()]
                    return " ".join(valid[:max_items])

                post_agg = posts.groupby("ownerUsername").agg(
                    aggregated_captions=("caption", join_non_null),
                    aggregated_hashtags=("hashtags", join_non_null),
                    avg_likes=("likesCount", "mean") if "likesCount" in posts.columns else ("ownerUsername", lambda _: 0),
                    avg_comments=("commentsCount", "mean") if "commentsCount" in posts.columns else ("ownerUsername", lambda _: 0),
                    tracked_posts_count=("id", "count") if "id" in posts.columns else ("ownerUsername", "count")
                ).reset_index()

        # Merge profiles with aggregated posts
        if not post_agg.empty:
            merged = profiles.merge(post_agg, left_on="username", right_on="ownerUsername", how="left")
        else:
            merged = profiles.copy()
            merged["aggregated_captions"] = ""
            merged["aggregated_hashtags"] = ""
            merged["avg_likes"] = 0.0
            merged["avg_comments"] = 0.0
            merged["tracked_posts_count"] = 0

        # Numeric sanitization
        merged["followers"] = pd.to_numeric(merged.get("followers", 0), errors="coerce").fillna(0)
        merged["following"] = pd.to_numeric(merged.get("following", 0), errors="coerce").fillna(0)
        merged["avg_likes"] = pd.to_numeric(merged.get("avg_likes", 0), errors="coerce").fillna(0)
        merged["avg_comments"] = pd.to_numeric(merged.get("avg_comments", 0), errors="coerce").fillna(0)

        # Engagement Rate = (avg_likes + avg_comments) / followers
        merged["engagement_rate"] = np.where(
            merged["followers"] > 0,
            (merged["avg_likes"] + merged["avg_comments"]) / merged["followers"],
            0.0
        )

        merged["follower_tier"] = merged["followers"].apply(get_follower_tier)

        # Build full content document for vectorization
        def build_doc(row):
            parts = [
                f"Creator {row.get('username', '')}",
                clean_text(row.get('fullName', '')),
                clean_text(row.get('category', '')),
                clean_text(row.get('bio', '')),
                clean_text(row.get('aggregated_hashtags', '')),
                clean_text(row.get('aggregated_captions', ''))
            ]
            return " ".join([p for p in parts if p])

        merged["content_document"] = merged.apply(build_doc, axis=1)

        self.creators_df = merged.reset_index(drop=True)
        return self.creators_df

    def import_kaggle_dataset(self, kaggle_csv_path: str) -> int:
        """
        Imports and standardizes any Kaggle influencer dataset CSV,
        aggregating and enriching them into the catalog.
        """
        if not os.path.exists(kaggle_csv_path):
            raise FileNotFoundError(f"Kaggle CSV not found at {kaggle_csv_path}")

        kdf = pd.read_csv(kaggle_csv_path)

        # Common column name heuristics in Kaggle influencer datasets
        rename_map = {}
        for col in kdf.columns:
            cl = col.lower().replace(" ", "_").replace(".", "_")
            if "user" in cl or "channel" in cl or "influencer" in cl:
                rename_map[col] = "username"
            elif "name" in cl and "user" not in cl:
                rename_map[col] = "fullName"
            elif "follower" in cl or "subscriber" in cl:
                rename_map[col] = "followers"
            elif "category" in cl or "topic" in cl or "niche" in cl:
                rename_map[col] = "category"
            elif "eng" in cl or "er" in cl:
                rename_map[col] = "engagement_rate"
            elif cl in ["avg_likes", "average_likes", "avg_like", "average_like"] or ("avg_like" in cl and "new" not in cl):
                rename_map[col] = "avg_likes"
            elif "bio" in cl or "desc" in cl:
                rename_map[col] = "bio"
            elif "country" in cl or "location" in cl:
                rename_map[col] = "country"

        kdf = kdf.rename(columns=rename_map)

        for needed in ["username", "fullName", "category", "bio", "followers", "engagement_rate", "avg_likes", "country"]:
            if needed not in kdf.columns:
                kdf[needed] = ""

        # Normalize followers, likes, engagement strings
        def parse_metric(val):
            if val is None or pd.isna(val) or str(val).strip() == "":
                return 0.0
            if isinstance(val, (int, float)):
                return float(val)
            s = str(val).strip().lower().replace(",", "").replace("%", "")
            try:
                if s.endswith("b"):
                    return float(s[:-1]) * 1_000_000_000
                elif s.endswith("m"):
                    return float(s[:-1]) * 1_000_000
                elif s.endswith("k"):
                    return float(s[:-1]) * 1_000
                return float(s)
            except ValueError:
                return 0.0

        kdf["followers"] = kdf["followers"].apply(parse_metric)
        kdf["avg_likes"] = kdf["avg_likes"].apply(parse_metric)
        kdf["engagement_rate"] = kdf["engagement_rate"].apply(parse_metric)
        if kdf["engagement_rate"].max() > 1.0:
            kdf["engagement_rate"] = kdf["engagement_rate"] / 100.0  # normalize percentages

        kdf["username"] = kdf["username"].astype(str).str.strip().str.lower().str.lstrip("@")
        kdf["follower_tier"] = kdf["followers"].apply(get_follower_tier)
        kdf["aggregated_captions"] = ""
        kdf["aggregated_hashtags"] = ""
        kdf["avg_comments"] = 0.0
        kdf["tracked_posts_count"] = 0

        # Known global creator knowledge base for high-precision semantic matching
        from creator_knowledge import KNOWN_CREATOR_PROFILES

        def enrich_creator_row(row):
            uname = row["username"]
            cat = str(row.get("category", "")).strip()
            bio = str(row.get("bio", "")).strip()
            country = str(row.get("country", "")).strip()
            
            if uname in KNOWN_CREATOR_PROFILES:
                known_cat, known_desc = KNOWN_CREATOR_PROFILES[uname]
                if not cat or cat.lower() in ["nan", "unknown", ""]:
                    cat = known_cat
                bio = f"{bio} {known_desc}".strip()
            
            doc_parts = [
                f"Creator @{uname}",
                clean_text(row.get("fullName", "")),
                f"Category: {cat}",
                f"Country: {country}" if country and country.lower() != "nan" else "",
                clean_text(bio)
            ]
            return cat, bio, " ".join([p for p in doc_parts if p])

        enriched_data = [enrich_creator_row(r) for _, r in kdf.iterrows()]
        kdf["category"] = [e[0] for e in enriched_data]
        kdf["bio"] = [e[1] for e in enriched_data]
        kdf["content_document"] = [e[2] for e in enriched_data]

        # Merge with existing dataframe
        if not self.creators_df.empty:
            combined = pd.concat([self.creators_df, kdf], ignore_index=True)
            combined = combined.drop_duplicates(subset=["username"], keep="last")
            self.creators_df = combined.reset_index(drop=True)
        else:
            self.creators_df = kdf.drop_duplicates(subset=["username"]).reset_index(drop=True)

        self.fit()
        self.save_index()
        return len(kdf)

    def fit(self):
        """Fit the vectorizer on the creator content documents."""
        if self.creators_df.empty:
            raise ValueError("Creator catalog is empty. Call build_creator_catalog first.")

        docs = self.creators_df["content_document"].fillna("").tolist()
        self.tfidf_matrix = self.vectorizer.fit_transform(docs)
        self.is_fitted = True
        return self

    def save_index(self, path: str = INDEX_FILE):
        """Save the fitted model and creator catalog."""
        if not self.is_fitted:
            raise RuntimeError("Cannot save an unfitted recommender.")
        data = {
            "vectorizer": self.vectorizer,
            "tfidf_matrix": self.tfidf_matrix,
            "creators_df": self.creators_df
        }
        with open(path, "wb") as f:
            pickle.dump(data, f)
        print(f"Vector index saved to {path} ({len(self.creators_df)} creators)")

    def load_index(self, path: str = INDEX_FILE) -> bool:
        """Load a previously saved vector index."""
        if not os.path.exists(path):
            return False
        with open(path, "rb") as f:
            data = pickle.load(f)
        self.vectorizer = data["vectorizer"]
        self.tfidf_matrix = data["tfidf_matrix"]
        self.creators_df = data["creators_df"]
        self.is_fitted = True
        return True

    def add_or_update_creator(self, creator_record: Dict[str, Any]) -> None:
        """
        Dynamically adds or updates a single creator in the catalog
        and re-indexes them without losing existing creators.
        """
        username = str(creator_record.get("username", "")).strip().lower().lstrip("@")
        if not username:
            raise ValueError("Creator must have a valid username.")

        followers = float(creator_record.get("followers", 0) or 0)
        avg_likes = float(creator_record.get("avg_likes", 0) or 0)
        avg_comments = float(creator_record.get("avg_comments", 0) or 0)
        eng_rate = float(creator_record.get("engagement_rate", 0) or 0)
        if eng_rate == 0 and followers > 0:
            eng_rate = (avg_likes + avg_comments) / followers

        content_doc = creator_record.get("content_document")
        if not content_doc:
            parts = [
                f"Creator {username}",
                clean_text(creator_record.get("fullName", "")),
                clean_text(creator_record.get("category", "")),
                clean_text(creator_record.get("bio", "")),
                clean_text(creator_record.get("aggregated_hashtags", "")),
                clean_text(creator_record.get("aggregated_captions", ""))
            ]
            content_doc = " ".join([p for p in parts if p])

        row = {
            "username": username,
            "fullName": creator_record.get("fullName", username),
            "bio": creator_record.get("bio", ""),
            "category": creator_record.get("category", ""),
            "followers": followers,
            "follower_tier": get_follower_tier(followers),
            "avg_likes": avg_likes,
            "avg_comments": avg_comments,
            "engagement_rate": eng_rate,
            "aggregated_captions": creator_record.get("aggregated_captions", ""),
            "aggregated_hashtags": creator_record.get("aggregated_hashtags", ""),
            "content_document": content_doc,
            "is_verified": creator_record.get("is_verified", False)
        }

        # If username already exists, update it; otherwise append
        if not self.creators_df.empty and username in self.creators_df["username"].values:
            idx = self.creators_df.index[self.creators_df["username"] == username][0]
            for k, v in row.items():
                self.creators_df.at[idx, k] = v
        else:
            self.creators_df = pd.concat([self.creators_df, pd.DataFrame([row])], ignore_index=True)

        # Refit vectorizer
        self.fit()
        self.save_index()
        print(f"Successfully indexed creator @{username} into vector store.")

    def recommend_by_query(
        self,
        query: str,
        category: Optional[str] = None,
        follower_tier: Optional[str] = None,
        min_followers: Optional[float] = None,
        max_followers: Optional[float] = None,
        min_engagement: Optional[float] = None,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Recommend creators based on a natural language search query with optional filters.
        Ranks by composite score: Semantic Cosine Similarity + Normalized Engagement.
        """
        if not self.is_fitted:
            raise RuntimeError("Recommender must be fitted before querying.")

        cleaned_query = clean_text(query)
        if not cleaned_query:
            return []

        # Vectorize user query
        query_vec = self.vectorizer.transform([cleaned_query])
        sim_scores = cosine_similarity(query_vec, self.tfidf_matrix).flatten()

        results = []
        # Max engagement rate for min-max normalization
        max_eng = self.creators_df["engagement_rate"].max()
        if max_eng <= 0:
            max_eng = 1.0

        for idx, sim in enumerate(sim_scores):
            row = self.creators_df.iloc[idx]

            # Filters
            if category and category.lower() not in str(row.get("category", "")).lower():
                continue
            if follower_tier and follower_tier.lower() not in str(row.get("follower_tier", "")).lower():
                continue
            if min_followers is not None and row.get("followers", 0) < min_followers:
                continue
            if max_followers is not None and row.get("followers", 0) > max_followers:
                continue
            if min_engagement is not None and row.get("engagement_rate", 0) < min_engagement:
                continue

            eng_norm = min(row.get("engagement_rate", 0) / max_eng, 1.0)
            
            # Semantic similarity is the gatekeeper; engagement acts as quality booster
            if sim > 0:
                composite_score = sim * (1.0 + 0.40 * eng_norm)
            else:
                composite_score = 0.0

            results.append({
                "username": row["username"],
                "full_name": row.get("fullName", ""),
                "category": row.get("category", "Uncategorized"),
                "bio": row.get("bio", ""),
                "followers": int(row.get("followers", 0)),
                "follower_tier": row.get("follower_tier", "Unknown"),
                "engagement_rate": float(row.get("engagement_rate", 0.0)),
                "semantic_similarity": float(sim),
                "composite_score": float(composite_score)
            })

        # Sort by composite score descending
        results.sort(key=lambda x: x["composite_score"], reverse=True)
        positive_matches = [r for r in results if r["composite_score"] > 0]
        return positive_matches[:top_k] if positive_matches else results[:top_k]

    def recommend_similar_creators(
        self,
        target_username: str,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Recommend creators who produce content similar to a given creator handle.
        """
        if not self.is_fitted:
            raise RuntimeError("Recommender must be fitted before querying.")

        target = target_username.strip().lower().lstrip("@")
        matches = self.creators_df.index[self.creators_df["username"] == target].tolist()
        if not matches:
            raise ValueError(f"Creator @{target} not found in catalog. Add them first using add_new_creator!")

        target_idx = matches[0]
        target_vec = self.tfidf_matrix[target_idx]
        sim_scores = cosine_similarity(target_vec, self.tfidf_matrix).flatten()

        results = []
        for idx, sim in enumerate(sim_scores):
            if idx == target_idx:
                continue  # skip the creator itself
            row = self.creators_df.iloc[idx]
            results.append({
                "username": row["username"],
                "full_name": row.get("fullName", ""),
                "category": row.get("category", "Uncategorized"),
                "bio": row.get("bio", ""),
                "followers": int(row.get("followers", 0)),
                "follower_tier": row.get("follower_tier", "Unknown"),
                "engagement_rate": float(row.get("engagement_rate", 0.0)),
                "similarity_score": float(sim)
            })

        results.sort(key=lambda x: x["similarity_score"], reverse=True)
        return results[:top_k]

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Creator Intelligence Recommender")
    parser.add_argument("--query", type=str, help="Search query (e.g. 'storytelling photography')")
    parser.add_argument("--similar", type=str, help="Target creator username (e.g. 'humansofny')")
    parser.add_argument("--tier", type=str, help="Follower tier filter (e.g. 'Micro', 'Mega')")
    parser.add_argument("--top_k", type=int, default=5, help="Number of recommendations")
    parser.add_argument("--rebuild", action="store_true", help="Rebuild vector index from scratch")
    args = parser.parse_args()

    recommender = CreatorRecommender()

    if args.rebuild or not os.path.exists(INDEX_FILE):
        print("Building creator catalog and fitting vector index...")
        recommender.build_creator_catalog()
        recommender.fit()
        recommender.save_index()
    else:
        recommender.load_index()

    if args.query:
        print(f"\n--- Recommendations for Query: '{args.query}' ---")
        recs = recommender.recommend_by_query(args.query, follower_tier=args.tier, top_k=args.top_k)
        for r in recs:
            print(f"@{r['username']} ({r['full_name']}) | Niche: {r['category']}")
            print(f"   Followers: {r['followers']:,} ({r['follower_tier']}) | Engagement Rate: {r['engagement_rate']:.2%}")
            print(f"   Match Score: {r['composite_score']:.3f} (Sim: {r['semantic_similarity']:.3f})")
            print(f"   Bio: {r['bio'][:120]}...\n")
    elif args.similar:
        print(f"\n--- Creators Similar to @{args.similar} ---")
        recs = recommender.recommend_similar_creators(args.similar, top_k=args.top_k)
        for r in recs:
            print(f"@{r['username']} ({r['full_name']}) | Similarity: {r['similarity_score']:.3f}")
            print(f"   Followers: {r['followers']:,} | Niche: {r['category']}")
            print(f"   Bio: {r['bio'][:120]}...\n")
    else:
        print("Recommender ready. Use --query 'your search' or --similar username")

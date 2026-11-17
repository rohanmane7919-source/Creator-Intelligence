"""Imports the cleaned dataset into the database (Stage 4).

All-or-nothing: everything is written in ONE transaction, and any error rolls
the whole import back. Only parameterised ORM statements are used.
"""
import numpy as np
import pandas as pd
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models.entities import (
    Category, CreatorMetric, CreatorProfile, ImportBatch, Platform,
    RecommendationResult,
)

TARGET_CATEGORIES = [
    "Beauty & Skincare", "Fashion & Lifestyle", "Fitness & Sports",
    "Technology & Gadgets", "Food & Cooking", "Travel & Tourism",
    "Gaming & Esports", "Education & Career", "Finance & Business",
    "Home & Interior Design",
]
CHUNK = 5000
# fields counted for the data-completeness score ("unknown" counts as missing)
COMPLETENESS_FIELDS = [
    "creator_name", "language", "content_type", "audience_age_distribution",
    "audience_gender_distribution", "audience_location", "hashtags", "comments_text",
]


class ImportConflictError(Exception):
    """Raised when data already exists and replace was not requested."""


def _py(v):
    """Convert pandas/numpy values to plain Python; missing values become None."""
    if isinstance(v, str):
        return v
    if v is None or v is pd.NaT:
        return None
    if isinstance(v, float) and np.isnan(v):
        return None
    if isinstance(v, np.generic):
        v = v.item()
        if isinstance(v, float) and v != v:
            return None
    if isinstance(v, pd.Timestamp):
        return v.to_pydatetime()
    return v


def _completeness(r: dict) -> float:
    ok = 0
    for f in COMPLETENESS_FIELDS:
        v = r.get(f)
        if v is not None and str(v).strip().lower() not in ("", "unknown"):
            ok += 1
    return round(ok / len(COMPLETENESS_FIELDS) * 100, 1)


def ensure_categories(db: Session) -> None:
    """Adds any missing target categories (no commit; caller decides)."""
    existing = set(db.scalars(select(Category.name)))
    for name in TARGET_CATEGORIES + ["Unmapped"]:
        if name not in existing:
            db.add(Category(name=name, is_target=name != "Unmapped"))
    db.flush()


def _ensure_platforms(db: Session, names) -> dict:
    existing = {p.name: p.id for p in db.scalars(select(Platform))}
    for name in sorted(set(names) - set(existing)):
        db.add(Platform(name=name))
    db.flush()
    return {p.name: p.id for p in db.scalars(select(Platform))}


def import_clean_dataframe(db: Session, df: pd.DataFrame, report: dict | None = None,
                           source_file: str = "unknown", replace: bool = False) -> dict:
    existing = db.scalar(select(func.count()).select_from(CreatorProfile))
    if existing and not replace:
        raise ImportConflictError(
            f"The database already contains {existing} creator records. "
            "Run the import again with --replace to wipe them first."
        )
    try:
        if replace:  # children first, so foreign keys are never violated
            db.execute(delete(RecommendationResult))
            db.execute(delete(CreatorMetric))
            db.execute(delete(CreatorProfile))
        ensure_categories(db)
        platform_names = {_py(p) or "Unknown" for p in df["platform"]}
        platforms = _ensure_platforms(db, platform_names)
        categories = {c.name: c.id for c in db.scalars(select(Category))}

        batch = ImportBatch(
            source_file=source_file,
            rows_in=int((report or {}).get("rows_in", len(df))),
            rows_imported=0,
            quality_report=report,
        )
        db.add(batch)
        db.flush()

        records = [{k: _py(v) for k, v in rec.items()} for rec in df.to_dict("records")]

        profile_rows = []
        for r in records:
            profile_rows.append({
                "batch_id": batch.id,
                "source_content_id": r["content_id"],
                "source_creator_id": r["creator_id"],
                "creator_name": r.get("creator_name"),
                "platform_id": platforms[r.get("platform") or "Unknown"],
                "category_id": categories[r.get("category_clean") or "Unmapped"],
                "category_raw": r.get("content_category"),
                "category_mapping": r.get("category_mapping") or "unmapped",
                "language": r.get("language"),
                "content_type": r.get("content_type"),
                "follower_count": int(r["follower_count"]),
                "audience_age_group": r.get("audience_age_distribution"),
                "audience_gender": r.get("audience_gender_distribution"),
                "audience_country": r.get("audience_location"),
                "is_sponsored": r.get("is_sponsored"),
                "disclosure_type": r.get("disclosure_type"),
                "sponsor_category": r.get("sponsor_category"),
                "has_hashtags": r.get("hashtags") is not None,
                "has_comments_text": r.get("comments_text") is not None,
                "completeness_pct": _completeness(r),
            })
        for i in range(0, len(profile_rows), CHUNK):
            db.execute(CreatorProfile.__table__.insert(), profile_rows[i:i + CHUNK])

        ids = dict(db.execute(
            select(CreatorProfile.source_content_id, CreatorProfile.id)
            .where(CreatorProfile.batch_id == batch.id)
        ).all())

        metric_rows = [{
            "creator_profile_id": ids[r["content_id"]],
            "observed_at": r.get("post_date"),
            "views": int(r["views"]),
            "likes": int(r["likes"]),
            "shares": int(r["shares"]),
            "comments_count": int(r["comments_count"]),
            "content_length": None if r.get("content_length") is None else int(r["content_length"]),
            "engagement_rate_views_pct": float(r["engagement_rate_views_pct"]),
            "engagement_rate_followers_pct": float(r["engagement_rate_followers_pct"]),
            "reach_rate_pct": float(r["reach_rate_pct"]),
            "flag_likes_exceed_views": bool(r.get("flag_likes_exceed_views")),
            "flag_interactions_exceed_followers": bool(r.get("flag_interactions_exceed_followers")),
        } for r in records]
        for i in range(0, len(metric_rows), CHUNK):
            db.execute(CreatorMetric.__table__.insert(), metric_rows[i:i + CHUNK])

        batch.rows_imported = len(profile_rows)
        db.commit()
        return {"batch_id": batch.id, "profiles": len(profile_rows),
                "metrics": len(metric_rows), "platforms": len(platforms)}
    except Exception:
        db.rollback()
        raise
"""Creator discovery endpoints (Stage 6a).

Each "creator" here is one creator-post record (see entities.py), so the API
says "creator records". The detail endpoint warns when the same source
creator ID appears with different platform / category / follower values.
All queries are parameterised SQLAlchemy statements.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database.session import get_db  # ASSUMPTION: same dependency dashboard.py uses
from app.models.entities import Category, CreatorMetric, CreatorProfile, Platform

router = APIRouter(prefix="/api/discovery", tags=["discovery"])

SORT_COLUMNS = {
    "followers": CreatorProfile.follower_count,
    "engagement": CreatorMetric.engagement_rate_views_pct,
    "engagement_followers": CreatorMetric.engagement_rate_followers_pct,
    "reach": CreatorMetric.reach_rate_pct,
    "completeness": CreatorProfile.completeness_pct,
    "name": CreatorProfile.creator_name,
}


def _escape_like(text: str) -> str:
    return text.replace("\\", "\\\\").replace("%", r"\%").replace("_", r"\_")


def _base_query():
    return (
        select(
            CreatorProfile.id,
            CreatorProfile.source_creator_id,
            CreatorProfile.creator_name,
            Platform.name.label("platform"),
            Category.name.label("category"),
            CreatorProfile.category_mapping,
            CreatorProfile.language,
            CreatorProfile.content_type,
            CreatorProfile.follower_count,
            CreatorProfile.completeness_pct,
            CreatorProfile.is_sponsored,
            CreatorMetric.engagement_rate_views_pct,
            CreatorMetric.engagement_rate_followers_pct,
            CreatorMetric.reach_rate_pct,
            CreatorMetric.flag_likes_exceed_views,
            CreatorMetric.flag_interactions_exceed_followers,
        )
        .join(Platform, Platform.id == CreatorProfile.platform_id)
        .join(Category, Category.id == CreatorProfile.category_id)
        .join(CreatorMetric, CreatorMetric.creator_profile_id == CreatorProfile.id)
    )


def _row_to_dict(r) -> dict:
    return {
        "id": r.id,
        "source_creator_id": r.source_creator_id,
        "creator_name": r.creator_name,
        "platform": r.platform,
        "category": r.category,
        "category_mapping": r.category_mapping,
        "language": r.language,
        "content_type": r.content_type,
        "follower_count": r.follower_count,
        "completeness_pct": r.completeness_pct,
        "is_sponsored": r.is_sponsored,
        "engagement_rate_views_pct": r.engagement_rate_views_pct,
        "engagement_rate_followers_pct": r.engagement_rate_followers_pct,
        "reach_rate_pct": r.reach_rate_pct,
        "flag_likes_exceed_views": r.flag_likes_exceed_views,
        "flag_interactions_exceed_followers": r.flag_interactions_exceed_followers,
    }


@router.get("/filters")
def get_filters(db: Session = Depends(get_db)):
    """Values for the filter dropdowns and sliders."""
    lo, hi = db.execute(
        select(func.min(CreatorProfile.follower_count), func.max(CreatorProfile.follower_count))
    ).one()
    languages = [x for x in db.scalars(
        select(CreatorProfile.language).where(CreatorProfile.language.is_not(None))
        .distinct().order_by(CreatorProfile.language)) if x]
    content_types = [x for x in db.scalars(
        select(CreatorProfile.content_type).where(CreatorProfile.content_type.is_not(None))
        .distinct().order_by(CreatorProfile.content_type)) if x]
    return {
        "platforms": list(db.scalars(select(Platform.name).order_by(Platform.name))),
        "categories": list(db.scalars(
            select(Category.name).where(Category.is_target.is_(True)).order_by(Category.name))),
        "languages": languages,
        "content_types": content_types,
        "follower_min": lo or 0,
        "follower_max": hi or 0,
    }


@router.get("/creators")
def search_creators(
    q: str | None = Query(None, max_length=100, description="creator name or ID contains"),
    platform: str | None = None,
    category: str | None = None,
    language: str | None = None,
    content_type: str | None = None,
    sponsored: bool | None = None,
    min_followers: int | None = Query(None, ge=0),
    max_followers: int | None = Query(None, ge=0),
    min_engagement: float | None = Query(None, ge=0, description="engagement rate on views, %"),
    max_engagement: float | None = Query(None, ge=0),
    sort: str = Query("followers", pattern="^(followers|engagement|engagement_followers|reach|completeness|name)$"),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    if min_followers is not None and max_followers is not None and min_followers > max_followers:
        raise HTTPException(422, "min_followers cannot be greater than max_followers")
    if min_engagement is not None and max_engagement is not None and min_engagement > max_engagement:
        raise HTTPException(422, "min_engagement cannot be greater than max_engagement")

    stmt = _base_query()
    if q:
        like = f"%{_escape_like(q.strip())}%"
        stmt = stmt.where(
            CreatorProfile.creator_name.ilike(like, escape="\\")
            | CreatorProfile.source_creator_id.ilike(like, escape="\\")
        )
    if platform:
        stmt = stmt.where(Platform.name == platform)
    if category:
        stmt = stmt.where(Category.name == category)
    if language:
        stmt = stmt.where(CreatorProfile.language == language)
    if content_type:
        stmt = stmt.where(CreatorProfile.content_type == content_type)
    if sponsored is not None:
        stmt = stmt.where(CreatorProfile.is_sponsored.is_(sponsored))
    if min_followers is not None:
        stmt = stmt.where(CreatorProfile.follower_count >= min_followers)
    if max_followers is not None:
        stmt = stmt.where(CreatorProfile.follower_count <= max_followers)
    if min_engagement is not None:
        stmt = stmt.where(CreatorMetric.engagement_rate_views_pct >= min_engagement)
    if max_engagement is not None:
        stmt = stmt.where(CreatorMetric.engagement_rate_views_pct <= max_engagement)

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0

    col = SORT_COLUMNS[sort]
    primary = col.desc() if order == "desc" else col.asc()
    stmt = stmt.order_by(primary, CreatorProfile.id.asc())  # id = stable tie-break
    rows = db.execute(stmt.limit(page_size).offset((page - 1) * page_size)).all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size,
        "items": [_row_to_dict(r) for r in rows],
        "note": "Each result is one creator-post record, not a verified unique creator.",
    }


@router.get("/creators/{creator_id}")
def creator_detail(creator_id: int, db: Session = Depends(get_db)):
    row = db.execute(_base_query().where(CreatorProfile.id == creator_id)).first()
    if row is None:
        raise HTTPException(404, "Creator record not found")
    item = _row_to_dict(row)

    # Other records sharing the same dataset creator ID
    same = db.execute(
        select(
            func.count(CreatorProfile.id),
            func.count(func.distinct(CreatorProfile.platform_id)),
            func.count(func.distinct(CreatorProfile.category_id)),
            func.min(CreatorProfile.follower_count),
            func.max(CreatorProfile.follower_count),
        ).where(CreatorProfile.source_creator_id == row.source_creator_id)
    ).one()
    n, n_plat, n_cat, f_lo, f_hi = same
    inconsistent = n > 1 and (n_plat > 1 or n_cat > 1 or f_lo != f_hi)
    item["same_id_records"] = n
    item["identity_warning"] = (
        f"The dataset ID {row.source_creator_id} appears in {n} records with different "
        f"platform/category/follower values ({n_plat} platforms, {n_cat} categories, "
        f"{f_lo:,} to {f_hi:,} followers). These may not be the same real account."
        if inconsistent else None
    )
    return item
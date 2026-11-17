"""Dashboard queries (Stage 5). Every number comes from the database."""
from sqlalchemy import and_, case, func, select
from sqlalchemy.orm import Session

from app.models.entities import (
    BusinessSearch, Category, CreatorMetric, CreatorProfile, ImportBatch,
    ModelRun, Platform,
)

# (label, lower bound inclusive, upper bound exclusive)
TIERS = [
    ("Under 10K", 0, 10_000),
    ("10K to 100K", 10_000, 100_000),
    ("100K to 500K", 100_000, 500_000),
    ("500K and above", 500_000, None),
]

# metric key -> (label, unit, column). Only these columns can ever be sorted on.
TOP_METRICS = {
    "followers": ("Followers", "count", CreatorProfile.follower_count),
    "engagement_rate_views_pct": ("Engagement rate (per view)", "percent", CreatorMetric.engagement_rate_views_pct),
    "engagement_rate_followers_pct": ("Engagement rate (per follower)", "percent", CreatorMetric.engagement_rate_followers_pct),
    "reach_rate_pct": ("Reach rate (views per follower)", "percent", CreatorMetric.reach_rate_pct),
    "views": ("Views", "count", CreatorMetric.views),
    "likes": ("Likes", "count", CreatorMetric.likes),
}


def _f(v):
    return None if v is None else float(v)


def _kpis(db: Session) -> dict:
    total, followers, sponsored, completeness = db.execute(
        select(
            func.count(CreatorProfile.id),
            func.coalesce(func.sum(CreatorProfile.follower_count), 0),
            # NULL is_sponsored rows are ignored by avg(), so the share is over known rows
            func.avg(case(
                (CreatorProfile.is_sponsored.is_(True), 1.0),
                (CreatorProfile.is_sponsored.is_(False), 0.0),
            )),
            func.avg(CreatorProfile.completeness_pct),
        )
    ).one()
    engagement = db.scalar(select(func.avg(CreatorMetric.engagement_rate_views_pct)))
    return {
        "total_records": int(total),
        "total_followers": int(followers),
        "avg_engagement_rate_views_pct": _f(engagement),
        "sponsored_share_pct": None if sponsored is None else float(sponsored) * 100,
        "avg_completeness_pct": _f(completeness),
    }


def _category_stats(db: Session) -> list[dict]:
    n = func.count(func.distinct(CreatorProfile.id))
    rows = db.execute(
        select(Category.name, Category.is_target, n,
               func.avg(CreatorMetric.engagement_rate_views_pct))
        .select_from(Category)
        .outerjoin(CreatorProfile, CreatorProfile.category_id == Category.id)
        .outerjoin(CreatorMetric, CreatorMetric.creator_profile_id == CreatorProfile.id)
        .group_by(Category.id, Category.name, Category.is_target)
        .order_by(n.desc(), Category.name)
    ).all()
    return [{"name": r[0], "is_target": bool(r[1]), "count": int(r[2]),
             "avg_engagement_rate_views_pct": _f(r[3]), "has_data": r[2] > 0} for r in rows]


def _platform_stats(db: Session) -> list[dict]:
    n = func.count(func.distinct(CreatorProfile.id))
    rows = db.execute(
        select(Platform.name, n, func.avg(CreatorMetric.engagement_rate_views_pct))
        .select_from(Platform)
        .outerjoin(CreatorProfile, CreatorProfile.platform_id == Platform.id)
        .outerjoin(CreatorMetric, CreatorMetric.creator_profile_id == CreatorProfile.id)
        .group_by(Platform.id, Platform.name)
        .order_by(n.desc(), Platform.name)
    ).all()
    return [{"name": r[0], "count": int(r[1]), "has_data": r[1] > 0,
             "avg_engagement_rate_views_pct": _f(r[2])} for r in rows]


def _tier_stats(db: Session) -> list[dict]:
    out = []
    for label, lo, hi in TIERS:
        cond = CreatorProfile.follower_count >= lo
        if hi is not None:
            cond = and_(cond, CreatorProfile.follower_count < hi)
        count, avg = db.execute(
            select(func.count(CreatorProfile.id),
                   func.avg(CreatorMetric.engagement_rate_views_pct))
            .select_from(CreatorProfile)
            .join(CreatorMetric, CreatorMetric.creator_profile_id == CreatorProfile.id)
            .where(cond)
        ).one()
        out.append({"name": label, "count": int(count), "has_data": count > 0,
                    "avg_engagement_rate_views_pct": _f(avg)})
    return out


def _data_quality(db: Session) -> dict | None:
    batch = db.scalars(select(ImportBatch).order_by(ImportBatch.id.desc()).limit(1)).first()
    if batch is None:
        return None
    report = batch.quality_report if isinstance(batch.quality_report, dict) else {}
    return {
        "source_file": batch.source_file,
        "imported_at": batch.imported_at,
        "rows_in": batch.rows_in,
        "rows_imported": batch.rows_imported,
        "warnings": list(report.get("warnings", [])),
        "date_range": report.get("date_range"),
    }


def get_summary(db: Session) -> dict:
    return {
        "kpis": _kpis(db),
        "categories": _category_stats(db),
        "platforms": _platform_stats(db),
        "follower_tiers": _tier_stats(db),
        "recent_searches": list(db.scalars(
            select(BusinessSearch).order_by(BusinessSearch.created_at.desc(), BusinessSearch.id.desc()).limit(5)
        )),
        "models": list(db.scalars(select(ModelRun).order_by(ModelRun.id.desc()).limit(5))),
        "data_quality": _data_quality(db),
    }


def get_top_creators(db: Session, metric: str, limit: int) -> dict:
    label, unit, col = TOP_METRICS[metric]
    rows = db.execute(
        select(
            CreatorProfile.id, CreatorProfile.source_content_id, CreatorProfile.creator_name,
            Platform.name.label("platform"), Category.name.label("category"),
            CreatorProfile.follower_count, col.label("value"),
        )
        .join(CreatorMetric, CreatorMetric.creator_profile_id == CreatorProfile.id)
        .join(Platform, CreatorProfile.platform_id == Platform.id)
        .join(Category, CreatorProfile.category_id == Category.id)
        .order_by(col.desc(), CreatorProfile.id)
        .limit(limit)
    ).all()
    items = [{
        "profile_id": r.id, "source_content_id": r.source_content_id,
        "creator_name": r.creator_name, "platform": r.platform, "category": r.category,
        "follower_count": int(r.follower_count), "value": float(r.value),
    } for r in rows]
    return {"metric": metric, "label": label, "unit": unit, "items": items}

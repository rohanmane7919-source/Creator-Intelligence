"""Rule-based creator recommendations (Stage 6b).

This is NOT a trained model. Each creator-post record gets a score out of 100
from fixed rules, and the response shows every component so the ranking can be
explained. The score is computed inside the database query (so only the top N
rows are fetched) and the explanation is built from the same columns, so the
two can never disagree.

Score (max 100):
  category fit   0-30   direct mapping 30, partial 15 (only when an industry is given)
  reach          0-25   reach_rate_pct capped at 100, weight depends on objective
  engagement     0-25   engagement on views capped at 10 %, weight depends on objective
  follower fit   0-15   closeness to the middle of the follower range (needs min AND max)
  completeness   0-15   completeness_pct scaled
  penalty        -15    if the record has a data-quality flag
(reach + engagement weights: awareness 25+15, engagement 15+25, balanced 20+20)
"""
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import Float, case, func, literal, or_, select
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.entities import (
    BusinessSearch, Category, CreatorMetric, CreatorProfile, Platform,
    RecommendationResult,
)

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])

METHOD = "rule_based_v1"
METHOD_NOTE = (
    "Rule-based score out of 100, not a trained model. Engagement values in this "
    "dataset are very similar across records, so the ranking is driven mostly by "
    "category fit, follower-range fit and data completeness. Each result is one "
    "creator-post record, not a verified unique creator."
)
# objective -> (reach weight, engagement weight)
WEIGHTS = {"awareness": (25.0, 15.0), "engagement": (15.0, 25.0), "balanced": (20.0, 20.0)}
FLAG_PENALTY = 15.0


class RecommendationRequest(BaseModel):
    industry: str | None = None          # a target category name
    objective: Literal["awareness", "engagement", "balanced"] = "balanced"
    platform: str | None = None
    min_followers: int | None = Field(None, ge=0)
    max_followers: int | None = Field(None, ge=0)
    min_engagement_pct: float | None = Field(None, ge=0)
    budget: float | None = Field(None, ge=0)  # stored in history only; not used in scoring
    limit: int = Field(10, ge=1, le=50)


def _cap(expr, cap: float):
    return case((expr > cap, cap), else_=expr)


def _components(req: RecommendationRequest):
    w_reach, w_eng = WEIGHTS[req.objective]
    if req.industry:
        p_category = case(
            (CreatorProfile.category_mapping == "direct", 30.0),
            (CreatorProfile.category_mapping == "partial", 15.0),
            else_=0.0,
        )
    else:
        p_category = literal(0.0, type_=Float)
    p_reach = _cap(CreatorMetric.reach_rate_pct, 100.0) / 100.0 * w_reach
    p_eng = _cap(CreatorMetric.engagement_rate_views_pct, 10.0) / 10.0 * w_eng
    p_comp = CreatorProfile.completeness_pct / 100.0 * 15.0
    if req.min_followers is not None and req.max_followers is not None:
        mid = (req.min_followers + req.max_followers) / 2.0
        half = (req.max_followers - req.min_followers) / 2.0
        if half == 0:
            p_follow = literal(15.0, type_=Float)
        else:
            p_follow = 15.0 * (1.0 - func.abs(CreatorProfile.follower_count - mid) / half)
    else:
        p_follow = literal(0.0, type_=Float)
    penalty = case(
        (or_(CreatorMetric.flag_likes_exceed_views.is_(True),
             CreatorMetric.flag_interactions_exceed_followers.is_(True)), FLAG_PENALTY),
        else_=0.0,
    )
    return p_category, p_reach, p_eng, p_follow, p_comp, penalty


@router.post("/search")
def recommend(req: RecommendationRequest, db: Session = Depends(get_db)):
    if (req.min_followers is not None and req.max_followers is not None
            and req.min_followers > req.max_followers):
        raise HTTPException(422, "min_followers cannot be greater than max_followers")

    p_category, p_reach, p_eng, p_follow, p_comp, penalty = _components(req)
    raw = p_reach + p_eng + p_comp + p_category + p_follow - penalty
    score_expr = case((raw < 0, 0.0), else_=raw)

    filters = []
    if req.industry:
        filters.append(Category.name == req.industry)
    if req.platform:
        filters.append(Platform.name == req.platform)
    if req.min_followers is not None:
        filters.append(CreatorProfile.follower_count >= req.min_followers)
    if req.max_followers is not None:
        filters.append(CreatorProfile.follower_count <= req.max_followers)
    if req.min_engagement_pct is not None:
        filters.append(CreatorMetric.engagement_rate_views_pct >= req.min_engagement_pct)

    def joined(stmt):
        return (stmt
                .join(Platform, Platform.id == CreatorProfile.platform_id)
                .join(Category, Category.id == CreatorProfile.category_id)
                .join(CreatorMetric, CreatorMetric.creator_profile_id == CreatorProfile.id)
                .where(*filters))

    total_candidates = db.scalar(joined(select(func.count(CreatorProfile.id)))) or 0

    stmt = joined(select(
        CreatorProfile.id, CreatorProfile.source_creator_id, CreatorProfile.creator_name,
        Platform.name.label("platform"), Category.name.label("category"),
        CreatorProfile.category_mapping, CreatorProfile.follower_count,
        CreatorProfile.completeness_pct,
        CreatorMetric.engagement_rate_views_pct, CreatorMetric.reach_rate_pct,
        CreatorMetric.flag_likes_exceed_views,
        CreatorMetric.flag_interactions_exceed_followers,
        p_category.label("c_category"), p_reach.label("c_reach"),
        p_eng.label("c_engagement"), p_follow.label("c_follower_fit"),
        p_comp.label("c_completeness"), penalty.label("c_penalty"),
    )).order_by(score_expr.desc(), CreatorProfile.id.asc()).limit(req.limit)
    rows = db.execute(stmt).all()

    items = []
    for rank, r in enumerate(rows, start=1):
        parts = {
            "category_fit": r.c_category, "reach": r.c_reach,
            "engagement": r.c_engagement, "follower_fit": r.c_follower_fit,
            "completeness": r.c_completeness,
        }
        total = max(0.0, sum(parts.values()) - r.c_penalty)
        reasons = []
        if req.industry:
            reasons.append(f"Category {r.category} ({r.category_mapping} mapping): "
                           f"+{r.c_category:.1f}")
        reasons.append(f"Reach rate {r.reach_rate_pct:.1f}%: +{r.c_reach:.1f}")
        reasons.append(f"Engagement {r.engagement_rate_views_pct:.2f}% of views: "
                       f"+{r.c_engagement:.1f}")
        if req.min_followers is not None and req.max_followers is not None:
            reasons.append(f"{r.follower_count:,} followers vs requested range: "
                           f"+{r.c_follower_fit:.1f}")
        reasons.append(f"Data completeness {r.completeness_pct:.0f}%: "
                       f"+{r.c_completeness:.1f}")
        warnings = []
        if r.flag_likes_exceed_views:
            warnings.append("Likes exceed views in this record (possible data issue)")
        if r.flag_interactions_exceed_followers:
            warnings.append("Interactions exceed followers in this record (possible data issue)")
        if warnings:
            reasons.append(f"Data-quality penalty: -{r.c_penalty:.1f}")
        items.append({
            "rank": rank,
            "id": r.id,
            "source_creator_id": r.source_creator_id,
            "creator_name": r.creator_name,
            "platform": r.platform,
            "category": r.category,
            "follower_count": r.follower_count,
            "engagement_rate_views_pct": r.engagement_rate_views_pct,
            "reach_rate_pct": r.reach_rate_pct,
            "completeness_pct": r.completeness_pct,
            "score": round(total, 1),
            "components": {k: round(v, 1) for k, v in parts.items()}
                          | {"penalty": round(-r.c_penalty, 1)},
            "reasons": reasons,
            "warnings": warnings,
        })

    # Save to search history (Stage 10 will show it)
    search = BusinessSearch(
        industry=req.industry, objective=req.objective,
        min_followers=req.min_followers, max_followers=req.max_followers,
        min_engagement_pct=req.min_engagement_pct, budget=req.budget,
        filters={"platform": req.platform, "limit": req.limit},
        result_count=len(items),
    )
    db.add(search)
    db.flush()
    for it in items:
        db.add(RecommendationResult(
            search_id=search.id, creator_profile_id=it["id"], rank=it["rank"],
            score=it["score"], method=METHOD,
            explanation={"components": it["components"], "reasons": it["reasons"],
                         "warnings": it["warnings"]},
        ))
    db.commit()

    return {
        "search_id": search.id,
        "method": METHOD,
        "method_note": METHOD_NOTE,
        "total_candidates": total_candidates,
        "items": items,
    }
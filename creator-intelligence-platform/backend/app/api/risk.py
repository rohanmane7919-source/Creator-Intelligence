"""Trust & risk signals API (Stage 7).

Rule-based review prioritisation. This is NOT fraud detection and NOT machine
learning. Scoring all records is cached in memory (keyed by the table size and
the chosen settings), so only the first request after an import is slow.
"""
from __future__ import annotations

import math
from dataclasses import asdict
from typing import Literal

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.entities import CreatorMetric, CreatorProfile, Platform
from app.schemas.risk import QueueResponse, RiskAssessment, SummaryResponse
from app.services.risk import DISCLAIMER, RiskConfig, assess_post, build_baselines

router = APIRouter(prefix="/api/risk", tags=["risk"])

SIGNAL_LABELS = {
    "interactions_exceed_followers": "Interactions exceed followers",
    "likes_exceed_views": "Likes exceed views",
    "engagement_outlier": "Unusually high engagement vs followers",
    "reach_outlier": "Unusually high reach vs followers",
    "weak_disclosure": "Sponsored with implicit disclosure",
    "low_completeness": "Low data completeness",
}
_CACHE: dict = {}


def risk_config(
    outlier_percentile: float = Query(0.99, ge=0.90, le=0.999),
    min_completeness_pct: float = Query(60.0, ge=0, le=100),
    medium_threshold: float = Query(25.0, ge=0, le=100),
    high_threshold: float = Query(50.0, ge=0, le=100),
) -> RiskConfig:
    if medium_threshold >= high_threshold:
        raise HTTPException(422, "medium_threshold must be lower than high_threshold")
    return RiskConfig(
        outlier_percentile=outlier_percentile,
        min_completeness_pct=min_completeness_pct,
        medium_threshold=medium_threshold,
        high_threshold=high_threshold,
    )


def _clean(v):
    """pandas/numpy value -> plain Python; missing -> None."""
    if v is None:
        return None
    try:
        if pd.isna(v):
            return None
    except (TypeError, ValueError):
        pass
    return v.item() if hasattr(v, "item") else v


def _load_frame(db: Session) -> pd.DataFrame:
    stmt = (
        select(
            CreatorProfile.id,
            CreatorProfile.creator_name,
            Platform.name.label("platform"),
            CreatorProfile.is_sponsored,
            CreatorProfile.disclosure_type,
            CreatorProfile.completeness_pct,
            CreatorMetric.engagement_rate_followers_pct,
            CreatorMetric.reach_rate_pct,
            CreatorMetric.flag_likes_exceed_views,
            CreatorMetric.flag_interactions_exceed_followers,
        )
        .join(Platform, Platform.id == CreatorProfile.platform_id)
        .join(CreatorMetric, CreatorMetric.creator_profile_id == CreatorProfile.id)
    )
    return pd.DataFrame([dict(r) for r in db.execute(stmt).mappings().all()])


def _bundle(db: Session, cfg: RiskConfig) -> dict:
    count, max_id = db.execute(
        select(func.count(CreatorProfile.id), func.max(CreatorProfile.id))
    ).one()
    if not count:
        raise HTTPException(404, "No records in the database. Import the dataset first.")
    key = (count, max_id, cfg)
    if key in _CACHE:
        return _CACHE[key]

    frame = _load_frame(db)
    if frame.empty:
        raise HTTPException(404, "No metric rows found for the imported records.")
    baselines = build_baselines(frame, cfg.outlier_percentile)
    rows = []
    for rec in frame.to_dict("records"):
        rec = {k: _clean(v) for k, v in rec.items()}
        res = assess_post(rec, baselines, cfg)
        rows.append({
            "id": rec["id"], "creator_name": rec["creator_name"], "platform": rec["platform"],
            "risk_score": res["risk_score"], "review_priority": res["review_priority"],
            "triggered": [s["key"] for s in res["signals"] if s["triggered"]],
        })
    bundle = {
        "frame": frame.set_index("id", drop=False),
        "baselines": baselines,
        "scored": pd.DataFrame(rows),
    }
    if len(_CACHE) >= 6:
        _CACHE.clear()
    _CACHE[key] = bundle
    return bundle


@router.get("/config")
def default_config():
    return {"config": asdict(RiskConfig()), "method": "rule_based_v1", "disclaimer": DISCLAIMER}


@router.get("/summary", response_model=SummaryResponse)
def summary(cfg: RiskConfig = Depends(risk_config), db: Session = Depends(get_db)):
    b = _bundle(db, cfg)
    scored = b["scored"]
    levels = scored["review_priority"].value_counts().to_dict()
    sig_counts: dict[str, int] = {}
    for triggered in scored["triggered"]:
        for k in triggered:
            sig_counts[k] = sig_counts.get(k, 0) + 1
    return {
        "total": int(len(scored)),
        "review_priority": {k: int(levels.get(k, 0)) for k in ("low", "medium", "high")},
        "signals": [{"key": k, "label": v, "count": sig_counts.get(k, 0)}
                    for k, v in SIGNAL_LABELS.items()],
        "baselines": b["baselines"],
        "config": asdict(cfg),
        "method": "rule_based_v1",
        "disclaimer": DISCLAIMER,
    }


@router.get("/queue", response_model=QueueResponse)
def review_queue(
    level: Literal["low", "medium", "high"] | None = None,
    platform: str | None = None,
    signal: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    cfg: RiskConfig = Depends(risk_config),
    db: Session = Depends(get_db),
):
    if signal is not None and signal not in SIGNAL_LABELS:
        raise HTTPException(422, f"Unknown signal. Choose one of: {list(SIGNAL_LABELS)}")
    df = _bundle(db, cfg)["scored"]
    if level:
        df = df[df["review_priority"] == level]
    if platform:
        df = df[df["platform"] == platform]
    if signal:
        df = df[df["triggered"].apply(lambda t: signal in t)]
    df = df.sort_values(["risk_score", "id"], ascending=[False, True])

    total = int(len(df))
    pages = max(1, math.ceil(total / page_size))
    chunk = df.iloc[(page - 1) * page_size: page * page_size]
    items = [{
        "profile_id": int(r["id"]),
        "creator_name": _clean(r["creator_name"]),
        "platform": _clean(r["platform"]),
        "risk_score": float(r["risk_score"]),
        "review_priority": r["review_priority"],
        "signals_triggered": list(r["triggered"]),
    } for r in chunk.to_dict("records")]
    return {"items": items, "total": total, "page": page, "pages": pages,
            "page_size": page_size, "disclaimer": DISCLAIMER}


@router.get("/posts/{profile_id}", response_model=RiskAssessment)
def post_risk(profile_id: int, cfg: RiskConfig = Depends(risk_config),
              db: Session = Depends(get_db)):
    b = _bundle(db, cfg)
    if profile_id not in b["frame"].index:
        raise HTTPException(404, f"Record {profile_id} not found")
    rec = {k: _clean(v) for k, v in b["frame"].loc[profile_id].to_dict().items()}
    res = assess_post(rec, b["baselines"], cfg)
    return {"profile_id": profile_id, "creator_name": rec["creator_name"],
            "platform": rec["platform"], **res}
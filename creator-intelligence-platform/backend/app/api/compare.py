"""Side-by-side comparison of 2 to 4 creator-post records (Stage 6b)."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.discovery import _base_query, _row_to_dict
from app.database.session import get_db
from app.models.entities import CreatorProfile

router = APIRouter(prefix="/api/compare", tags=["compare"])

# metric -> higher is better
HIGHLIGHT_METRICS = [
    "follower_count", "engagement_rate_views_pct", "engagement_rate_followers_pct",
    "reach_rate_pct", "completeness_pct",
]


@router.get("")
def compare(
    ids: str = Query(..., description="comma-separated record IDs, 2 to 4"),
    db: Session = Depends(get_db),
):
    try:
        wanted = [int(x) for x in ids.split(",") if x.strip()]
    except ValueError:
        raise HTTPException(422, "ids must be whole numbers separated by commas")
    if len(set(wanted)) != len(wanted):
        raise HTTPException(422, "ids must not repeat")
    if not 2 <= len(wanted) <= 4:
        raise HTTPException(422, "Choose between 2 and 4 records to compare")

    rows = db.execute(_base_query().where(CreatorProfile.id.in_(wanted))).all()
    by_id = {r.id: _row_to_dict(r) for r in rows}
    missing = [i for i in wanted if i not in by_id]
    if missing:
        raise HTTPException(404, f"Record(s) not found: {missing}")
    items = [by_id[i] for i in wanted]  # keep the order the user chose

    highlights = {}
    for m in HIGHLIGHT_METRICS:
        values = {it["id"]: it[m] for it in items}
        if len(set(values.values())) == 1:
            highlights[m] = []  # all equal: no winner
        else:
            best = max(values.values())
            highlights[m] = [i for i, v in values.items() if v == best]

    warnings = []
    for it in items:
        if it["flag_likes_exceed_views"] or it["flag_interactions_exceed_followers"]:
            warnings.append(
                f"Record {it['id']} has a data-quality flag (interactions exceed views/followers)."
            )

    return {
        "items": items,
        "highlights": highlights,
        "warnings": warnings,
        "note": "Each column is one creator-post record. Highlights show the highest value per metric.",
    }
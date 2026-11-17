import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.dashboard import DashboardSummary, TopCreatorsResponse, TopMetric
from app.services import dashboard as service

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])
log = logging.getLogger(__name__)


@router.get("/summary", response_model=DashboardSummary)
def summary(db: Session = Depends(get_db)):
    try:
        return service.get_summary(db)
    except SQLAlchemyError:
        log.exception("Dashboard summary query failed")
        raise HTTPException(status_code=503, detail="Database query failed. Check the backend terminal for details.")


@router.get("/top-creators", response_model=TopCreatorsResponse)
def top_creators(
    metric: TopMetric = "followers",
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    try:
        return service.get_top_creators(db, metric, limit)
    except SQLAlchemyError:
        log.exception("Top creators query failed")
        raise HTTPException(status_code=503, detail="Database query failed. Check the backend terminal for details.")

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

TopMetric = Literal[
    "followers",
    "engagement_rate_views_pct",
    "engagement_rate_followers_pct",
    "reach_rate_pct",
    "views",
    "likes",
]


class Kpis(BaseModel):
    total_records: int
    total_followers: int
    avg_engagement_rate_views_pct: float | None
    sponsored_share_pct: float | None
    avg_completeness_pct: float | None


class GroupStat(BaseModel):
    name: str
    count: int
    avg_engagement_rate_views_pct: float | None
    has_data: bool
    is_target: bool = False  # categories only: one of the 10 target categories


class RecentSearch(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
    industry: str | None
    objective: str | None
    min_followers: int | None
    max_followers: int | None
    min_engagement_pct: float | None
    result_count: int | None


class ModelStatus(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    model_name: str
    task: str
    status: str
    trained_at: datetime
    train_rows: int | None
    test_rows: int | None
    metrics: dict | None
    notes: str | None


class DataQuality(BaseModel):
    source_file: str
    imported_at: datetime
    rows_in: int
    rows_imported: int
    warnings: list[str]
    date_range: list[str] | None


class DashboardSummary(BaseModel):
    kpis: Kpis
    categories: list[GroupStat]
    platforms: list[GroupStat]
    follower_tiers: list[GroupStat]
    recent_searches: list[RecentSearch]
    models: list[ModelStatus]
    data_quality: DataQuality | None


class TopCreator(BaseModel):
    profile_id: int
    source_content_id: str
    creator_name: str | None
    platform: str
    category: str
    follower_count: int
    value: float


class TopCreatorsResponse(BaseModel):
    metric: TopMetric
    label: str
    unit: Literal["count", "percent"]
    items: list[TopCreator]

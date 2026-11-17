"""All database tables (Stage 4), in one file so the whole schema is visible.

Data model decision: the dataset's creator_id is NOT a real account (platform,
category and followers change between posts that share it). So each source row
is stored as ONE creator-post record in `creator_profiles`.
"""
from datetime import datetime

from sqlalchemy import (
    JSON, BigInteger, Boolean, CheckConstraint, DateTime, Float, ForeignKey,
    Index, Integer, String, Text, UniqueConstraint, func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base

# JSONB on PostgreSQL, plain JSON elsewhere (lets unit tests run on SQLite)
JsonType = JSON().with_variant(JSONB, "postgresql")


class Platform(Base):
    __tablename__ = "platforms"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)


class Category(Base):
    """The 10 target categories plus 'Unmapped'. is_target marks the 10."""
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    is_target: Mapped[bool] = mapped_column(Boolean, default=False)


class ImportBatch(Base):
    """One row per import run, with the full data-quality report."""
    __tablename__ = "import_batches"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_file: Mapped[str] = mapped_column(String(255))
    rows_in: Mapped[int] = mapped_column(Integer)
    rows_imported: Mapped[int] = mapped_column(Integer)
    quality_report: Mapped[dict | None] = mapped_column(JsonType)
    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class CreatorProfile(Base):
    """One row per source record. source_creator_id is a dataset label only."""
    __tablename__ = "creator_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("import_batches.id"), index=True)
    source_content_id: Mapped[str] = mapped_column(String(64), unique=True)
    source_creator_id: Mapped[str] = mapped_column(String(64), index=True)
    creator_name: Mapped[str | None] = mapped_column(String(255), index=True)
    platform_id: Mapped[int] = mapped_column(ForeignKey("platforms.id"), index=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), index=True)
    category_raw: Mapped[str | None] = mapped_column(String(80))
    category_mapping: Mapped[str] = mapped_column(String(20))  # direct/partial/unmapped
    language: Mapped[str | None] = mapped_column(String(40))
    content_type: Mapped[str | None] = mapped_column(String(40))
    follower_count: Mapped[int] = mapped_column(BigInteger, index=True)
    audience_age_group: Mapped[str | None] = mapped_column(String(20))
    audience_gender: Mapped[str | None] = mapped_column(String(20))
    audience_country: Mapped[str | None] = mapped_column(String(60))
    is_sponsored: Mapped[bool | None] = mapped_column(Boolean)
    disclosure_type: Mapped[str | None] = mapped_column(String(30))
    sponsor_category: Mapped[str | None] = mapped_column(String(60))
    has_hashtags: Mapped[bool] = mapped_column(Boolean)
    has_comments_text: Mapped[bool] = mapped_column(Boolean)
    completeness_pct: Mapped[float] = mapped_column(Float)

    platform: Mapped[Platform] = relationship()
    category: Mapped[Category] = relationship()
    metrics: Mapped[list["CreatorMetric"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan", passive_deletes=True
    )

    __table_args__ = (
        CheckConstraint("follower_count >= 0", name="ck_profiles_followers_nonneg"),
    )


class CreatorMetric(Base):
    """Measurements for a profile. 1:N so real time series can be stored later."""
    __tablename__ = "creator_metrics"

    id: Mapped[int] = mapped_column(primary_key=True)
    creator_profile_id: Mapped[int] = mapped_column(
        ForeignKey("creator_profiles.id", ondelete="CASCADE"), index=True
    )
    observed_at: Mapped[datetime | None] = mapped_column(DateTime)
    views: Mapped[int] = mapped_column(BigInteger)
    likes: Mapped[int] = mapped_column(BigInteger)
    shares: Mapped[int] = mapped_column(BigInteger)
    comments_count: Mapped[int] = mapped_column(BigInteger)
    content_length: Mapped[int | None] = mapped_column(Integer)
    engagement_rate_views_pct: Mapped[float] = mapped_column(Float)
    engagement_rate_followers_pct: Mapped[float] = mapped_column(Float)
    reach_rate_pct: Mapped[float] = mapped_column(Float)
    flag_likes_exceed_views: Mapped[bool] = mapped_column(Boolean, default=False)
    flag_interactions_exceed_followers: Mapped[bool] = mapped_column(Boolean, default=False)

    profile: Mapped[CreatorProfile] = relationship(back_populates="metrics")

    __table_args__ = (
        CheckConstraint(
            "views >= 0 AND likes >= 0 AND shares >= 0 AND comments_count >= 0",
            name="ck_metrics_nonneg",
        ),
        Index("ix_metrics_engagement", "engagement_rate_views_pct"),
    )


class BusinessSearch(Base):
    """A search made by a business user (Stage 10 fills this)."""
    __tablename__ = "business_searches"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    industry: Mapped[str | None] = mapped_column(String(80))
    objective: Mapped[str | None] = mapped_column(String(120))
    min_followers: Mapped[int | None] = mapped_column(BigInteger)
    max_followers: Mapped[int | None] = mapped_column(BigInteger)
    min_engagement_pct: Mapped[float | None] = mapped_column(Float)
    budget: Mapped[float | None] = mapped_column(Float)
    filters: Mapped[dict | None] = mapped_column(JsonType)
    result_count: Mapped[int | None] = mapped_column(Integer)


class RecommendationResult(Base):
    """One ranked creator for one search, with the reason it was recommended."""
    __tablename__ = "recommendation_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    search_id: Mapped[int] = mapped_column(
        ForeignKey("business_searches.id", ondelete="CASCADE"), index=True
    )
    creator_profile_id: Mapped[int] = mapped_column(
        ForeignKey("creator_profiles.id", ondelete="CASCADE"), index=True
    )
    rank: Mapped[int] = mapped_column(Integer)
    score: Mapped[float] = mapped_column(Float)
    method: Mapped[str] = mapped_column(String(50))  # e.g. "rule_based_v1"
    explanation: Mapped[dict | None] = mapped_column(JsonType)

    __table_args__ = (UniqueConstraint("search_id", "rank", name="uq_reco_search_rank"),)


class ModelRun(Base):
    """Training and evaluation metadata for each ML experiment."""
    __tablename__ = "model_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    model_name: Mapped[str] = mapped_column(String(80), index=True)
    task: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(30))
    trained_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    train_rows: Mapped[int | None] = mapped_column(Integer)
    test_rows: Mapped[int | None] = mapped_column(Integer)
    metrics: Mapped[dict | None] = mapped_column(JsonType)
    params: Mapped[dict | None] = mapped_column(JsonType)
    artifact_path: Mapped[str | None] = mapped_column(String(255))
    notes: Mapped[str | None] = mapped_column(Text)
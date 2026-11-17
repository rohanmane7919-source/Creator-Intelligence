import os

os.environ.setdefault("DB_PASSWORD", "test-only")  # tests never touch PostgreSQL

import pandas as pd  # noqa: E402
import pytest  # noqa: E402
from sqlalchemy import create_engine, func, select  # noqa: E402
from sqlalchemy.exc import IntegrityError  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.database.session import Base  # noqa: E402
from app.models.entities import (  # noqa: E402
    Category, CreatorMetric, CreatorProfile, ImportBatch, Platform,
)
from app.services.cleaning import clean_dataset  # noqa: E402
from app.services.importer import ImportConflictError, import_clean_dataframe  # noqa: E402


@pytest.fixture
def db():
    engine = create_engine("sqlite://")  # in-memory
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def make_clean():
    raw = pd.DataFrame({
        "id": [1, 2, 3],
        "platform": ["YouTube", "TikTok", "YouTube"],
        "content_id": ["content_1", "content_2", "content_3"],
        "creator_id": ["creator_1", "creator_2", "creator_3"],
        "creator_name": ["ann", "bob", None],
        "content_category": ["beauty", "tech", "cooking"],
        "post_date": ["5/29/23 12:15 AM", "5/30/23 1:00 PM", "6/1/23 2:00 PM"],
        "language": ["English", "Hindi", "English"],
        "content_type": ["video", "image", "video"],
        "hashtags": ["a,b", None, "c"],
        "comments_text": ["hi", "yo", None],
        "views": [1000, 2000, 500],
        "likes": [100, 200, 50],
        "shares": [10, 20, 5],
        "comments_count": [10, 20, 5],
        "follower_count": [10000, 20000, 5000],
        "is_sponsored": [True, False, False],
        "audience_age_distribution": ["19-25", "26-35", "19-25"],
        "audience_gender_distribution": ["female", "unknown", "male"],
        "audience_location": ["UK", "USA", "India"],
    })
    clean, report = clean_dataset(raw)
    return clean, report


def count(db, model):
    return db.scalar(select(func.count()).select_from(model))


def test_import_creates_linked_rows(db):
    clean, report = make_clean()
    result = import_clean_dataframe(db, clean, report, "test.csv")
    assert result["profiles"] == 3 and result["metrics"] == 3
    assert count(db, CreatorProfile) == 3 and count(db, CreatorMetric) == 3
    assert count(db, Category) == 11  # 10 targets + Unmapped
    assert {p.name for p in db.scalars(select(Platform))} == {"YouTube", "TikTok"}
    batch = db.scalars(select(ImportBatch)).one()
    assert batch.rows_imported == 3 and batch.quality_report["rows_out"] == 3


def test_missing_values_stored_as_null_and_completeness(db):
    clean, report = make_clean()
    import_clean_dataframe(db, clean, report, "test.csv")
    by_id = {p.source_content_id: p for p in db.scalars(select(CreatorProfile))}
    assert by_id["content_3"].creator_name is None
    assert by_id["content_2"].has_hashtags is False
    assert by_id["content_3"].has_comments_text is False
    assert by_id["content_1"].completeness_pct == 100.0
    # content_2: hashtags missing + gender "unknown" -> 6 of 8 fields
    assert by_id["content_2"].completeness_pct == 75.0
    assert by_id["content_3"].category.name == "Unmapped"


def test_existing_data_blocks_import_without_replace(db):
    clean, report = make_clean()
    import_clean_dataframe(db, clean, report, "test.csv")
    with pytest.raises(ImportConflictError):
        import_clean_dataframe(db, clean, report, "test.csv")
    assert count(db, CreatorProfile) == 3


def test_replace_does_not_double_the_data(db):
    clean, report = make_clean()
    import_clean_dataframe(db, clean, report, "test.csv")
    import_clean_dataframe(db, clean, report, "test.csv", replace=True)
    assert count(db, CreatorProfile) == 3 and count(db, CreatorMetric) == 3
    assert count(db, ImportBatch) == 2  # history of runs is kept


def test_failed_import_rolls_back_everything(db):
    clean, report = make_clean()
    bad = pd.concat([clean, clean.iloc[[0]]], ignore_index=True)  # duplicate content_id
    with pytest.raises(IntegrityError):
        import_clean_dataframe(db, bad, report, "bad.csv")
    assert count(db, CreatorProfile) == 0
    assert count(db, ImportBatch) == 0
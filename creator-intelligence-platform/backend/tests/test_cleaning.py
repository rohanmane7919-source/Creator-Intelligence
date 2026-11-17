import pandas as pd
import pytest

from app.services.cleaning import clean_dataset


def make_raw():
    return pd.DataFrame({
        "ID": [1, 2, 3, 4, 5, 6],
        "Platform ": ["youtube", "TikTok", "TikTok", "Instagram", "Instagram", "RedNote"],
        "content_id": ["content_1", "content_2", "content_2", "content_4", "content_5", "content_6"],
        "creator_id": ["creator_1", "creator_2", "creator_2", "creator_4", "creator_5", "creator_6"],
        "content_category": ["beauty", "tech", "tech", "cooking", "lifestyle", "beauty"],
        "post_date": ["5/29/23 12:15 AM"] * 4 + ["not a date", "5/30/23 1:00 PM"],
        "views": [1000, 2000, 2000, 500, "abc", -5],
        "likes": [100, 200, 200, 50, 10, 1],
        "shares": [10, 20, 20, 5, 1, 1],
        "comments_count": [10, 20, 20, 5, 1, 1],
        "follower_count": [10000, 20000, 20000, 5000, 3000, 100],
        "is_sponsored": ["True", "False", "False", "false", "true", "False"],
    })


def test_removes_duplicates_and_invalid_rows():
    raw = make_raw()
    clean, report = clean_dataset(raw)
    assert report["rows_removed"]["duplicate_content_id"] == 1 or report["rows_removed"]["exact_duplicates"] == 1
    assert report["rows_removed"]["invalid_rows_removed"] == 2  # "abc" views and negative views
    assert report["rows_out"] == 3
    assert list(clean["content_id"]) == ["content_1", "content_2", "content_4"]


def test_engagement_is_in_percent():
    clean, _ = clean_dataset(make_raw())
    row = clean[clean["content_id"] == "content_1"].iloc[0]
    assert row["engagement_rate_views_pct"] == pytest.approx(12.0)      # (100+10+10)/1000*100
    assert row["engagement_rate_followers_pct"] == pytest.approx(1.2)   # 120/10000*100


def test_category_mapping_keeps_unknown_identifiable():
    clean, _ = clean_dataset(make_raw())
    by_id = clean.set_index("content_id")
    assert by_id.loc["content_1", "category_clean"] == "Beauty & Skincare"
    assert by_id.loc["content_2", "category_clean"] == "Technology & Gadgets"
    assert by_id.loc["content_4", "category_clean"] == "Unmapped"
    assert by_id.loc["content_4", "category_mapping"] == "unmapped"


def test_platform_and_bool_normalised():
    clean, _ = clean_dataset(make_raw())
    assert clean["platform"].iloc[0] == "YouTube"
    assert clean["is_sponsored"].tolist() == [True, False, False]


def test_missing_required_column_raises():
    with pytest.raises(ValueError):
        clean_dataset(make_raw().drop(columns=["views"]))


def test_raw_dataframe_not_modified():
    raw = make_raw()
    snapshot = raw.copy()
    clean_dataset(raw)
    pd.testing.assert_frame_equal(raw, snapshot)
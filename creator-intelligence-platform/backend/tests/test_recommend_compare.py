"""Tests for Recommendations and Compare (in-memory SQLite)."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.session import Base, get_db
from app.main import app
from app.models.entities import (
    BusinessSearch, Category, CreatorMetric, CreatorProfile, ImportBatch, Platform,
    RecommendationResult,
)


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()

    ig, yt = Platform(name="Instagram"), Platform(name="YouTube")
    beauty = Category(name="Beauty & Skincare", is_target=True)
    tech = Category(name="Technology & Gadgets", is_target=True)
    batch = ImportBatch(source_file="t.csv", rows_in=4, rows_imported=4)
    db.add_all([ig, yt, beauty, tech, batch])
    db.flush()

    ids = {}

    def add(n, name, plat, cat, followers, eng, reach, comp, mapping, flag=False):
        p = CreatorProfile(
            batch_id=batch.id, source_content_id=f"c{n}", source_creator_id=f"S{n}",
            creator_name=name, platform_id=plat.id, category_id=cat.id,
            category_mapping=mapping, language="English", content_type="Video",
            follower_count=followers, has_hashtags=True, has_comments_text=True,
            completeness_pct=comp, is_sponsored=False,
        )
        db.add(p)
        db.flush()
        db.add(CreatorMetric(
            creator_profile_id=p.id, views=1000, likes=50, shares=5, comments_count=5,
            engagement_rate_views_pct=eng, engagement_rate_followers_pct=1.0,
            reach_rate_pct=reach, flag_likes_exceed_views=flag,
        ))
        ids[name] = p.id

    add(1, "A", ig, beauty, 100_000, 6.0, 40.0, 100.0, "direct")
    add(2, "B", ig, beauty, 100_000, 6.0, 40.0, 100.0, "partial")
    add(3, "C", yt, tech, 500_000, 3.0, 10.0, 60.0, "direct")
    add(4, "D", ig, beauty, 100_000, 6.0, 40.0, 100.0, "direct", flag=True)
    db.commit()

    def override():
        yield db

    app.dependency_overrides[get_db] = override
    c = TestClient(app)
    c.db, c.ids = db, ids
    yield c
    app.dependency_overrides.clear()
    db.close()


BEAUTY = {"industry": "Beauty & Skincare", "min_followers": 50_000, "max_followers": 150_000}


def _by_name(j):
    return {i["creator_name"]: i for i in j["items"]}


def test_direct_ranks_above_partial_and_scores(client):
    j = client.post("/api/recommendations/search", json=BEAUTY).json()
    items = _by_name(j)
    assert j["items"][0]["creator_name"] == "A"
    assert items["A"]["score"] == 80.0   # 30 + 8 + 12 + 15 + 15
    assert items["B"]["score"] == 65.0   # partial category: 15 instead of 30
    assert j["method"] == "rule_based_v1"


def test_explanation_matches_score(client):
    j = client.post("/api/recommendations/search", json=BEAUTY).json()
    for it in j["items"]:
        assert abs(sum(it["components"].values()) - it["score"]) < 0.3
        assert it["reasons"]


def test_flagged_record_is_penalised(client):
    items = _by_name(client.post("/api/recommendations/search", json=BEAUTY).json())
    assert abs(items["A"]["score"] - items["D"]["score"] - 15.0) < 0.1
    assert items["D"]["warnings"]


def test_hard_filters(client):
    j = client.post("/api/recommendations/search",
                    json={"industry": "Technology & Gadgets", "platform": "YouTube"}).json()
    assert [i["creator_name"] for i in j["items"]] == ["C"]
    j = client.post("/api/recommendations/search",
                    json={**BEAUTY, "min_followers": 200_000, "max_followers": 300_000}).json()
    assert j["items"] == [] and j["total_candidates"] == 0


def test_no_results_is_ok(client):
    r = client.post("/api/recommendations/search", json={"industry": "Gaming & Esports"})
    assert r.status_code == 200 and r.json()["items"] == []


def test_search_is_saved_to_history(client):
    j = client.post("/api/recommendations/search", json=BEAUTY).json()
    assert client.db.scalar(select(func.count()).select_from(BusinessSearch)) == 1
    saved = client.db.scalar(select(func.count()).select_from(RecommendationResult))
    assert saved == len(j["items"]) == 3


def test_validation(client):
    bad = [
        {"min_followers": 10, "max_followers": 5},
        {"objective": "profit"},
        {"limit": 0},
        {"limit": 500},
    ]
    for body in bad:
        assert client.post("/api/recommendations/search", json=body).status_code == 422


def test_compare_ok(client):
    a, c = client.ids["A"], client.ids["C"]
    j = client.get(f"/api/compare?ids={a},{c}").json()
    assert [i["id"] for i in j["items"]] == [a, c]
    assert j["highlights"]["follower_count"] == [c]
    assert j["highlights"]["engagement_rate_views_pct"] == [a]
    assert j["highlights"]["engagement_rate_followers_pct"] == []  # equal values


def test_compare_bad_ids(client):
    a = client.ids["A"]
    assert client.get(f"/api/compare?ids={a}").status_code == 422
    assert client.get(f"/api/compare?ids={a},{a}").status_code == 422
    assert client.get("/api/compare?ids=1,abc").status_code == 422
    assert client.get("/api/compare?ids=1,2,3,4,5").status_code == 422


def test_compare_missing_record(client):
    a = client.ids["A"]
    assert client.get(f"/api/compare?ids={a},99999").status_code == 404
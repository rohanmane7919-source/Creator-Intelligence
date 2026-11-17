"""Tests for the Discovery endpoints (in-memory SQLite, no PostgreSQL needed)."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.discovery import get_db
from app.database.session import Base
from app.main import app
from app.models.entities import (
    Category, CreatorMetric, CreatorProfile, ImportBatch, Platform,
)


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    ig, yt = Platform(name="Instagram"), Platform(name="YouTube")
    beauty = Category(name="Beauty & Skincare", is_target=True)
    tech = Category(name="Technology & Gadgets", is_target=True)
    batch = ImportBatch(source_file="t.csv", rows_in=4, rows_imported=4)
    db.add_all([ig, yt, beauty, tech, batch])
    db.flush()

    def add(cid, source, name, plat, cat, followers, eng):
        p = CreatorProfile(
            batch_id=batch.id, source_content_id=cid, source_creator_id=source,
            creator_name=name, platform_id=plat.id, category_id=cat.id,
            category_mapping="direct", language="English", content_type="Video",
            follower_count=followers, has_hashtags=True, has_comments_text=True,
            completeness_pct=80.0, is_sponsored=False,
        )
        db.add(p)
        db.flush()
        db.add(CreatorMetric(
            creator_profile_id=p.id, views=1000, likes=50, shares=5, comments_count=5,
            engagement_rate_views_pct=eng, engagement_rate_followers_pct=1.0,
            reach_rate_pct=10.0,
        ))

    add("c1", "S1", "Asha Glow", ig, beauty, 10_000, 6.0)
    add("c2", "S2", "Tech Ravi", yt, tech, 500_000, 3.0)
    add("c3", "S3", "Mira_100%", ig, beauty, 50_000, 9.0)
    add("c4", "S1", "Asha Glow", yt, tech, 900_000, 2.0)  # same ID, different details
    db.commit()

    def override():
        yield db

    app.dependency_overrides[get_db] = override
    yield TestClient(app)
    app.dependency_overrides.clear()
    db.close()


def test_filters(client):
    j = client.get("/api/discovery/filters").json()
    assert j["platforms"] == ["Instagram", "YouTube"]
    assert j["follower_min"] == 10_000 and j["follower_max"] == 900_000


def test_default_sort_followers_desc(client):
    j = client.get("/api/discovery/creators").json()
    assert j["total"] == 4
    assert [i["follower_count"] for i in j["items"]] == [900_000, 500_000, 50_000, 10_000]


def test_filter_platform_and_category(client):
    j = client.get("/api/discovery/creators?platform=Instagram&category=Beauty %26 Skincare").json()
    assert j["total"] == 2


def test_follower_range(client):
    j = client.get("/api/discovery/creators?min_followers=20000&max_followers=600000").json()
    assert {i["creator_name"] for i in j["items"]} == {"Tech Ravi", "Mira_100%"}


def test_min_engagement(client):
    j = client.get("/api/discovery/creators?min_engagement=5").json()
    assert j["total"] == 2


def test_search_text_is_literal(client):
    assert client.get("/api/discovery/creators?q=ravi").json()["total"] == 1
    assert client.get("/api/discovery/creators?q=100%25").json()["total"] == 1  # % not a wildcard
    assert client.get("/api/discovery/creators?q=%25").json()["total"] == 1      # only the real "%"


def test_pagination(client):
    j = client.get("/api/discovery/creators?page_size=3&page=2").json()
    assert j["pages"] == 2 and len(j["items"]) == 1


def test_invalid_params(client):
    assert client.get("/api/discovery/creators?min_followers=10&max_followers=5").status_code == 422
    assert client.get("/api/discovery/creators?sort=bogus").status_code == 422
    assert client.get("/api/discovery/creators?page_size=1000").status_code == 422


def test_detail_with_identity_warning(client):
    first = client.get("/api/discovery/creators?q=S1&sort=followers&order=asc").json()["items"][0]
    d = client.get(f"/api/discovery/creators/{first['id']}").json()
    assert d["same_id_records"] == 2
    assert d["identity_warning"] is not None


def test_detail_clean_and_missing(client):
    ravi = client.get("/api/discovery/creators?q=Ravi").json()["items"][0]
    assert client.get(f"/api/discovery/creators/{ravi['id']}").json()["identity_warning"] is None
    assert client.get("/api/discovery/creators/99999").status_code == 404
import os

os.environ.setdefault("DB_PASSWORD", "test-only")  # tests never touch PostgreSQL

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.database.session import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.services.importer import ensure_categories, import_clean_dataframe  # noqa: E402
from tests.test_importer import make_clean  # noqa: E402


def make_client(with_data: bool):
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        if with_data:
            clean, report = make_clean()
            import_clean_dataframe(s, clean, report, "test.csv")
        else:
            ensure_categories(s)
            s.commit()

    def override():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db] = override
    return TestClient(app)


@pytest.fixture
def client():
    yield make_client(True)
    app.dependency_overrides.clear()


@pytest.fixture
def empty_client():
    yield make_client(False)
    app.dependency_overrides.clear()


def test_summary_kpis_come_from_the_database(client):
    r = client.get("/api/dashboard/summary")
    assert r.status_code == 200
    k = r.json()["kpis"]
    assert k["total_records"] == 3
    assert k["total_followers"] == 35000  # 10000 + 20000 + 5000
    assert k["sponsored_share_pct"] == pytest.approx(100 / 3)
    # engagement per view: 12.0, 12.0, 12.0 for the three test rows
    assert k["avg_engagement_rate_views_pct"] == pytest.approx(12.0)


def test_category_coverage_lists_every_category_and_flags_empty_ones(client):
    cats = {c["name"]: c for c in client.get("/api/dashboard/summary").json()["categories"]}
    assert len(cats) == 11
    assert cats["Beauty & Skincare"]["count"] == 1 and cats["Beauty & Skincare"]["has_data"]
    assert cats["Fitness & Sports"]["count"] == 0 and not cats["Fitness & Sports"]["has_data"]
    assert cats["Unmapped"]["count"] == 1 and cats["Unmapped"]["is_target"] is False


def test_follower_tiers_and_platforms(client):
    body = client.get("/api/dashboard/summary").json()
    tiers = {t["name"]: t["count"] for t in body["follower_tiers"]}
    assert tiers == {"Under 10K": 1, "10K to 100K": 2, "100K to 500K": 0, "500K and above": 0}
    plats = {p["name"]: p["count"] for p in body["platforms"]}
    assert plats == {"YouTube": 2, "TikTok": 1}


def test_data_quality_exposes_cleaning_warnings(client):
    dq = client.get("/api/dashboard/summary").json()["data_quality"]
    assert dq["source_file"] == "test.csv" and dq["rows_imported"] == 3
    assert isinstance(dq["warnings"], list)


def test_top_creators_default_is_followers(client):
    body = client.get("/api/dashboard/top-creators").json()
    assert body["metric"] == "followers" and body["unit"] == "count"
    assert [i["source_content_id"] for i in body["items"]] == ["content_2", "content_1", "content_3"]
    assert body["items"][0]["value"] == 20000


def test_top_creators_respects_limit_and_metric(client):
    body = client.get("/api/dashboard/top-creators?metric=likes&limit=1").json()
    assert len(body["items"]) == 1 and body["items"][0]["value"] == 200
    assert client.get("/api/dashboard/top-creators?metric=reach_rate_pct").json()["unit"] == "percent"


def test_top_creators_rejects_bad_input(client):
    assert client.get("/api/dashboard/top-creators?metric=password").status_code == 422
    assert client.get("/api/dashboard/top-creators?limit=0").status_code == 422
    assert client.get("/api/dashboard/top-creators?limit=500").status_code == 422


def test_empty_database_returns_zeros_not_fake_numbers(empty_client):
    body = empty_client.get("/api/dashboard/summary").json()
    assert body["kpis"]["total_records"] == 0 and body["kpis"]["total_followers"] == 0
    assert body["kpis"]["avg_engagement_rate_views_pct"] is None
    assert body["data_quality"] is None and body["recent_searches"] == [] and body["models"] == []
    assert empty_client.get("/api/dashboard/top-creators").json()["items"] == []

"""Database helper. Run from the project root:
    python scripts\\db_tools.py setup            create tables + reference data
    python scripts\\db_tools.py import           import data\\processed\\posts_clean.csv
    python scripts\\db_tools.py import --replace wipe old creator rows first
    python scripts\\db_tools.py verify           check what is stored
"""
import argparse
import json
import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import func, inspect, select
from sqlalchemy.exc import SQLAlchemyError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.database.session import Base, SessionLocal, engine  # noqa: E402
from app.models import entities as m  # noqa: E402
from app.services.importer import (  # noqa: E402
    ImportConflictError, ensure_categories, import_clean_dataframe,
)

CLEAN_CSV = ROOT / "data" / "processed" / "posts_clean.csv"
REPORT_JSON = ROOT / "data" / "processed" / "quality_report.json"


def load_clean() -> pd.DataFrame:
    if not CLEAN_CSV.exists():
        sys.exit(f"Missing {CLEAN_CSV}. Run: python scripts\\run_cleaning.py")
    df = pd.read_csv(CLEAN_CSV, low_memory=False)
    df["post_date"] = pd.to_datetime(df["post_date"], errors="coerce")
    return df


def cmd_setup():
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        ensure_categories(db)
        db.commit()
    tables = inspect(engine).get_table_names()
    print("Tables in database:", ", ".join(sorted(tables)))
    print("Setup complete.")


def cmd_import(replace: bool):
    df = load_clean()
    report = json.loads(REPORT_JSON.read_text(encoding="utf-8")) if REPORT_JSON.exists() else None
    with SessionLocal() as db:
        result = import_clean_dataframe(db, df, report, CLEAN_CSV.name, replace=replace)
    print("Import complete:", result)


def cmd_verify():
    df = load_clean()
    ok = True

    def check(label, passed, detail=""):
        nonlocal ok
        ok = ok and passed
        print(f"[{'PASS' if passed else 'FAIL'}] {label} {detail}")

    with SessionLocal() as db:
        print("ROW COUNTS")
        for model in [m.Platform, m.Category, m.ImportBatch, m.CreatorProfile,
                      m.CreatorMetric, m.BusinessSearch, m.RecommendationResult, m.ModelRun]:
            n = db.scalar(select(func.count()).select_from(model))
            print(f"  {model.__tablename__:<24} {n}")

        profiles = db.scalar(select(func.count()).select_from(m.CreatorProfile))
        metrics = db.scalar(select(func.count()).select_from(m.CreatorMetric))
        print("\nCHECKS AGAINST data/processed/posts_clean.csv")
        check("profile rows equal CSV rows", profiles == len(df), f"({profiles} vs {len(df)})")
        check("metric rows equal CSV rows", metrics == len(df), f"({metrics} vs {len(df)})")
        db_followers = db.scalar(select(func.sum(m.CreatorProfile.follower_count)))
        check("sum of follower_count matches", db_followers == int(df["follower_count"].sum()),
              f"({db_followers} vs {int(df['follower_count'].sum())})")
        db_eng = db.scalar(select(func.avg(m.CreatorMetric.engagement_rate_views_pct)))
        check("average engagement matches", abs(db_eng - df["engagement_rate_views_pct"].mean()) < 1e-6,
              f"({db_eng:.4f} vs {df['engagement_rate_views_pct'].mean():.4f})")
        orphans = db.scalar(
            select(func.count()).select_from(m.CreatorMetric)
            .outerjoin(m.CreatorProfile, m.CreatorMetric.creator_profile_id == m.CreatorProfile.id)
            .where(m.CreatorProfile.id.is_(None))
        )
        check("no metric row without a profile", orphans == 0)

        print("\nCREATORS BY PLATFORM")
        for name, n in db.execute(
            select(m.Platform.name, func.count()).join(m.CreatorProfile)
            .group_by(m.Platform.name).order_by(func.count().desc())
        ):
            print(f"  {name:<12} {n}")

        print("\nCREATORS BY CATEGORY")
        for name, n in db.execute(
            select(m.Category.name, func.count()).join(m.CreatorProfile)
            .group_by(m.Category.name).order_by(func.count().desc())
        ):
            print(f"  {name:<24} {n}")

        print("\nSAMPLE (3 joined rows)")
        rows = db.execute(
            select(m.CreatorProfile.source_content_id, m.CreatorProfile.creator_name,
                   m.Platform.name, m.Category.name, m.CreatorProfile.follower_count,
                   m.CreatorMetric.engagement_rate_views_pct, m.CreatorProfile.completeness_pct)
            .join(m.Platform, m.CreatorProfile.platform_id == m.Platform.id)
            .join(m.Category, m.CreatorProfile.category_id == m.Category.id)
            .join(m.CreatorMetric, m.CreatorMetric.creator_profile_id == m.CreatorProfile.id)
            .limit(3)
        ).all()
        for r in rows:
            print(" ", tuple(r))

    print("\nOVERALL:", "ALL CHECKS PASSED" if ok else "SOME CHECKS FAILED")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("setup")
    p_imp = sub.add_parser("import")
    p_imp.add_argument("--replace", action="store_true")
    sub.add_parser("verify")
    args = parser.parse_args()
    try:
        if args.cmd == "setup":
            cmd_setup()
        elif args.cmd == "import":
            cmd_import(args.replace)
        else:
            cmd_verify()
    except ImportConflictError as e:
        sys.exit(f"NOT IMPORTED: {e}")
    except SQLAlchemyError as e:
        sys.exit(f"DATABASE ERROR: {e.__class__.__name__}: {str(e).splitlines()[0]}")

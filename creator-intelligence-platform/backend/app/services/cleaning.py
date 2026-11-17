"""Reproducible cleaning pipeline (Stage 3).

Input : raw DataFrame (one row per post)
Output: (clean DataFrame, quality-report dict)

The raw file is never modified: every step works on a copy.
"""
import re

import numpy as np
import pandas as pd

REQUIRED_COLUMNS = [
    "content_id", "creator_id", "platform", "post_date",
    "views", "likes", "shares", "comments_count", "follower_count",
]
KEY_METRICS = ["views", "likes", "shares", "comments_count", "follower_count"]
OPTIONAL_NUMERIC = ["content_length"]

# Only categories the data genuinely supports. Everything else stays "Unmapped".
CATEGORY_MAP = {
    "beauty": ("Beauty & Skincare", "direct"),
    "lifestyle": ("Fashion & Lifestyle", "partial"),  # lifestyle is broader than fashion
    "tech": ("Technology & Gadgets", "direct"),
}

PLATFORM_MAP = {
    "youtube": "YouTube", "instagram": "Instagram", "tiktok": "TikTok",
    "bilibili": "Bilibili", "rednote": "RedNote", "xiaohongshu": "RedNote",
}


# ---------- small helpers ----------
def standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out.columns = [
        re.sub(r"[^0-9a-zA-Z]+", "_", str(c).strip()).strip("_").lower()
        for c in out.columns
    ]
    return out


def _strip_text(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for c in out.columns:
        s = out[c]
        if pd.api.types.is_object_dtype(s) or pd.api.types.is_string_dtype(s):
            s = s.map(lambda v: v.strip() if isinstance(v, str) else v)
            out[c] = s.replace("", np.nan)
    return out


def _missing_counts(df: pd.DataFrame) -> dict:
    counts = df.isna().sum()
    return {c: int(n) for c, n in counts.items() if n > 0}


def _parse_dates(s: pd.Series) -> pd.Series:
    parsed = pd.to_datetime(s, format="%m/%d/%y %I:%M %p", errors="coerce")
    leftover = parsed.isna() & s.notna()
    if leftover.any():
        parsed[leftover] = pd.to_datetime(s[leftover], format="mixed", errors="coerce")
    return parsed


def _to_bool(v):
    if isinstance(v, (bool, np.bool_)):
        return bool(v)
    if isinstance(v, str):
        return {"true": True, "1": True, "yes": True,
                "false": False, "0": False, "no": False}.get(v.strip().lower())
    if isinstance(v, (int, float)) and not pd.isna(v):
        return bool(v)
    return None


def _map_category(v):
    if not isinstance(v, str):
        return ("Unmapped", "unmapped")
    return CATEGORY_MAP.get(v.strip().lower(), ("Unmapped", "unmapped"))


def _map_platform(v):
    if not isinstance(v, str):
        return None
    return PLATFORM_MAP.get(v.strip().lower(), v.strip().title())


def _trailing_number(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s.astype("string").str.extract(r"(\d+)$")[0], errors="coerce")


def _cv(s: pd.Series) -> float:
    m = float(s.mean())
    return float(s.std() / m) if m else 0.0


# ---------- diagnostics ----------
def creator_id_consistency(df: pd.DataFrame) -> dict:
    """Does one creator_id behave like one real account?"""
    sizes = df.groupby("creator_id").size()
    multi = sizes[sizes >= 2].index
    out = {"creator_ids": int(len(sizes)), "ids_with_2plus_posts": int(len(multi))}
    if len(multi) == 0:
        return out
    g = df[df["creator_id"].isin(multi)].groupby("creator_id")
    for col in ["platform", "category_clean", "follower_count"]:
        out[f"pct_ids_with_multiple_{col}"] = round(float((g[col].nunique() > 1).mean() * 100), 1)
    spread = g["follower_count"].agg(["min", "max"])
    out["median_follower_max_to_min_ratio"] = round(float((spread["max"] / spread["min"]).median()), 2)
    return out


def creator_id_hash_check(df: pd.DataFrame):
    """% of rows where creator number == content number modulo (#creator_ids)."""
    n = df["creator_id"].nunique()
    if n == 0:
        return None
    ok = (_trailing_number(df["content_id"]) % n) == _trailing_number(df["creator_id"])
    return round(float(ok.mean() * 100), 1)


# ---------- main pipeline ----------
def clean_dataset(raw: pd.DataFrame):
    report = {"rows_in": int(len(raw))}
    df = standardize_columns(raw)

    missing_cols = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")
    report["columns"] = list(df.columns)

    df = _strip_text(df)
    report["missing_before"] = _missing_counts(df)
    removed = {}

    # 1) identifiers, then duplicates (the surrogate "id" column is ignored)
    no_id = df[["content_id", "creator_id"]].isna().any(axis=1)
    removed["missing_identifier"] = int(no_id.sum())
    df = df[~no_id]

    subset = [c for c in df.columns if c != "id"]
    exact = df.duplicated(subset=subset, keep="first")
    removed["exact_duplicates"] = int(exact.sum())
    df = df[~exact]

    dup_id = df.duplicated(subset=["content_id"], keep="first")
    removed["duplicate_content_id"] = int(dup_id.sum())
    df = df[~dup_id].copy()

    # 2) numeric conversion
    coerced = {}
    for col in KEY_METRICS + [c for c in OPTIONAL_NUMERIC if c in df.columns]:
        before = int(df[col].isna().sum())
        df[col] = pd.to_numeric(df[col], errors="coerce")
        coerced[col] = int(df[col].isna().sum()) - before
    report["non_numeric_set_to_missing"] = coerced

    # 3) dates (rows with bad dates are kept, the date stays empty)
    df["post_date"] = _parse_dates(df["post_date"])
    report["missing_or_unparseable_dates"] = int(df["post_date"].isna().sum())

    # 4) invalid values (a row may match several reasons)
    bad = {
        "missing_key_metric": df[KEY_METRICS].isna().any(axis=1),
        "negative_value": (df[KEY_METRICS] < 0).any(axis=1),
        "non_positive_views": df["views"] <= 0,
        "non_positive_followers": df["follower_count"] <= 0,
    }
    drop = pd.concat(bad.values(), axis=1).any(axis=1)
    for k, v in bad.items():
        removed[f"invalid_{k}"] = int(v.sum())
    removed["invalid_rows_removed"] = int(drop.sum())
    df = df[~drop].copy()

    # 5) flags (kept, not removed) and engagement metrics, all in PERCENT
    inter = df["likes"] + df["comments_count"] + df["shares"]
    df["flag_likes_exceed_views"] = df["likes"] > df["views"]
    df["flag_interactions_exceed_followers"] = inter > df["follower_count"]
    df["engagement_rate_views_pct"] = (inter / df["views"] * 100).round(4)
    df["engagement_rate_followers_pct"] = (inter / df["follower_count"] * 100).round(4)
    df["reach_rate_pct"] = (df["views"] / df["follower_count"] * 100).round(4)

    # 6) normalisation; the original category is kept for traceability
    df["platform"] = df["platform"].map(_map_platform)
    if "content_category" in df.columns:
        mapped = df["content_category"].map(_map_category)
    else:
        mapped = pd.Series([("Unmapped", "unmapped")] * len(df), index=df.index)
    df["category_clean"] = mapped.map(lambda t: t[0])
    df["category_mapping"] = mapped.map(lambda t: t[1])
    if "is_sponsored" in df.columns:
        df["is_sponsored"] = df["is_sponsored"].map(_to_bool)

    df = df.reset_index(drop=True)

    # 7) report
    report["rows_removed"] = removed
    report["rows_out"] = int(len(df))
    report["missing_after"] = _missing_counts(df)
    report["category_mapping_counts"] = {
        f"{r} -> {c} ({m})": int(n)
        for (r, c, m), n in pd.DataFrame({
            "r": df.get("content_category", pd.Series(["(none)"] * len(df))),
            "c": df["category_clean"], "m": df["category_mapping"],
        }).value_counts(dropna=False).items()
    }
    report["flags"] = {
        "likes_exceed_views": int(df["flag_likes_exceed_views"].sum()),
        "interactions_exceed_followers": int(df["flag_interactions_exceed_followers"].sum()),
    }
    dates = df["post_date"].dropna()
    report["date_range"] = (
        [str(dates.min()), str(dates.max())] if len(dates) else None
    )
    report["creator_id_consistency"] = creator_id_consistency(df)
    report["creator_id_hash_match_pct"] = creator_id_hash_check(df)

    # 8) automatic, dataset-agnostic warnings
    warnings = []
    cons = report["creator_id_consistency"]
    if cons.get("pct_ids_with_multiple_platform", 0) > 90:
        warnings.append(
            "creator_id does not identify a consistent account: platform, category and "
            "follower_count change between posts that share a creator_id. Do not treat "
            "creator_id as one real creator."
        )
    for col in ["views", "likes", "engagement_rate_views_pct"]:
        cv = _cv(df[col]) if len(df) > 1 else 0.0
        if len(df) > 1 and cv < 0.05:
            warnings.append(
                f"'{col}' varies by only {cv:.1%} across all rows. Real social-media data "
                "normally varies far more, so the data may be synthetic or capped."
            )
    report["warnings"] = warnings
    return df, report
"""Rule-based trust & risk signals (Stage 7).

IMPORTANT: this is NOT a fraud detector and NOT machine learning. It counts
transparent, configurable signals. A triggered signal means "this record looks
unusual and deserves a human look", never "this creator is fraudulent".
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

import pandas as pd

DISCLAIMER = (
    "Risk signals are statistical or data-quality indicators, not proof of "
    "fraud. Unusual values can have innocent explanations (viral posts, small "
    "accounts, data-entry errors). Use them to prioritise manual review only."
)
MIN_BASELINE_N = 100  # smallest platform sample we trust for percentile baselines


@dataclass(frozen=True)
class RiskConfig:
    """All thresholds and weights live here so they can be tuned or exposed in the UI."""
    w_interactions_exceed_followers: float = 35
    w_likes_exceed_views: float = 35
    w_engagement_outlier: float = 25
    w_reach_outlier: float = 15
    w_weak_disclosure: float = 10
    w_low_completeness: float = 10
    outlier_percentile: float = 0.99
    min_completeness_pct: float = 60.0
    medium_threshold: float = 25
    high_threshold: float = 50


@dataclass
class Signal:
    key: str
    label: str
    group: str            # "anomaly" | "disclosure" | "data_quality"
    evaluated: bool       # False when the needed data is missing
    triggered: bool
    weight: float
    value: float | str | None
    threshold: float | str | None
    explanation: str


def build_baselines(df: pd.DataFrame, percentile: float = 0.99) -> dict:
    """Per-platform percentile baselines from a DataFrame with columns
    platform, engagement_rate_followers_pct, reach_rate_pct."""
    out = {}
    for platform, g in df.groupby("platform"):
        out[platform] = {
            "n": int(len(g)),
            "engagement_followers_pct": float(g["engagement_rate_followers_pct"].quantile(percentile)),
            "reach_pct": float(g["reach_rate_pct"].quantile(percentile)),
        }
    return out


def _outlier_signal(key, label, value, base, base_key, weight, pct, platform):
    if value is None or base is None or base["n"] < MIN_BASELINE_N:
        return Signal(key, label, "anomaly", False, False, weight, value, None,
                      "Not evaluated: missing value or too few records on this platform.")
    limit = base[base_key]
    hit = value > limit
    return Signal(
        key, label, "anomaly", True, hit, weight, round(float(value), 2), round(limit, 2),
        (f"{value:.2f}% is above the {pct:.0%} percentile ({limit:.2f}%) of {platform} posts."
         if hit else f"{value:.2f}% is within the normal range for {platform} posts."),
    )


def assess_post(record: dict, baselines: dict, config: RiskConfig | None = None) -> dict:
    """Score one record. `record` keys: platform, engagement_rate_followers_pct,
    reach_rate_pct, flag_likes_exceed_views, flag_interactions_exceed_followers,
    is_sponsored, disclosure_type, completeness_pct (any may be None)."""
    cfg = config or RiskConfig()
    platform = record.get("platform")
    base = baselines.get(platform)
    signals: list[Signal] = []

    # --- impossible/contradictory metrics -------------------------------
    for key, label, field, weight, text in [
        ("interactions_exceed_followers", "Interactions exceed followers",
         "flag_interactions_exceed_followers", cfg.w_interactions_exceed_followers,
         "Likes + comments + shares are larger than the follower count."),
        ("likes_exceed_views", "Likes exceed views", "flag_likes_exceed_views",
         cfg.w_likes_exceed_views, "Likes are larger than views, which is normally impossible."),
    ]:
        v = record.get(field)
        signals.append(Signal(
            key, label, "anomaly", v is not None, bool(v), weight, None if v is None else bool(v), True,
            text if v else ("Not triggered." if v is not None else "Not evaluated: flag missing."),
        ))

    # --- engagement outliers vs the platform's own distribution ----------
    signals.append(_outlier_signal(
        "engagement_outlier", "Unusually high engagement vs followers",
        record.get("engagement_rate_followers_pct"), base, "engagement_followers_pct",
        cfg.w_engagement_outlier, cfg.outlier_percentile, platform))
    signals.append(_outlier_signal(
        "reach_outlier", "Unusually high reach vs followers",
        record.get("reach_rate_pct"), base, "reach_pct",
        cfg.w_reach_outlier, cfg.outlier_percentile, platform))

    # --- disclosure (compliance, not authenticity) ------------------------
    spons, disc = record.get("is_sponsored"), record.get("disclosure_type")
    ev = spons is not None and disc is not None
    hit = bool(ev and spons and str(disc).lower() == "implicit")
    signals.append(Signal(
        "weak_disclosure", "Sponsored with implicit disclosure", "disclosure", ev, hit,
        cfg.w_weak_disclosure, disc, "explicit",
        "Sponsored content that does not clearly state the paid partnership." if hit
        else ("Not triggered." if ev else "Not evaluated: sponsorship info missing.")))

    # --- data quality -----------------------------------------------------
    comp = record.get("completeness_pct")
    ev = comp is not None
    hit = bool(ev and comp < cfg.min_completeness_pct)
    signals.append(Signal(
        "low_completeness", "Low data completeness", "data_quality", ev, hit,
        cfg.w_low_completeness, comp, cfg.min_completeness_pct,
        f"Only {comp}% of profile fields are filled in." if hit
        else ("Not triggered." if ev else "Not evaluated: completeness missing.")))

    score = min(100.0, sum(s.weight for s in signals if s.triggered))
    level = ("high" if score >= cfg.high_threshold
             else "medium" if score >= cfg.medium_threshold else "low")
    return {
        "risk_score": round(score, 1),
        "review_priority": level,
        "signals": [asdict(s) for s in signals],
        "triggered_count": sum(s.triggered for s in signals),
        "not_evaluated": [s.key for s in signals if not s.evaluated],
        "method": "rule_based_v1",
        "disclaimer": DISCLAIMER,
    }
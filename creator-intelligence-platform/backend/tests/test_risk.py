import pandas as pd
from app.services.risk import RiskConfig, assess_post, build_baselines


def _baselines():
    df = pd.DataFrame({
        "platform": ["TikTok"] * 200,
        "engagement_rate_followers_pct": [float(i) / 10 for i in range(200)],
        "reach_rate_pct": [float(i) / 5 for i in range(200)],
    })
    return build_baselines(df, 0.99)


def _clean(**over):
    r = dict(platform="TikTok", engagement_rate_followers_pct=1.0, reach_rate_pct=2.0,
             flag_likes_exceed_views=False, flag_interactions_exceed_followers=False,
             is_sponsored=False, disclosure_type="none", completeness_pct=100.0)
    r.update(over)
    return r


def test_clean_record_is_low_risk():
    res = assess_post(_clean(), _baselines())
    assert res["risk_score"] == 0 and res["review_priority"] == "low"


def test_interactions_exceed_followers_raises_to_medium():
    res = assess_post(_clean(flag_interactions_exceed_followers=True), _baselines())
    assert res["risk_score"] == 35 and res["review_priority"] == "medium"


def test_outlier_engagement_triggers():
    res = assess_post(_clean(engagement_rate_followers_pct=19.9), _baselines())
    keys = {s["key"] for s in res["signals"] if s["triggered"]}
    assert "engagement_outlier" in keys


def test_score_is_capped_at_100():
    res = assess_post(_clean(flag_interactions_exceed_followers=True,
                             flag_likes_exceed_views=True,
                             engagement_rate_followers_pct=19.9, reach_rate_pct=39.9,
                             is_sponsored=True, disclosure_type="implicit",
                             completeness_pct=10.0), _baselines())
    assert res["risk_score"] == 100 and res["review_priority"] == "high"


def test_missing_data_is_not_scored_as_risk():
    res = assess_post(_clean(engagement_rate_followers_pct=None, completeness_pct=None),
                      _baselines())
    assert "engagement_outlier" in res["not_evaluated"]
    assert res["risk_score"] == 0


def test_unknown_platform_skips_outlier_checks():
    res = assess_post(_clean(platform="Mastodon", engagement_rate_followers_pct=999),
                      _baselines())
    assert "engagement_outlier" in res["not_evaluated"]


def test_weights_are_configurable():
    cfg = RiskConfig(w_interactions_exceed_followers=60)
    res = assess_post(_clean(flag_interactions_exceed_followers=True), _baselines(), cfg)
    assert res["review_priority"] == "high"


def test_disclaimer_always_present():
    assert "not proof of fraud" in assess_post(_clean(), _baselines())["disclaimer"]
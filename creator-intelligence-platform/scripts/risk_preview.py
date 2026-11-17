import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

import pandas as pd
from app.services.importer import _completeness, _py
from app.services.risk import RiskConfig, assess_post, build_baselines

df = pd.read_csv(ROOT / "data" / "processed" / "posts_clean.csv")
cfg = RiskConfig()
baselines = build_baselines(df, cfg.outlier_percentile)

levels, triggers = Counter(), Counter()
for rec in df.to_dict("records"):
    rec = {k: _py(v) for k, v in rec.items()}
    rec["completeness_pct"] = _completeness(rec)
    res = assess_post(rec, baselines, cfg)
    levels[res["review_priority"]] += 1
    for s in res["signals"]:
        if s["triggered"]:
            triggers[s["key"]] += 1

print("Posts scored:", sum(levels.values()))
print("Review priority:", dict(levels))
print("Signals triggered:", dict(triggers))
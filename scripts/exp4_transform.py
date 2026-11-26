"""Exercise 4: target transformations, scored on VALIDATION only.

Kept separate from src/train.py so reports/metrics.json stays the
untransformed pipeline. Every model is fit on train (2011) and scored in
original units on valid (H1 2012). The test set is read only by `--final`,
which picks the best transform per model from the saved validation results
and scores those on test exactly once.

Run: python scripts/exp4_transform.py            # validation only
     python scripts/exp4_transform.py --final    # touches test, once
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.config import PROCESSED, ROOT, TARGET  # noqa: E402
from src.features import feature_columns  # noqa: E402
from src.train import temporal_split  # noqa: E402

VALID_OUT = ROOT / "reports" / "exp4_valid.json"
TEST_OUT = ROOT / "reports" / "exp4_test.json"

# name -> (forward: (y, X) -> target to fit, inverse: (pred, X) -> cnt)
TRANSFORMS = {
    "identity": (lambda y, X: y, lambda p, X: p),
    "log1p": (lambda y, X: np.log1p(y), lambda p, X: np.expm1(p)),
    # Predict today's count as a multiple of the trailing 7-day mean.
    "ratio_roll7": (
        lambda y, X: y / X["cnt_roll_7"],
        lambda p, X: p * X["cnt_roll_7"],
    ),
    # Predict the change from yesterday.
    "diff_lag1": (
        lambda y, X: y - X["cnt_lag_1"],
        lambda p, X: p + X["cnt_lag_1"],
    ),
}

MODELS = {
    "ridge": make_pipeline(StandardScaler(), Ridge(alpha=1.0)),
    "hgb": HistGradientBoostingRegressor(random_state=0, max_iter=300),
}


def run(model_name, transform_name, train, evalset, cols):
    fwd, inv = TRANSFORMS[transform_name]
    model = clone(MODELS[model_name])
    model.fit(train[cols], fwd(train[TARGET], train))
    pred = np.asarray(inv(model.predict(evalset[cols]), evalset), dtype=float)
    return {
        "r2": round(float(r2_score(evalset[TARGET], pred)), 4),
        "mae": round(float(mean_absolute_error(evalset[TARGET], pred)), 1),
    }


if __name__ == "__main__":
    df = pd.read_parquet(PROCESSED)
    cols = feature_columns(df)
    train, valid, test = temporal_split(df)

    if "--final" not in sys.argv:
        res = {m: {t: run(m, t, train, valid, cols) for t in TRANSFORMS} for m in MODELS}
        VALID_OUT.write_text(json.dumps(res, indent=2))
        print(f"{'model':6s} {'transform':12s} valid_r2  valid_mae")
        for m, ts in res.items():
            for t, s in ts.items():
                print(f"{m:6s} {t:12s} {s['r2']:8.4f}  {s['mae']:8.1f}")
    else:
        valid_res = json.loads(VALID_OUT.read_text())
        chosen = {m: max(ts, key=lambda t: ts[t]["r2"]) for m, ts in valid_res.items()}
        out = {
            m: {"transform": t, "valid": valid_res[m][t], "test": run(m, t, train, test, cols)}
            for m, t in chosen.items()
        }
        TEST_OUT.write_text(json.dumps(out, indent=2))
        print(json.dumps(out, indent=2))

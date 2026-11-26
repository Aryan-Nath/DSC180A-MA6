"""Guard rails on the ingest contract and the trained model's behaviour."""
import pandas as pd
import pytest
from sklearn.metrics import r2_score

from src.config import (
    CONSUMED_COLS,
    FORBIDDEN,
    LAG_WARMUP,
    RAW,
    RAW_FEATURE_COLS,
    REDUNDANT_COLS,
    TARGET,
)
from src.features import build_features, feature_columns, reindex_to_calendar
from src.ingest import load_raw, verify_raw_hash
from src.train import MODELS, temporal_split


@pytest.fixture(scope="module")
def raw():
    return load_raw().sort_values("dteday").reset_index(drop=True)


@pytest.fixture(scope="module")
def feats(raw):
    return build_features(raw)


def test_calendar_is_complete_before_lagging(raw):
    """The reindexed frame must have no gaps, or the lags are wrong."""
    grid = reindex_to_calendar(raw)
    assert set(grid.dteday.diff().dropna().dt.days.unique()) == {1}


def test_only_expected_rows_are_dropped(raw, feats):
    """Rows may only vanish for the lag warm-up or downstream of a genuinely
    absent day -- never because an encoder produced a silent NaN.

    Accounting: the first LAG_WARMUP days have no complete history. Each
    absent calendar day m costs the LAG_WARMUP rows after it (cnt_lag_1 is
    NaN on m+1, cnt_roll_7 is NaN on m+1..m+7, cnt_lag_7 on m+7,
    cnt_roll_14 on m+1..m+14; their union is 14 rows). Day m itself was never in `raw`, so it is not a loss.
    The bound is exact for the current feature set; add a longer lag and
    LAG_WARMUP in src/config.py must grow with it.
    """
    full = pd.date_range(raw.dteday.min(), raw.dteday.max(), freq="D")
    missing_days = len(full) - len(raw)
    allowed_loss = LAG_WARMUP + LAG_WARMUP * missing_days
    lost = len(raw) - len(feats)
    assert lost <= allowed_loss, f"lost {lost} rows; expected at most {allowed_loss}"


def test_beats_the_mean_baseline(feats):
    """A model that cannot beat predicting the training mean is not a result."""
    cols = feature_columns(feats)
    train, _, test = temporal_split(feats)
    ridge = MODELS["ridge"]
    ridge.fit(train[cols], train[TARGET])
    assert r2_score(test[TARGET], ridge.predict(test[cols])) > 0.4


def test_persistence_baseline_is_reported():
    """The baseline that matters for a lag-driven model is 'yesterday again'.
    It must be in the comparison, whatever its score."""
    assert "baseline_persistence" in MODELS


def unclassified_raw_columns(path) -> set[str]:
    """Columns of the CSV at `path` that src/config.py does not classify."""
    classified = FORBIDDEN | RAW_FEATURE_COLS | CONSUMED_COLS | REDUNDANT_COLS | {"dteday"}
    return set(pd.read_csv(path, nrows=0).columns) - classified


def test_every_raw_column_is_classified():
    """A new column in the raw CSV (e.g. `cnt_next_day`) would flow straight
    into feature_columns() as a numeric feature. Force a decision first."""
    assert not unclassified_raw_columns(RAW), (
        f"unclassified raw columns: {sorted(unclassified_raw_columns(RAW))}; "
        "add each to FORBIDDEN or a feature class in src/config.py"
    )


def test_column_classification_check_can_fail(tmp_path):
    """Proves the check above is not vacuous: a copy of the CSV with an extra
    column must be flagged. The real raw file is never touched."""
    fake = tmp_path / "bike_daily.csv"
    df = pd.read_csv(RAW)
    df["cnt_next_day"] = df["cnt"].shift(-1)
    df.to_csv(fake, index=False)
    assert unclassified_raw_columns(fake) == {"cnt_next_day"}


def test_raw_file_is_unmodified():
    """data/raw/bike_daily.csv is immutable. Catches writes that bypass the
    Edit/Write permission and hook, e.g. a Bash `cp` (see docs/SEEDED_FAULTS.md)."""
    verify_raw_hash()


def test_hash_check_detects_a_modified_copy(tmp_path):
    """The hash check is not vacuous: a one-byte change must raise."""
    copy = tmp_path / "bike_daily.csv"
    copy.write_bytes(RAW.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="sha256"):
        verify_raw_hash(copy)

# Seeded faults

Four deliberate faults, each applied, run through `make test` and the
PostToolUse hook, then fixed. All output below was captured from real runs in
this repo (Python 3.13.1, pinned requirements); nothing is paraphrased except
where marked.

## Method and honest caveats

- **Who did what.** I (Claude Sonnet, running as a Claude Code subagent
  directed by Claude Opus) applied each fault and each fix. The student did
  not type these edits. "Turns to fix" therefore means: tool calls I needed
  after seeing the red output.
- **The hook was invoked directly, not by a live Claude Code session.** There
  is no local Ollama model here and the edits were made through a shell, so
  the `Edit|Write` matcher never fired by itself. I ran
  `.claude/hooks/check_leakage.sh` with `CLAUDE_PROJECT_DIR` set and a
  hand-built PostToolUse JSON on stdin, shaped like the one Claude Code sends
  for an `Edit` tool call (`tool_name`, `tool_input.file_path`,
  `tool_response`, ...). Exit code 2 plus stderr is what Claude Code feeds
  back to the agent. That the real harness delivers it is documented
  behaviour I did not observe here. Payload used (the project path contains
  spaces; the hook handles them):

```
{"session_id": "sim-0001", "transcript_path": "/dev/null", "cwd": "/Users/Aryan/Desktop/UCSD Coursework/Fall 2026/DSC 180A/bikeshare-open", "hook_event_name": "PostToolUse", "tool_name": "Edit", "tool_input": {"file_path": "/Users/Aryan/Desktop/UCSD Coursework/Fall 2026/DSC 180A/bikeshare-open/src/features.py", "old_string": "...", "new_string": "...", "replace_all": false}, "tool_response": {"filePath": "/Users/Aryan/Desktop/UCSD Coursework/Fall 2026/DSC 180A/bikeshare-open/src/features.py", "success": true}, "tool_use_id": "toolu_sim_0001"}
```

- The hook runs only `tests/test_leakage.py` (not the contract tests), so a
  fault caught only by `tests/test_contract.py` would not fire it.
- Each fault was committed in its broken state (`SEEDED FAULT ...` commits)
  and fixed in the next commit, so `git show` reproduces every diff.

## Exercise 1 reference: the RED run for the new feature

Before `cnt_roll_14` existed, `test_roll_14_is_mean_of_14_strictly_earlier_days`
failed for the right reason (column missing). Commit `Add failing test for
cnt_roll_14`. Last lines of `make test`:

```
            and self._info_axis._can_hold_identifiers_and_holds_name(name)
        ):
            return self[name]
>       return object.__getattribute__(self, name)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E       AttributeError: 'DataFrame' object has no attribute 'cnt_roll_14'. Did you mean: 'cnt_roll_7'?

.venv/lib/python3.13/site-packages/pandas/core/generic.py:6194: AttributeError
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_roll_14_is_mean_of_14_strictly_earlier_days
1 failed, 14 passed in 2.11s
make: *** [test] Error 1
```

## Fault a: a forbidden column appended in feature_columns

Commits: `SEEDED FAULT a` then `Fix fault a`

**Exact change**

```diff
diff --git a/src/features.py b/src/features.py
index b69d083..d43d5b5 100644
--- a/src/features.py
+++ b/src/features.py
@@ -83,7 +83,7 @@ def build_features(df: pd.DataFrame) -> pd.DataFrame:
 def feature_columns(df: pd.DataFrame) -> list[str]:
     """Numeric columns that are safe to feed the model."""
     numeric = df.select_dtypes(include="number").columns
-    return [c for c in numeric if c not in FORBIDDEN]
+    return [c for c in numeric if c not in FORBIDDEN] + ["casual", "registered"]
 
 
 if __name__ == "__main__":
```

**`make test` (red), last lines**

```
python -m pytest tests/ -q
.......F.........                                                        [100%]
=================================== FAILURES ===================================
__________________________ test_no_forbidden_features __________________________

feats =         dteday  instant  season  ...  cnt_lag_7   cnt_roll_7  cnt_roll_14
0   2011-01-17     17.0  WINTER  ...     132....142857  2814.714286
699 2012-12-31    731.0  WINTER  ...      920.0  1531.428571  2672.571429

[700 rows x 29 columns]

    def test_no_forbidden_features(feats):
        """Guards the gate, not the data: feature_columns() excludes FORBIDDEN by
        construction, so this cannot discover a *new* leaky column. What it
        catches is someone editing feature_columns() or FORBIDDEN -- which is
        exactly the fault the Step 7 hook demonstrates."""
        cols = set(feature_columns(feats))
>       assert not (cols & FORBIDDEN), f"forbidden columns in feature set: {cols & FORBIDDEN}"
E       AssertionError: forbidden columns in feature set: {'registered', 'casual'}
E       assert not ({'atemp', 'casual', 'cnt_lag_1', 'cnt_lag_7', 'cnt_roll_14', 'cnt_roll_7', ...} & {'casual', 'cnt', 'cnt_2d_bfr', 'days_since_2011', 'instant', 'registered', ...})

tests/test_leakage.py:31: AssertionError
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_no_forbidden_features - AssertionError: fo...
1 failed, 16 passed in 2.27s
make: *** [test] Error 1
```

**PostToolUse hook** (`.claude/hooks/check_leakage.sh`, fed the payload shown in the Method section; exit code 2)

stderr:

```
Leakage tests failed after editing /Users/Aryan/Desktop/UCSD Coursework/Fall 2026/DSC 180A/bikeshare-open/src/features.py:
feats =         dteday  instant  season  ...  cnt_lag_7   cnt_roll_7  cnt_roll_14
0   2011-01-17     17.0  WINTER  ...     132....142857  2814.714286
699 2012-12-31    731.0  WINTER  ...      920.0  1531.428571  2672.571429

[700 rows x 29 columns]

    def test_no_forbidden_features(feats):
        """Guards the gate, not the data: feature_columns() excludes FORBIDDEN by
        construction, so this cannot discover a *new* leaky column. What it
        catches is someone editing feature_columns() or FORBIDDEN -- which is
        exactly the fault the Step 7 hook demonstrates."""
        cols = set(feature_columns(feats))
>       assert not (cols & FORBIDDEN), f"forbidden columns in feature set: {cols & FORBIDDEN}"
E       AssertionError: forbidden columns in feature set: {'casual', 'registered'}
E       assert not ({'atemp', 'casual', 'cnt_lag_1', 'cnt_lag_7', 'cnt_roll_14', 'cnt_roll_7', ...} & {'casual', 'cnt', 'cnt_2d_bfr', 'days_since_2011', 'instant', 'registered', ...})

tests/test_leakage.py:31: AssertionError
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_no_forbidden_features - AssertionError: fo...
1 failed, 7 passed in 0.34s
```
**Result:** test went red (`test_no_forbidden_features`) and the hook fired with exit 2.

**Turns to fix:** 1 (one `git checkout HEAD~1 -- src/features.py`, then `make test` green: 17 passed). Applied by Claude Sonnet, not live-session Claude Code.


## Fault b: delete `.shift(1)` from `cnt_roll_7`

Commits: `SEEDED FAULT b` then `Fix fault b`

**Exact change**

```diff
diff --git a/src/features.py b/src/features.py
index b69d083..ccbe14d 100644
--- a/src/features.py
+++ b/src/features.py
@@ -73,7 +73,7 @@ def build_features(df: pd.DataFrame) -> pd.DataFrame:
     # If you add a longer lag, raise LAG_WARMUP in src/config.py.
     out["cnt_lag_1"] = out[TARGET].shift(1)
     out["cnt_lag_7"] = out[TARGET].shift(WEEK)
-    out["cnt_roll_7"] = out[TARGET].shift(1).rolling(WEEK).mean()
+    out["cnt_roll_7"] = out[TARGET].rolling(WEEK).mean()
     # Mean of the 14 calendar days strictly before today (shift, then roll).
     out["cnt_roll_14"] = out[TARGET].shift(1).rolling(LAG_WARMUP).mean()
 
```

**`make test` (red), last lines**

```
=================================== FAILURES ===================================
_______________________ test_rolling_mean_excludes_today _______________________

feats =         dteday  instant  season  ...  cnt_lag_7   cnt_roll_7  cnt_roll_14
0   2011-01-17     17.0  WINTER  ...     132....428571  2814.714286
699 2012-12-31    731.0  WINTER  ...      920.0  1789.857143  2672.571429

[700 rows x 29 columns]

    def test_rolling_mean_excludes_today(feats):
        """cnt_roll_7 must be the mean of the 7 calendar days *before* today."""
        by_date = feats.set_index("dteday")[TARGET]
        date = feats.dteday.iloc[200]
        window = [date - pd.Timedelta(days=k) for k in range(1, 8)]
        if all(d in by_date.index for d in window):
            expected = sum(by_date[d] for d in window) / 7
>           assert feats.set_index("dteday").cnt_roll_7[date] == pytest.approx(expected)
E           assert np.float64(4389.428571428572) == 4240.714285714285 ± 0.00424071
E             
E             comparison failed
E             Obtained: 4389.428571428572
E             Expected: 4240.714285714285 ± 0.00424071

tests/test_leakage.py:57: AssertionError
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_rolling_mean_excludes_today - assert np.fl...
1 failed, 16 passed in 1.53s
make: *** [test] Error 1
```

**PostToolUse hook** (`.claude/hooks/check_leakage.sh`, fed the payload shown in the Method section; exit code 2)

stderr:

```
Leakage tests failed after editing /Users/Aryan/Desktop/UCSD Coursework/Fall 2026/DSC 180A/bikeshare-open/src/features.py:
[700 rows x 29 columns]

    def test_rolling_mean_excludes_today(feats):
        """cnt_roll_7 must be the mean of the 7 calendar days *before* today."""
        by_date = feats.set_index("dteday")[TARGET]
        date = feats.dteday.iloc[200]
        window = [date - pd.Timedelta(days=k) for k in range(1, 8)]
        if all(d in by_date.index for d in window):
            expected = sum(by_date[d] for d in window) / 7
>           assert feats.set_index("dteday").cnt_roll_7[date] == pytest.approx(expected)
E           assert np.float64(4389.428571428572) == 4240.714285714285 ± 0.00424071
E             
E             comparison failed
E             Obtained: 4389.428571428572
E             Expected: 4240.714285714285 ± 0.00424071

tests/test_leakage.py:57: AssertionError
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_rolling_mean_excludes_today - assert np.fl...
1 failed, 7 passed in 0.46s
```
**Result:** red (`test_rolling_mean_excludes_today`), hook fired with exit 2.

**Turns to fix:** 1 (restored the line; 17 passed). Applied by Claude Sonnet.

**Weakness noticed:** that test wraps its assertion in `if all(d in by_date.index for d in window)`, so it silently checks nothing if the sampled row's window ever straddles the missing day. It happens to check a real window at row 200 today. The new `cnt_roll_14` test names a fixed date and has no such guard.


## Fault c: remove the raise from `encode_weather`

Commits: `SEEDED FAULT c`, `Add test_encode_weather_raises_on_unknown_label`, `Fix fault c`

**Exact change**

```diff
diff --git a/src/features.py b/src/features.py
index b69d083..63c270f 100644
--- a/src/features.py
+++ b/src/features.py
@@ -26,8 +26,6 @@ def encode_weather(series: pd.Series) -> pd.Series:
     """
     known = series.dropna()
     unknown = set(known.unique()) - set(WEATHER_ORDER)
-    if unknown:
-        raise ValueError(f"unmapped weather labels: {sorted(unknown)}")
     return series.map(WEATHER_ORDER).astype(float)
 
 
```

**`make test` with the fault applied: GREEN (a gap).** Last lines:

```
python -m pytest tests/ -q
.................                                                        [100%]
17 passed in 1.48s
```

**Hook stderr with the fault applied:** (empty), exit code 0. The hook was silent.

The real data contains only GOOD / MISTY / BAD, so no existing test ever
feeds the encoder an unseen label. The raise is dead code as far as the suite
is concerned, which is exactly the property that lets the 20 BAD-weather
days vanish in a different dataset.

**Gap closed:** added `test_encode_weather_raises_on_unknown_label` in
`tests/test_leakage.py` (synthetic `["GOOD","MISTY","SNOW"]` must raise
`ValueError`). Against the still-faulty encoder it is red:

```
_________________ test_encode_weather_raises_on_unknown_label __________________

    def test_encode_weather_raises_on_unknown_label():
        """Closes the gap found by seeded fault c: with the raise removed,
        .map() turned an unseen label into NaN and dropna() deleted the row
        silently, and no test noticed. Real data never has an unseen label, so
        only a synthetic input can exercise this path."""
>       with pytest.raises(ValueError, match="unmapped weather labels"):
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E       Failed: DID NOT RAISE ValueError

tests/test_leakage.py:80: Failed
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_encode_weather_raises_on_unknown_label - F...
1 failed, 17 passed in 1.37s
make: *** [test] Error 1
```

Hook stderr for the same state (exit code 2):

```
Leakage tests failed after editing /Users/Aryan/Desktop/UCSD Coursework/Fall 2026/DSC 180A/bikeshare-open/src/features.py:
......F..                                                                [100%]
=================================== FAILURES ===================================
_________________ test_encode_weather_raises_on_unknown_label __________________

    def test_encode_weather_raises_on_unknown_label():
        """Closes the gap found by seeded fault c: with the raise removed,
        .map() turned an unseen label into NaN and dropna() deleted the row
        silently, and no test noticed. Real data never has an unseen label, so
        only a synthetic input can exercise this path."""
>       with pytest.raises(ValueError, match="unmapped weather labels"):
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E       Failed: DID NOT RAISE ValueError

tests/test_leakage.py:80: Failed
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_encode_weather_raises_on_unknown_label - F...
1 failed, 8 passed in 0.31s
```

**Turns to fix:** 2 (write the missing test and see it red; then restore the
raise: 18 passed). Applied by Claude Sonnet.

## Fault d: a Bash `cp` into `data/raw/` that the Edit/Write hook cannot see

Setup (all through a throwaway shell script kept outside the repo): back up the raw
file to a temp path, build a modified copy in which 2012-10-29 (Hurricane
Sandy, 22 rides) becomes 2200 rides with `casual` adjusted so that
`casual + registered == cnt` still holds, `cp` that copy over
`data/raw/bike_daily.csv`, then run the hook, `make test`, `make data`,
and restore from the backup.

**Before any defence (starter code + my earlier commits):**

```
backup sha: a6bed1577f6e4de5
tampered row before: ['2012-10-29', np.int64(2), np.int64(20), np.int64(22)]
tampered row after:  ['2012-10-29', np.int64(2180), np.int64(20), np.int64(2200)]
raw sha after cp: d09143ff47f5a1f5
hook exit: 0  (stderr bytes:        0)
python -m pytest tests/ -q
..................                                                       [100%]
18 passed in 2.15s
--- make data:
python -m src.ingest
OK ingest: 728 rows, 2011-01-03 -> 2012-12-31
restored sha: a6bed1577f6e4de56dcfae6d8315985073cc0ad3446c8c99ed60c86a0b5ad9dc  data/raw/bike_daily.csv
```

- The hook exited 0 with empty stderr. Two independent reasons: Claude Code's
  matcher is `Edit|Write` so a `Bash` call never reaches it, and even if it
  did, the script exits 0 for any payload whose `file_path` is not under
  `src/` (a Bash payload has no `file_path`).
- `.claude/settings.json` denies `Write(./data/raw/**)` and
  `Edit(./data/raw/**)`, which do not cover a `cp` in a Bash call.
- `make test`: **18 passed**. The suite did not notice, and `make data`
  printed OK. The poisoned Sandy row would have flowed into the test-set metrics.
- A cruder tamper (changing only `cnt`, leaving `casual`/`registered`)
  was caught, but only by accident: `test_leakage_identity_holds` failed
  because the identity broke. Captured output of that first attempt:

```
backup sha: a6bed1577f6e4de5
tampered row before: ['2012-10-29', np.int64(22)]
raw sha after cp: 1b637d824b4388b5
hook exit: 0  (stderr bytes:        0)

tests/test_leakage.py:22: AssertionError
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_leakage_identity_holds - assert np.False_
1 failed, 17 passed in 1.71s
make: *** [test] Error 1
--- make data:
python -m src.ingest
OK ingest: 728 rows, 2011-01-03 -> 2012-12-31
restored sha: a6bed1577f6e4de56dcfae6d8315985073cc0ad3446c8c99ed60c86a0b5ad9dc  data/raw/bike_daily.csv
```

**Fix (extra-credit item):** `RAW_SHA256` in `src/config.py` plus
`verify_raw_hash()`, called first thing in `src.ingest.load_raw()`. `make
data`, `make features`, and every test that loads data now fail on any byte
change. Two tests: `test_raw_file_is_unmodified` and
`test_hash_check_detects_a_modified_copy` (a tmp copy with one extra byte must
raise). Same tamper after the fix:

```
backup sha: a6bed1577f6e4de5
tampered row before: ['2012-10-29', np.int64(2), np.int64(20), np.int64(22)]
tampered row after:  ['2012-10-29', np.int64(2180), np.int64(20), np.int64(2200)]
raw sha after cp: d09143ff47f5a1f5
hook exit: 0  (stderr bytes:        0)
ERROR tests/test_leakage.py::test_dates_are_sorted_and_unique - ValueError: /...
ERROR tests/test_split.py::test_splits_non_empty - ValueError: /Users/Aryan/D...
ERROR tests/test_split.py::test_splits_are_ordered_in_time - ValueError: /Use...
ERROR tests/test_split.py::test_no_overlapping_dates - ValueError: /Users/Ary...
1 failed, 5 passed, 14 errors in 1.34s
make: *** [test] Error 1
--- make data:
    )
ValueError: /Users/Aryan/Desktop/UCSD Coursework/Fall 2026/DSC 180A/bikeshare-open/data/raw/bike_daily.csv sha256 is d09143ff47f5a1f5..., expected a6bed1577f6e4de5...; the immutable raw file was modified. Restore it with `git checkout data/raw/bike_daily.csv`.
make: *** [data] Error 1
restored sha: a6bed1577f6e4de56dcfae6d8315985073cc0ad3446c8c99ed60c86a0b5ad9dc  data/raw/bike_daily.csv
 M src/config.py
 M src/ingest.py
 M tests/test_contract.py
```

The hook still exits 0 (it still cannot see Bash), but the failure now
surfaces in `make test` and `make data`, which the agent is instructed to
run before claiming anything works. The raw file was restored from the backup
after each run; the final sha256 printed above is
`a6bed1577f6e4de56dcfae6d8315985073cc0ad3446c8c99ed60c86a0b5ad9dc`, matching the
required prefix `a6bed1577f6e4de5`.

**Other things that would catch it** (not implemented here):
- A `PreToolUse` hook on `Bash` that inspects `tool_input.command` and exits 2
  for any command mentioning `data/raw`. This blocks before the write, which
  the PostToolUse hook cannot do. It is regex matching on shell text, so
  `cd data && cp x raw/..` style indirection can slip past.
- A `Stop` hook running `make test`, exit 2 on failure (check
  `stop_hook_active` to avoid looping), so the agent cannot finish with a
  poisoned file even if it did not run tests itself.
- Filesystem permissions: `chmod a-w data/raw/bike_daily.csv` (or `chflags
  uchg` on macOS). Stops `cp` itself, but any owner can undo it with one more command.

**Turns to fix:** 2 (reproduce, then implement the hash check and re-run).
Applied by Claude Sonnet.

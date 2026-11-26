# Bikeshare demand forecasting: open-weight agentic workflow

Everything below reproduces with `pip install -r requirements.txt && make all`.
"Before" is the starter pipeline (14 features,
`reports/metrics_before_feature.json`); "after" adds `cnt_roll_14` and is
`reports/metrics.json`. Split: train 2011, validation H1 2012, test H2 2012.

## Results

| model | feature set | valid R2 | valid MAE | test R2 | test MAE |
|---|---|---|---|---|---|
| baseline_mean | before | -0.9318 | 2002.2 | -2.1441 | 2847.7 |
| baseline_mean | after | -0.8583 | 1965.6 | -2.0333 | 2793.1 |
| baseline_persistence | before | 0.4507 | 900.6 | 0.5099 | 840.1 |
| baseline_persistence | after | 0.4507 | 900.6 | 0.5099 | 840.1 |
| ridge | before | 0.6475 | 832.9 | 0.5833 | 947.1 |
| ridge | after | 0.6919 | 763.2 | 0.6268 | 870.9 |
| hgb | before | 0.2185 | 1296.6 | -0.4975 | 1972.6 |
| hgb | after | 0.1643 | 1341.2 | -0.6534 | 2087.9 |

The mean baseline moves between "before" and "after" only because the 14-day
warm-up removes 14 more 2011 rows (train 348 -> 334 rows; validation 182 and
test 184 rows are unchanged), so its training mean changed. Persistence does
not depend on training data and is identical. The table was generated from
the two JSON files, not typed.

## Headline finding

A model handed `casual` and `registered` scores test R^2 = 1.000000
(`python -m src.leakage_demo`) because `casual + registered == cnt` exactly;
it has learned addition and forecasts nothing. With those columns, the other
forbidden columns, and the time indexes excluded, and with a date-based split,
the honest test R^2 is 0.627 for ridge, 0.510 for persistence ("yesterday
again"), -2.033 for the mean baseline, and -0.653 for gradient boosting. Ridge
beats persistence by 0.117 R^2 on test but loses on MAE (870.9 vs 840.1 rides
per day). Gradient boosting fails because ridership grew about 65% from 2011 to
2012 and trees cannot predict above the largest count they saw in training
(6043 rides): 39.0% of the 182 validation days already exceed it. The new
feature `cnt_roll_14` (mean of the 14 calendar days before d, shifted by one
before rolling) raised validation ridge R^2 from 0.6475 to 0.6919 (+0.044,
above the 0.01 noise bar) and cut validation MAE from 832.9 to 763.2, so it is
kept; it lowered validation hgb R^2 (0.2185 to 0.1643), which I treat as the
tree model's extrapolation problem, not a reason to drop it.

## Exercise 4: target transformation

Script: `scripts/exp4_transform.py` (not part of `make all`;
`reports/metrics.json` is the untransformed pipeline). I fit ridge and hgb on
train with four targets (identity, `log1p(cnt)`, `cnt / cnt_roll_7`, and
`cnt - cnt_lag_1`), inverted predictions to rides, and scored on validation:

| model | identity | log1p | ratio to roll_7 | diff from lag_1 |
|---|---|---|---|---|
| ridge valid R2 | 0.6919 | -0.1653 | 0.4966 | 0.6915 |
| hgb valid R2 | 0.1643 | 0.0789 | 0.7118 | 0.6161 |

(Validation MAE for hgb: identity 1341.2, log1p 1423.1, ratio 741.9, diff 823.5;
for ridge 763.2, 1345.0, 987.7, 763.0. Saved in `reports/exp4_valid.json`.)
Predicting the ratio to the trailing 7-day mean lifts hgb from 0.164 to 0.712,
above ridge on validation. `log1p` does not help: it compresses the scale but
the tree still cannot output a value above anything it was trained on.

I then picked the best transform per model on validation alone (ridge:
identity; hgb: ratio) and touched the test set once, with `--final`:
hgb-ratio test R^2 0.5962, MAE 879.4; ridge test R^2 0.6268, MAE 870.9
(`reports/exp4_test.json`). Persistence is 0.5099 and 840.1.

Is it defensible or does it just win the comparison? Partly defensible. For:
the failure is about the level of demand, not about the features, and
modelling demand as a multiple of recent demand is a plausible mechanism
(ridership scaled with users and fleet), so a tree that predicts a bounded
ratio can follow a level it never saw. Against: (1) I tried 4 targets x 2
models on 182 validation days and picked the maximum; the +0.020 R^2 margin
of hgb over ridge is within the range that selection alone can produce.
(2) The margin reversed on test: hgb-ratio is 0.031 R^2 below ridge. So the
validation ranking did not hold. (3) The ratio target works by multiplying a
persistence-like level back in, so hgb is partly rebuilding the thing it is
being compared to, and it still loses to persistence on test MAE (879.4 vs
840.1). My verdict: the transformation is a useful diagnosis and confirms
the extrapolation explanation, but it is not evidence that hgb "competes"; I
did not adopt it in the pipeline.

## Exercise 5: ridge vs persistence

On test, ridge beats persistence on R^2 (0.6268 vs 0.5099, +0.117) and loses
on MAE (870.9 vs 840.1, ridge 30.8 rides or 3.7% worse). On validation the
sign is the opposite on MAE: ridge 763.2 vs persistence 900.6, 15.3% better.
So ridge wins both metrics on one half-year and loses one of them on the
next, and the one it loses is the one that does not punish rare large misses.
That pattern suggests ridge makes fewer very large errors and more small ones,
but I did not examine per-day errors, so that is a hypothesis, not a result.
Whether to deploy depends on the cost of a miss. If a 1,500-ride miss on a day
the operator under-stocks costs much more than three 500-ride misses
(quadratic-like), the R^2 edge matters and ridge is worth it. If cost is
roughly linear in rides, the 30.8-ride MAE deficit says ridge is not better
than a model with no parameters, no retraining and no way to break. With one
184-day test window, a 0.117 R^2 gap and a 3.7% MAE gap in opposite
directions, I would not deploy ridge on this evidence: I would ship
persistence as the default, run ridge in shadow for a few months, and switch
only if it wins MAE on out-of-sample days too. (This is my draft judgement;
the student decides.)

## Attribution

**Model.** Implementation was done by Claude Sonnet (model `claude-sonnet-5-5`),
run as a Claude Code subagent that was directed by Claude Opus, not by the
local `qwen3.5:9b` open-weight model the assignment describes. Ollama is not
installed on the machine, `make model` was never run, and the `.claude/settings.json`
`bikeshare-coder` endpoint was never used. Consequences: the PostToolUse hook was
invoked by hand with a simulated payload, not by a live session, and
`agent/audit.py` was later run against `claude-sonnet-5-5` via the Anthropic API (git-ignored `.claude/settings.local.json` override, since Ollama was unavailable); see `docs/AUDIT.md`.

**Agent-generated files and functions** (all written by the model above):
- `tests/test_leakage.py`: `test_roll_14_is_mean_of_14_strictly_earlier_days`,
  `test_encode_weather_raises_on_unknown_label`.
- `tests/test_contract.py`: `unclassified_raw_columns`,
  `test_every_raw_column_is_classified`, `test_column_classification_check_can_fail`,
  `test_raw_file_is_unmodified`, `test_hash_check_detects_a_modified_copy`.
- `src/features.py`: the `cnt_roll_14` line and use of `WEEK`.
- `src/config.py`: `WEEK`, `LAG_WARMUP = 14`, `RAW_SHA256`, `RAW_FEATURE_COLS`,
  `CONSUMED_COLS`, `REDUNDANT_COLS`.
- `src/ingest.py`: `verify_raw_hash`, and its call in `load_raw`.
- `scripts/exp4_transform.py` and `reports/exp4_*.json`.
- `.claude/skills/seed-fault/SKILL.md`, `CLAUDE.md` edits, `docs/*.md`, this report.
- The starter files (pipeline, original tests, hook, `new-feature` skill,
  `agent/audit.py`) are course-provided and unmodified apart from the above.

**Decisions: DRAFT — student to review and confirm/own these decisions.**
These were made by the agent, not by the student:
- Feature choice `cnt_roll_14` (and "kept"), based on validation ridge R^2 +0.044.
- Treating hgb's validation drop as the extrapolation problem rather than
  evidence against the feature.
- Introducing `WEEK = 7` so `LAG_WARMUP` can mean "longest window".
- The five-way raw column classification in config (which columns count as
  consumed or redundant).
- Adding a sha256 check to `load_raw()` for fault d, rather than a PreToolUse
  hook or a Stop hook.
- The Exercise 4 candidate transforms, "best on validation" selection rule,
  and the verdict not to adopt it.
- The Exercise 5 recommendation (persistence as default, ridge in shadow).
- Wording of the 58-line `CLAUDE.md`.

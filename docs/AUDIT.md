# Audit

## 1. Teammate repo

> **Note: second audit of this repo.** We work in a group of three, so `lindbergryan04/DSC180A-MA6` is audited by two teammates; this is the second of those audits. It was done independently and does not rely on the other teammate's findings.

**Teammate repo URL:** https://github.com/lindbergryan04/DSC180A-MA6
**Commit audited:** `ecdae291abd35775e0b32156b784343a8d6463de` (HEAD of the default branch when cloned, 2026-11-25)

**How it was run.** The repo was cloned into a scratch directory outside this
repo and treated as untrusted data; none of its code, Makefile or hooks was
executed. From this repo's root (so `.claude/agents/leakage-auditor.md` and the
git-ignored `.claude/settings.local.json` applied) I ran headless Claude Code
(`claude-sonnet-5-5`) with the `leakage-auditor` subagent:

```
claude -p "Use the leakage-auditor subagent to audit the repository at <clone>/repo ..."   --add-dir <clone>/repo --allowedTools Read Grep Glob Agent --disallowedTools Bash Edit Write
```

The subagent definition lists `Bash`, which could execute the teammate's code,
so I limited the session to read-only tools. Consequence: the auditor reviewed by
reading only and could not run the tests or re-run the pipeline. I did not run
`agent/audit.py` on the teammate repo, because its allowed tools include Bash.

**`/leakage-auditor` output (verbatim, as returned by the headless session; the
first paragraph is the session's own framing around the subagent's report):**

```text
Here is the leakage-auditor's report. It is the subagent's output, and it ran on the repo at the scratchpad path. I haven't checked it myself.

**Scope.** The auditor read `src/config.py`, `features.py`, `train.py`, `ingest.py` and `leakage_demo.py`. It also read the three test files, the Makefile, `reports/metrics.json` and the raw CSV header. It did not run any code. The `scripts/` directory (`exp4_transform.py`) doesn't exist in that repo, so that experiment wasn't reviewed. Only the `change_from_yesterday` path in `train.py` (`--predict-change`) was visible.

Checks 1 to 3 and 5 pass. Check 4 has a cap on row loss, and it holds. One finding changes a conclusion (F1), and one is a latent risk (F2).

**F1. The kept feature fails the repo's own keep/drop rule (medium).**
- Location: `src/train.py:106-114`, with the numbers in `reports/metrics.json`.
- `cnt_prior_week_same_type` is in the headline feature set, and the headline rests on Ridge. Ridge's validation R² is 0.6459 with the feature and 0.6475 without it, a change of -0.0016. Test R² is also worse with the feature (0.5794 against 0.5833).
- CLAUDE.md says a validation gain under 0.01 means drop the feature.
- HGB gains +0.058 on validation. HGB scores -0.43 on test, so that gain doesn't justify keeping the feature.
- Fix: drop the feature from the headline set, or state in `docs/DECISIONS.md` that it is kept despite a null validation result. The auditor did not read `docs/DECISIONS.md` in full.

**F2. Lag windows are derived from `LAG_WARMUP` (low, latent).**
- Location: `src/features.py:75-82`, `src/config.py:63`.
- The 7-day windows use `LAG_WARMUP` directly. CLAUDE.md forbids this because a warm-up bump silently resizes the short windows.
- It produces no wrong number today, since `LAG_WARMUP` is 7. If someone raises it to 14, `cnt_lag_7`, `cnt_roll_7` and the same-type means become 14-day features while keeping the old names. `test_rolling_mean_excludes_today` hard-codes 7, so it would catch the roll but not the lag or same-type features.
- Fix: add `WEEK = 7` to `src/config.py` and use it for the short windows.
- CLAUDE.md also says `LAG_WARMUP` is 14 and the table has 700 rows. The code has 7 and 714 rows (348 train, 182 valid, 184 test). The auditor judged the CLAUDE.md gotcha stale, not the code.

**Checks that pass**
1. **Target leakage.** The 15 features in `metrics.json` contain no `casual`, `registered`, `cnt` or `cnt_2d_bfr`, and no arithmetic combination of them. `season`, `yr`, `mnth` and `weekday` are strings in the CSV, so `feature_columns` drops them as non-numeric. Every lag uses `.shift(1)` or `.shift(7)`. In `cnt_prior_week_same_type` the `.where(...)` mask is applied before `.shift(1)`, so it uses only past counts and today's workday flag, which is known in advance.
2. **Temporal ordering.** `temporal_split` splits by date. `StandardScaler` sits inside the pipeline and is cloned and fitted on train only. The mean baseline is fitted on train only.
3. **Calendar gaps.** `reindex_to_calendar` runs before any lag is built, and `test_lags_are_true_calendar_lags` checks it.
4. **Silent row loss.** `encode_weather` raises on unknown labels instead of mapping them to NaN. `test_only_expected_rows_are_dropped` caps the loss at 14 rows, and the actual loss is exactly 14 (728 down to 714). That cap lives in a test, not as an assertion in `build_features`.
5. **Baselines.** The mean and persistence baselines are in `MODELS` and appear in `metrics.json` for valid and test, including under `before_feature`. The `--predict-change` path also reports both. Ridge beats persistence on test (0.579 against 0.510), so the headline holds. HGB's negative R² is reported, not hidden.

Two small issues don't change any number. `tests/test_contract.py:46-52` fits the shared `MODELS["ridge"]` object without cloning it, and it scores on the test split. `src/leakage_demo.py` uses `casual` and `registered` on purpose as a demonstration.
```

**Verdict.**

Auditor's findings, as reported: no leakage, a correct time split and both
baselines present (checks 1 to 3 and 5 pass, check 4 bounded); F1 (medium): the
kept feature `cnt_prior_week_same_type` fails the 0.01 keep/drop rule for ridge
(valid R2 0.6475 to 0.6459); F2 (low, latent): the 7-day windows use
`LAG_WARMUP`; plus two small test-hygiene notes.

My judgement (I read `src/features.py`, `src/config.py`, `reports/metrics.json`,
`docs/DECISIONS.md` and `REPORT.md` of the teammate repo). F1's numbers are
correct (ridge valid 0.6459 vs 0.6475; test 0.5794 vs 0.5833; hgb valid +0.0584,
test -0.4272), but the finding is already answered: the teammate's
`docs/DECISIONS.md` (2026-11-18) and REPORT.md say the feature was kept because
boosting cleared 0.01 while ridge lost 0.0016, which is the justification the
auditor asked for; it did not read those files. Whether that is a good decision
is arguable (ridge, the headline model, did not benefit and boosting is
negative on test), but it changes no reported number. F2 is real:
`features.py:75-82` use `LAG_WARMUP` (7) as the window, so raising it would
silently resize the lag and same-type windows; today it is 7 and nothing is
wrong. The auditor's claim that "CLAUDE.md forbids this" and its remark that the
CLAUDE.md gotcha says 14 / 700 rows do not hold for the teammate repo: its
CLAUDE.md has no such rule (47 lines, no `WEEK`). The auditor ran from this repo's
directory and apparently read this repo's CLAUDE.md, so I could not reproduce
that part. The `test_contract.py` fit-without-clone note is minor test hygiene.
None of the findings changes a reported metric; I agree with F2 as hardening
and consider F1 already documented. This is one read-only model pass at no
stated confidence, not proof of correctness.

## 2. Batch audit of this repo (`agent/audit.py`)

Command: `python agent/audit.py . --out reports/audit.jsonl`
(run with `AUDIT_MODEL=claude-sonnet-5-5`; the script reads that variable and was not modified)

**Run with `claude-sonnet-5-5` via the Anthropic API, not the local Ollama model.**
Ollama is not installed, so `bikeshare-coder` does not exist. The user approved
sending this repo to Claude for this run. I redirected the SDK's Claude Code
binary with a git-ignored `.claude/settings.local.json` (model
`claude-sonnet-5-5`, `ANTHROPIC_BASE_URL=https://api.anthropic.com`, the
starter's dummy `ANTHROPIC_AUTH_TOKEN` blanked so the normal Claude login is
used). The committed `.claude/settings.json` and `~/.claude.json` are unchanged.
The "workspace not trusted" warning still printed (it only ignores the
`permissions.allow` entries) and did not block the run.

`reports/audit.jsonl` (verbatim, one line; this is the second run, made with
`.venv` activated):

```json
{"repo": "bikeshare-open", "leakage": "none", "temporal_ok": true, "baseline_reported": true, "reproducible": true, "findings": [{"file": "README.md", "line": 25, "issue": "README says `make test` runs 14 tests, but the suite has 20 and all 20 pass.", "why_it_matters": "This is a documentation mismatch only. It doesn't affect leakage, splits, baselines or reproducibility, but a stale count can hide a deleted test."}, {"file": "scripts/exp4_transform.py", "line": 75, "issue": "`--final` is documented as run-once, but nothing enforces it. A rerun overwrites reports/exp4_test.json, and I couldn't tell from the repo whether it has been run more than once.", "why_it_matters": "Repeated runs against test, or picking a transform after seeing test scores, would compromise the held-out set. Choosing the transform from validation results is correct."}], "confidence": "high"}
```

**History.** The first run (committed in a553765, since overwritten) used the
system Python 3.13, which has no pyarrow, and reported `reproducible: false`
because it could not run `make train`. That was an environment artifact:
`requirements.txt` pins `pyarrow==26.0.1`, installed in `.venv`. I re-ran inside
the venv; that is the file above.

**Verdict.**

Auditor's findings, as reported: leakage `none`, temporal_ok `true`,
baseline_reported `true`, reproducible `true`, confidence `high`. Two findings:
(1) `README.md:25` says `make test` runs 14 tests but the suite has 20;
(2) `scripts/exp4_transform.py:75`: `--final` is documented as run-once but
nothing enforces it.

My judgement: finding 1 is correct (I confirmed 20 tests pass) and is
documentation only; no reported number changes. I fix the README count in a
later commit. Finding 2 is accurate (the `--final` branch writes
`reports/exp4_test.json` unconditionally) but no number changes: the transform
is chosen from validation only, and `docs/DECISIONS.md` records that test was
touched once. A guard would be reasonable hardening, not done. The auditor
could not tell whether `--final` was run more than once; I cannot prove that
from the repo either beyond the DECISIONS entry. No leakage found, but this is
one model's single run, not proof.

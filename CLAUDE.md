# Bikeshare demand capstone

Daily Capital Bikeshare counts, 2011-2012. We forecast `cnt` (total daily
rides) from calendar, weather, and lagged-demand features.

## Commands
- `make data` - assert raw CSV shape AND its sha256 (`RAW_SHA256`)
- `make features` - build `data/processed/features.parquet`
- `make train` - fit models, write `reports/metrics.json`
- `make test` - pytest; run this before claiming anything works
- `make all` - headline reproduce command: three stages in order;
  `reports/metrics.json` must match a fresh run exactly.
- `python scripts/exp4_transform.py` - target-transform experiment, validation
  only. `--final` touches test; run it once, never again.

## Non-negotiable rules
- **Never** put `casual` or `registered` in a feature set:
  `casual + registered == cnt` exactly. `src/config.py` lists these and the
  other excluded columns (`cnt_2d_bfr`, raw time indexes) with the reason
  for each. Derive feature lists from `FORBIDDEN`; never hand-type them.
- **Never** split this data randomly. Use `src.train.temporal_split`.
  Train = 2011, valid = H1 2012, test = H2 2012. Never tune on test.
- Any new lag or rolling feature must be built on a gap-free calendar
  index (`src.features.reindex_to_calendar`) and must `.shift(1)` before
  it aggregates. Add a test for it in `tests/test_leakage.py`, red first.
  `LAG_WARMUP` is the LONGEST window; short windows use `WEEK`. Never
  derive a window from `LAG_WARMUP` or a bump will silently resize them.
- Report the mean baseline **and** the persistence baseline (yesterday's
  count) alongside every model. A negative R^2 is a finding, not a bug
  to hide.
- `data/raw/` is immutable and `load_raw()` checks its sha256. Never
  change that hash to make a test pass. A new raw column must first be
  classified in `src/config.py` (FORBIDDEN, RAW_FEATURE_COLS, CONSUMED_COLS
  or REDUNDANT_COLS), or `test_every_raw_column_is_classified` fails.
- the hook only runs `tests/test_leakage.py` on Edit/Write of `src/`.
  It never sees Bash writes, so run full `make test` yourself after changes.
- Validation gain under 0.01 R^2 is noise: drop the feature. Record every
  keep/drop as a dated line in `docs/DECISIONS.md` with a matching commit.

## Skills
- `/new-feature <name>` - add a feature, test first.
- `/seed-fault <description>` - break the code on purpose, see if the tests
  and hook catch it, fix it, log it in `docs/SEEDED_FAULTS.md`. If a test
  stays green under the fault, that is a gap: add a test.

## Style
- Standard library, pandas, scikit-learn only. No new dependencies
  without asking. Versions are pinned in `requirements.txt`.
- Paths and constants live in `src/config.py`. Nothing is hardcoded twice.

## Gotchas
- The mirror in `DATA_URL` is missing 2011-03-10. It is NOT the UCI file:
  728 rows from 2011-01-03, not 731 from 2011-01-01. With `LAG_WARMUP` 14
  the feature table has 700 rows.
- `weather` uses the labels `GOOD` / `MISTY` / `BAD`, not the UCI codes 1-4.
- Ridership grew ~65% from 2011 to 2012, so tree models trained on 2011
  cannot extrapolate to 2012. That is the headline result, not an error.
- 2012-10-29 (Hurricane Sandy, 22 rides) is in the test set; expect it in residuals.

# Audit

## 1. Teammate repo

**Teammate repo URL:** TODO: awaiting teammate repo URL

**`/leakage-auditor` output (verbatim):** TODO: awaiting teammate repo URL.
Nothing has been run against a teammate's repo and no output is pasted here.
Once there is a URL, clone it, open Claude Code in it with
`.claude/agents/leakage-auditor.md` available, run `/leakage-auditor`, and paste
the reply below without editing.

**Verdict:** TODO: awaiting teammate repo URL. Structure to fill in: first the
auditor's findings exactly as reported (file, line, scenario, fix); then, in a
separate paragraph headed "My judgement", which findings actually change a
reported number (re-run the teammate's pipeline with the fix and give the
before/after metric), which are style or do not change a number, and which of
the auditor's claims I could not reproduce.

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

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

`reports/audit.jsonl` (verbatim, one line):

```json
{"repo": "bikeshare-open", "leakage": "none", "temporal_ok": true, "baseline_reported": true, "reproducible": false, "findings": [{"file": "src/train.py", "line": 1, "issue": "I could not run `make train` end to end. The active Python (miniconda 3.13) has no pyarrow, which requirements.txt pins and the README's venv would install. Parquet reads failed, so I did not diff reports/metrics.json against a fresh run.", "why_it_matters": "The claim that metrics.json matches a fresh run is unverified here. Everything else I checked supports it: HGB has random_state=0, Ridge is deterministic, the pipeline is documented, and versions are pinned."}, {"file": "scripts/exp4_transform.py", "line": 80, "issue": "reports/exp4_test.json already exists, so `--final` has been run. The script has no guard to stop a second run, and the CLAUDE.md 'run it once' rule rests on convention alone.", "why_it_matters": "A re-run could turn test into a tuning set. The transform is chosen on validation only, so there is no leakage today."}], "confidence": "medium"}
```

**Verdict.**

Auditor's findings, as reported: leakage `none`, temporal_ok `true`,
baseline_reported `true`, reproducible `false`, confidence `medium`. Two findings:
(1) `src/train.py:1`: it could not run `make train` because its Python lacked
pyarrow, so it did not diff `reports/metrics.json` against a fresh run;
(2) `scripts/exp4_transform.py:80`: `--final` has no guard against a second run,
the "run it once" rule is convention only.

My judgement: `reproducible: false` is an artifact of the audit environment, not
a defect in the repo. The auditor used a system Python 3.13, while
`requirements.txt` pins `pyarrow==26.0.1`, which is installed in `.venv` (I
checked). I did not re-run the auditor inside the venv, so the "matches a fresh
run" claim is not independently confirmed by this audit. Finding 2 is accurate
(`TEST_OUT.write_text` runs unconditionally under `--final`) but changes no
reported number: the transform is chosen on validation only. A guard would be a
reasonable hardening, not done here. The auditor found no leakage; I take that
as consistent with the `check_identity`/test-suite checks but it is one model's
single run at medium confidence, not proof.

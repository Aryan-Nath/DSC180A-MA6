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

**Result: could not run. `reports/audit.jsonl` was NOT produced** (the script
writes the file only after all repos finish). TODO (not run: no local model).

What I observed, verbatim from the run (stderr of the process, which then
produced no further output and was killed by me after a 150 s limit; exit
status 142 is the shell's report of that SIGALRM):

```
Ignoring 5 permissions.allow entries from .claude/settings.json: this workspace has not been trusted. Run Claude Code interactively here once and accept the trust dialog, or set projects["/Users/Aryan/Desktop/UCSD Coursework/Fall 2026/DSC 180A/bikeshare-open"].hasTrustDialogAccepted: true in /Users/Aryan/.claude.json.
[claude-code:unrecognized_model] {"model":"bikeshare-coder","query_source":"sdk"}
```

Why: `ollama` is not installed on this machine (`ollama: command not found`),
nothing listens on `localhost:11434`, and `bikeshare-coder` was never built
(`make model` was deliberately not run: it downloads a ~7 GB model and needs
permission). `.claude/settings.json` sends the SDK's Claude Code binary to
that endpoint, so the audit has no model to talk to. I did not point it at a
hosted model, because that would send this repo to an external service
without the student's say-so, and I did not edit the student's
`~/.claude.json` to accept the workspace trust dialog.

To produce the real file, on a machine with Ollama: `make model`,
`make check-model`, run Claude Code once in this repo and accept the trust
prompt, then run the command above and commit `reports/audit.jsonl`
(and paste the relevant findings into section 1 style notes if useful).

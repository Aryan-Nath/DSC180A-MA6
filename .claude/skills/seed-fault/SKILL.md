---
name: seed-fault
description: Deliberately break the pipeline in one described way, check whether the test suite and the PostToolUse hook catch it, then fix it and log it. Use when someone asks to seed, inject, or stress-test a leakage or contract fault.
allowed-tools: Read, Edit, Bash(make*), Bash(python -m pytest*), Bash(git*), Bash(bash .claude/hooks/check_leakage.sh*)
---

# Seeding a fault: $ARGUMENTS

Never touch `data/raw/` with Edit or Write (denied). To test a raw-data
fault, change a copy outside the repo and restore with
`git checkout data/raw/bike_daily.csv`; confirm the sha256 still begins
`a6bed1577f6e4de5` before you finish.

1. **Start green.** Run `make test`. If it is not green, stop: the baseline
   is broken and a seeded fault would prove nothing.

2. **Apply exactly the change in $ARGUMENTS** to the smallest possible spot in
   `src/`. Show it with `git diff`; that diff is the "exact change" to record.
   Commit it alone as `SEEDED FAULT <letter> (deliberately broken): ...`.

3. **Run `make test` and keep the output.** Record the failing test names.
   - Red: good. The suite covers this fault.
   - Green: that is a **gap**. Say so plainly, write a new test that fails on
     this fault, show it red, and commit it separately before the fix.

4. **Fire the hook as Claude Code would**, with a PostToolUse payload on stdin:
   `echo '{"hook_event_name":"PostToolUse","tool_name":"Edit","tool_input":{"file_path":"'$PWD'/src/features.py"}}' | CLAUDE_PROJECT_DIR=$PWD bash .claude/hooks/check_leakage.sh; echo "exit=$?"`
   Record stderr and the exit code. Exit 2 with stderr is the working case.
   The hook only runs `tests/test_leakage.py`; if only `test_contract.py`
   caught the fault, say the hook missed it. State that you invoked the hook
   by hand if you did not trigger it through a live session.

5. **Fix it** (`git checkout <commit-before-fault> -- <file>` or a hand edit),
   run `make test` until green, and commit as `Fix fault <letter>: ...`.
   Count the tool calls the fix took ("turns to fix") and say who made them.

6. **Append the record to `docs/SEEDED_FAULTS.md`**: exact diff, red output,
   hook stderr and exit code, turns to fix. Paste real output only. If a step
   could not be run, write `TODO (not run: <reason>)`, never a guess.

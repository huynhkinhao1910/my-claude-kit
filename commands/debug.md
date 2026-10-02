---
description: Find the proven root cause of a bug with the debugging skill (reproduce → narrow → one hypothesis at a time → prove), stop and report, then fix through /quick
argument-hint: <symptom | error text | failing test | request_id>
---

Symptom: $ARGUMENTS

Follow the `debugging` skill:

1. **Reproduce.** Get the exact failing input and environment, and turn it into a failing test or a single command that fails. If it can't be reproduced, report what was tried and what differs between the environments, then **STOP**.
   - **UI bug** (wrong screen state, a button that does nothing, a broken flow): have `e2e-runner` (run mode) write one TC from the report and run it through a browser MCP on local/staging. Its failing step, network and console lines are the evidence.
   - **Slow** (page, endpoint or job): measure first with `debugging/references/slow-triage.md` and write down the time per bucket. If DB holds ≥ 50% of server time, run `database-reviewer` in `profile` mode for the baseline, plans and proposals. Other buckets go to their owner from the triage table. Do not tune a bucket that is not the bottleneck.
2. **Evidence.** Read the full error, the logs for the `request_id`, and the recent changes (`git log`, lockfile diffs). Use `git bisect run` when there is a known good commit.
3. **Narrow and test hypotheses** one at a time, with the stack tools from `debugging/references/stack-tools.md`. Revert exploratory edits between hypotheses. After 3 failed hypotheses, stop, widen the scope, and say so.
4. **STOP — report** in this format, and change no code yet:
   ```
   Symptom:     ...
   Evidence:    ...   (log lines, query plan, trace, failing test)
   Root cause:  ...   (one sentence; or "not proven yet" + the next experiment)
   Fix:         ...   (smallest change at the cause, not the symptom)
   Regression:  ...   (the test that fails before and passes after; for N+1 a query-count assertion, for UI the TC id)
   Measured:    ...   (slow cases only: bucket breakdown and the baseline numbers to beat)
   Same pattern elsewhere: file:line, ...
   ```
   Options: `fix` (runs `/quick` with this report) | `dig deeper` | `stop`.
5. **After the fix** (`/quick` step 3): for a slow case, rerun `database-reviewer` `profile` (or repeat the triage measurement) and show the before/after table. For a UI bug, rerun the same TC with `/ui-test <slug|url> TC-n`. Without a measured improvement or a passing TC, the bug is not fixed.

Rules: read-only diagnostics only. Clearing caches, retrying failed jobs, purging queues, killing queries or editing data are actions that need my yes. Leave no `dd()`, `dump()`, `console.log` or `fmt.Println` behind.

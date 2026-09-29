---
description: Find the proven root cause of a bug with the debugging skill (reproduce → narrow → one hypothesis at a time → prove), stop and report, then fix through /quick
argument-hint: <symptom | error text | failing test | request_id>
---

Symptom: $ARGUMENTS

Follow the `debugging` skill:

1. **Reproduce.** Get the exact failing input and environment, and turn it into a failing test or a single command that fails. If it can't be reproduced, report what was tried and what differs between the environments, then **STOP**.
2. **Evidence.** Read the full error, the logs for the `request_id`, and the recent changes (`git log`, lockfile diffs). Use `git bisect run` when there is a known good commit.
3. **Narrow and test hypotheses** one at a time, with the stack tools from `debugging/references/stack-tools.md`. Revert exploratory edits between hypotheses. After 3 failed hypotheses, stop, widen the scope, and say so.
4. **STOP — report** in this format, and change no code yet:
   ```
   Symptom:     ...
   Evidence:    ...   (log lines, query plan, trace, failing test)
   Root cause:  ...   (one sentence; or "not proven yet" + the next experiment)
   Fix:         ...   (smallest change at the cause, not the symptom)
   Regression:  ...   (the test that fails before and passes after)
   Same pattern elsewhere: file:line, ...
   ```
   Options: `fix` (runs `/quick` with this report) | `dig deeper` | `stop`.

Rules: read-only diagnostics only. Clearing caches, retrying failed jobs, purging queues, killing queries or editing data are actions that need my yes. Leave no `dd()`, `dump()`, `console.log` or `fmt.Println` behind.

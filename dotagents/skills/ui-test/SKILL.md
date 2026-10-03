---
name: "ui-test"
description: "Write UI test cases (from spec ACs or flows you describe), get them approved, then run them on a running app through claude-in-chrome and report PASS/FAIL/BLOCKED per case"
---

Input: <slug | URL> [TC-id] [--mutating]

Target: the user's request

1. **Resolve the target.**
   - A slug: take the base URL from `STATUS.md` or the project `CLAUDE.md`, or ask for it.
   - A URL with no slug: ask which flows to cover.
   - Confirm that the app is running and that the host is local, dev or staging. Any other host: **STOP** and ask.
2. **Write test cases.** Skip this step when `test-cases.md` already covers the UI-visible ACs, or when a `TC-id` is given. Otherwise delegate to `e2e-runner` in write mode, show the TCs, mark every `Mutates: yes`, and **STOP** for an OK. Mutating TCs run only with `--mutating` or an explicit yes now, and never against production.
3. **Run.** Delegate to `e2e-runner` in run mode (all TCs, or only `TC-id`), passing the environment, the base URL, the test account source and the approval for mutating TCs.
4. **Report.** Show the result table and the expected-vs-actual block for each FAIL. With a slug, the report is saved to `docs/features/<slug>/ui-test-report.md`, and `STATUS.md` is updated with the result line.
5. **STOP.** Options:
   - `fix TC-n`: hand the failing TC block to `implementer` (through `/quick` outside a feature), then rerun that TC.
   - `done`.

Rules: no test case counts as PASS without its UI, network and console checks. Test accounts and fixtures only. Never edit application code in this command.

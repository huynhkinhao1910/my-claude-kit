---
name: "ui-test"
description: "Run UI test cases (from spec ACs, test-cases.md, or flows you describe) on a running app through a browser MCP, report PASS/FAIL/BLOCKED per case with screenshots, then optionally codify passing cases into Playwright specs"
---

Input: <slug | URL> [TC-id] [--mutating] [--chrome]

Target: the user's request

1. **Resolve the target.**
   - A slug: test cases come from `docs/features/<slug>/spec.md` (UI-observable ACs/ECs), or else from `test-cases.md`. Ask for the base URL if it is not in `STATUS.md` or the project `CLAUDE.md`.
   - A URL with no slug: ask which flows to cover.
   - A `TC-id`: rerun only that case.
   - Confirm that the app is running and that the host is local, dev or staging. Any other host: **STOP** and ask.
2. **Test cases.** If `e2e-runner` has to draft or derive new TCs, show them and **STOP** for an OK before running. List every `Mutates: yes` TC. These run only with `--mutating` or an explicit yes now, and never against production.
3. **Run.** Delegate to `e2e-runner` in run mode, passing the environment, the test account source and the approval for mutating TCs. Use Playwright MCP by default; `--chrome` selects claude-in-chrome.
4. **Report.** Show the result table and the expected-vs-actual block for each FAIL. With a slug, the report is saved to `docs/features/<slug>/ui-test-report.md`, and `STATUS.md` is updated with the result line.
5. **STOP.** Options:
   - `fix TC-n`: hand the failing TC block to `implementer` (through `/quick` outside a feature), then rerun that TC.
   - `codify`: `e2e-runner` in codify mode writes Playwright specs for the PASS TCs.
   - `done`.

Rules: no test case counts as PASS without its UI, network and console checks. Test accounts and fixtures only. Never edit application code in this command.

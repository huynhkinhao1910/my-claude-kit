---
description: Fast path for a small fix or change — reproduce with a failing test, fix, verify, light review, one approval gate before commit. Escalates to /feature when the change is not small.
argument-hint: <what to fix or change | issue text>
---

Task: $ARGUMENTS

**0. Size check first.** Stop and propose `/feature <slug>` instead if ANY of these holds:
- more than ~3 production files or ~150 changed lines expected
- a new endpoint, table, migration, queue, or public contract change (response format, route, event payload)
- auth, payments, permissions or data deletion are touched
- the requirement is ambiguous enough that there is more than one reasonable behaviour

Otherwise restate the task in one line and continue. No spec and no plan files.

**1. Reproduce.** For a bug, `test-writer` writes the smallest failing test that shows it, and confirms that it fails for the right reason. If the cause is unclear, follow the `debugging` skill until you have a root cause. For a small change, write a failing test for the new behaviour. Pure refactors or config edits with no testable behaviour skip this step, and say so.

**2. Fix.** `implementer` makes the minimal change until the test passes, then runs the formatter on the changed files.

**3. Verify.** Run only what the change touches:

| Stack | Checks |
|---|---|
| Laravel | `vendor/bin/pint --test <files>` → `php artisan test --filter=<Test>` → the related test folder |
| NestJS / Node | `npx tsc --noEmit` → `npm run lint` (if present) → the related spec files |
| Vue / React | `npx tsc --noEmit` (if tsconfig) → related component tests |
| Go | `gofmt -l <pkgs>` → `go vet <pkgs>` → `go test -race <pkgs>` |

Red → back to step 2 (max 2 rounds, then **STOP** and report).

Coming from a `/debug` report with a `Measured:` line or a UI TC: also re-measure (`database-reviewer` `profile`, or the triage measurement), or rerun the TC (`e2e-runner`). Then show the before/after or the TC verdict. No improvement means red.

**4. Light review.** Run the one language reviewer for the changed files (the same routing as `/review`), plus `security-reviewer` only if input handling or auth changed. Don't write review.md: put the findings inline, with BLOCKER/MAJOR only.

**5. STOP — the only gate.** Show:
- the one-line summary, `git diff --stat`, the test that proves it, and the verify results
- the reviewer's BLOCKER/MAJOR rows (or "none")

Options: `commit` | `fix #n` | `escalate to /feature`.
On `commit`: `commit-message-writer` on the staged files, then commit on the current branch. Never push, and never commit to `main`/`master` directly (create `fix/<slug>` first).

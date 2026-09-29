# Agent Orchestration

Agents live in `~/.claude/agents/`. Every agent follows `AGENT_STANDARD.md`: reviewers, verifiers and explorers are read-only, and only `implementer` and the build resolvers write code.

## Kit Roster

| Phase | Agent | Writes code? |
|-------|-------|--------------|
| Spec | requirement-analyst | docs only |
| Explore | code-explorer | no |
| Plan | planner (feature plan), architect (cross-cutting decisions → ADR) | docs only |
| Implement | test-writer → implementer | yes |
| Fix build | build-error-resolver (PHP, TS, Vue, Python), go-build-resolver, react-build-resolver | yes |
| Review | laravel-reviewer, typescript-reviewer, vue-reviewer, react-reviewer, go-reviewer, python-reviewer, code-reviewer (fallback), security-reviewer, database-reviewer, scalability-reviewer, silent-failure-hunter | no |
| Verify | spec-verifier | no |
| E2E | e2e-runner | tests only |
| Ship | doc-writer, commit-message-writer | docs only |
| Maintenance | refactor-cleaner | yes |

## When to Reach for Which

1. New feature or non-trivial change: run `/feature` (spec → plan → implement → verify → review → ship).
2. Small fix or change (≤ ~3 files, no new contract, no auth/payments): run `/quick`, which has one approval gate before commit.
3. Cause unknown: run `/debug` first (the `debugging` skill), and fix only after the root cause is proven.
4. Bug fix: `test-writer` reproduces the bug with a failing test, then `implementer` makes it pass.
5. Code just changed: run `/code-review` (local changes, read-only), or `/review <slug>` inside the pipeline. Both route by file type: `*.php` to laravel-reviewer, `*.vue` to vue-reviewer, `*.tsx`/`*.jsx` to react-reviewer, `*.ts`/`*.js` to typescript-reviewer, and `*.go` to go-reviewer.
6. Build, type or lint failure: run `/build-fix`, which picks the matching resolver. Dead code cleanup: `/refactor-clean` (`refactor-cleaner`).
7. Stopping mid-task: `/save-session`, then `/resume-session` in the next session.
8. Changes touching auth, user input, uploads, payments, webhooks or secrets: add `security-reviewer`.
9. Migrations, raw SQL, or queries over large tables: add `database-reviewer`.
10. Queries, jobs, list/export endpoints, outbound HTTP clients or infra config: add `scalability-reviewer`, which judges behaviour at 10× load and on multiple nodes.

## Parallel Execution

Launch independent agents in one message so they run concurrently. `/review` already does this for its reviewers.

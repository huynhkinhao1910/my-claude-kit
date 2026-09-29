# Agent Orchestration

Agents live in `~/.claude/agents/`. Every agent follows `AGENT_STANDARD.md`: reviewers, verifiers and explorers are read-only, and only `implementer` and the build resolvers write code.

## Kit Roster

| Phase | Agent | Writes code? |
|-------|-------|--------------|
| Spec | requirement-analyst | docs only |
| Explore | code-explorer | no |
| Plan | planner | docs only |
| Implement | test-writer → implementer | yes |
| Fix build | build-error-resolver (PHP, TS, Vue, Python), go-build-resolver, react-build-resolver | yes |
| Review | laravel-reviewer, typescript-reviewer, vue-reviewer, react-reviewer, go-reviewer, python-reviewer, code-reviewer (fallback), security-reviewer, database-reviewer, silent-failure-hunter | no |
| Verify | spec-verifier | no |
| E2E | e2e-runner | tests only |
| Ship | doc-writer, commit-message-writer | docs only |

## When to Reach for Which

1. New feature or non-trivial change: run `/feature` (spec → plan → implement → verify → review → ship).
2. Bug fix: `test-writer` reproduces the bug with a failing test, then `implementer` makes it pass.
3. Code just changed: run `/review`. It routes by file type: `*.php` to laravel-reviewer, `*.vue` to vue-reviewer, `*.tsx`/`*.jsx` to react-reviewer, `*.ts`/`*.js` to typescript-reviewer, and `*.go` to go-reviewer.
4. Build, type or lint failure: use the matching build resolver.
5. Changes touching auth, user input, uploads, payments, webhooks or secrets: add `security-reviewer`.
6. Migrations, raw SQL, or queries over large tables: add `database-reviewer`.

## Parallel Execution

Launch independent agents in one message so they run concurrently. `/review` already does this for its reviewers.

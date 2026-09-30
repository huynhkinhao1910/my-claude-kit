---
name: "refactor-clean"
description: "Find and remove dead code, unused imports and dependencies with the refactor-cleaner agent, one safe batch at a time, tests green after every batch"
---

Input: "[path | package] (default: whole repo)"

Scope: the user's request

Precondition: the test suite is green on the current branch, and the branch is not `main`/`master`. If either fails, **STOP** and say so.

1. **Find candidates** (read-only), using what the project has:

| Stack | Tools |
|---|---|
| Laravel | `composer-unused` (if installed); grep for classes/methods with no references outside their own file; unused routes via `php artisan route:list` vs controllers |
| NestJS / Vue / React | `npx knip`, falling back to `npx ts-prune` and `npx depcheck` |
| Go | `deadcode ./...` or `staticcheck -checks U1000 ./...` |

2. **Classify**: **safe** (no references, not public API, not reflective or dynamic), **risky** (used via container strings, events, config, route names, reflection, templates or other repos), **keep**. Show the table, and **STOP** for approval of the safe batch.
3. **Remove the safe batch** with `refactor-cleaner`, one batch at a time: delete, then run tests and the formatter, then commit (`refactor: remove unused …`). Revert that batch if anything goes red.
4. Risky items are listed for me to decide. Never remove them automatically.
5. **Report**: removed files/symbols/dependencies, the line delta, the test result per batch, and the risky list.

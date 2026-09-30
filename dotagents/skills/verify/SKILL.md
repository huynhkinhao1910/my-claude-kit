---
name: "verify"
description: "Deterministic quality gate — detects the stack and runs format check, static analysis, tests, lint"
---

Input: [slug]

Detect stack from files at repo root and run, stopping at the first failing category:

| Marker | Checks |
|---|---|
| `artisan` + `composer.json` | `./vendor/bin/pint --test` → `./vendor/bin/phpstan analyse --memory-limit=1G` (if installed) → `php artisan test --parallel` |
| `package.json` | `npm run lint` (if script exists) → `npx tsc --noEmit` (if tsconfig) → `npm test -- --run` (if script exists) |
| `go.mod` | `gofmt -l .` (must be empty) → `go vet ./...` → `go test -race ./...` |
| `pyproject.toml` | `ruff check .` → `mypy --strict src` → `pytest -q` |

Output a table `Check | Result | Details` (trim output to the failing lines).
On failure: propose the fix and ask whether to delegate to `build-error-resolver` (static/lint) or `implementer` (tests). Never proceed to `/review` while red.

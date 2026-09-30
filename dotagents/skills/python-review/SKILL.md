---
name: "python-review"
description: "Python / FastAPI code review for typing, error handling, async correctness, FastAPI layering, SQLAlchemy usage and security. Invokes the python-reviewer agent (read-only)."
---

Input: "[base-branch]  (default: main)"

# Python Code Review

This command invokes the **python-reviewer** agent for Python-specific review of local changes. Nothing is edited.

## What This Command Does

1. **Identify Python Changes**: `git diff <base>...HEAD -- '*.py' pyproject.toml` (base = argument, default `main`) plus uncommitted `*.py` changes
2. **Run Static Analysis** (read-only): `ruff format --check`, `ruff check`, `mypy --strict src`
3. **Run Related Tests**: `pytest <related tests> -q`
4. **Review**: typing, errors, async, FastAPI layering and response contract, SQLAlchemy (N+1, transactions, row locks), security
5. **Generate Report**: `review-checklist` table, severity CRITICAL / HIGH / MEDIUM / LOW

## When to Use

- After writing or modifying Python / FastAPI code
- Before committing Python changes
- Reviewing a PR with `.py` files

Changes touching auth, user input, uploads, payments or secrets: also run **security-reviewer**. Migrations or queries on large tables: also run **database-reviewer**.

## Automated Checks Run

```bash
ruff format --check <files>
ruff check <files>
mypy --strict src
pytest <related tests> -q
uvx pip-audit        # when pyproject.toml / uv.lock changed
```

## Review Categories

### CRITICAL (Must Fix)
- SQL built with f-strings / `%`; `eval`, `pickle`, `yaml.load` or `shell=True` on untrusted input
- Endpoint without auth, or query not scoped by owner (IDOR)
- Pydantic input without `extra="forbid"` on models that map to DB rows (mass assignment)
- Hardcoded secrets; secrets or tokens in logs
- Money/stock update without a row lock inside the transaction

### HIGH (Should Fix)
- Blocking I/O (`requests`, `time.sleep`, sync driver) inside `async def`
- Outbound call without timeout; un-awaited coroutine; fire-and-forget `create_task`
- Bare `except` / `except Exception` that swallows; lost `from exc`
- ORM object returned from a router; error built in a router instead of the central handler
- `commit()` in a repository; lazy load in async code (N+1)
- Missing tests for 401 / 404 / 422 / business-error paths

### MEDIUM (Consider)
- Missing type hints on public API, `Any` leaks, `Optional` not narrowed
- Mutable default args, naive datetimes, float money
- Unbounded list endpoint (no `per_page` cap)

## Approval Criteria

| Status | Condition |
|--------|-----------|
| PASS: Approve | No CRITICAL or HIGH issues |
| WARNING: Warning | Only MEDIUM issues (merge with caution) |
| FAIL: Block | CRITICAL or HIGH issues found |

## Integration with Other Commands

- `/python-test` first to make sure tests pass
- `/build-fix` when `ruff` / `mypy` fail (build-error-resolver)
- `/code-review` for a mixed-language diff

## Related

- Agent: `agents/python-reviewer.md`
- Skills: `skills/python-patterns/`, `skills/fastapi-patterns/`, `skills/python-testing/`

---
description: Enforce TDD for Python / FastAPI. Write failing pytest tests first, implement the minimum to pass, refactor, and verify 80%+ coverage with pytest-cov.
argument-hint: "<what to build or the bug to reproduce>"
---

# Python TDD Command

This command enforces test-driven development for Python and FastAPI code using the `python-testing` skill.

## What This Command Does

1. **Define the surface**: function signature, or endpoint + request/response schema
2. **Write Tests** (RED): pytest, AAA, `parametrize` for input variants; endpoints through `httpx.AsyncClient`
3. **Run Tests**: confirm they fail for the right reason (not an import error or a typo)
4. **Implement** (GREEN): minimal code following `python-patterns` / `fastapi-patterns`
5. **Refactor**: tests stay green; `ruff format`, `ruff check`, `mypy --strict src`
6. **Check Coverage**: `uv run pytest --cov=src --cov-report=term-missing` ≥ 80%

## When to Use

- Implementing new Python functions, services or FastAPI endpoints
- Fixing a bug (reproduce it with a failing test first)
- Adding coverage to existing code

## TDD Cycle

```
RED      → Write a failing test
GREEN    → Implement minimal code to pass
REFACTOR → Improve code, tests stay green
REPEAT   → Next behavior
```

## Example Session

````
User: /python-test GET /api/v1/orders/{id} returns the caller's order only

Agent:
## Step 1: Tests (RED) — tests/integration/test_get_order.py

```python
async def test_returns_order_owned_by_caller(client, auth_as, make_order) -> None:
    auth_as(1)
    order = await make_order(user_id=1)

    resp = await client.get(f"/api/v1/orders/{order.id}")

    assert resp.status_code == 200
    assert resp.json()["data"]["id"] == order.id


async def test_returns_404_for_other_users_order(client, auth_as, make_order) -> None:
    auth_as(1)
    order = await make_order(user_id=2)

    resp = await client.get(f"/api/v1/orders/{order.id}")

    assert resp.status_code == 404
    assert resp.json()["meta"]["code"] == "not_found"


async def test_returns_401_without_token(client) -> None:
    resp = await client.get("/api/v1/orders/1")

    assert resp.status_code == 401
```

## Step 2: Run — FAIL (404 route not found for all three) ✓ right reason

## Step 3: Implement — repository `get_for_user`, service raises NotFoundError, router returns ok()

## Step 4: Run — 3 passed; coverage 91%
````

## Coverage Targets

| Code | Target |
|------|--------|
| Services, money/security paths | 90%+ |
| General code | 80%+ |
| Migrations, `main.py` wiring | Exclude |

## TDD Best Practices

**DO:**
- Write the test FIRST and watch it fail
- Use the real test database; fake only the network edge (`respx`, broker fake)
- Override dependencies with `app.dependency_overrides`
- Cover 401 / 403-or-404 / 422 / each business error per endpoint

**DON'T:**
- Mock your own services or repositories
- Use `time.sleep` / `asyncio.sleep` to wait for things
- Test private functions directly
- Ignore flaky tests

## Related Commands

- `/python-review` - Review code after implementation
- `/build-fix` - Fix `ruff` / `mypy` failures

## Related

- Skills: `skills/python-testing/`, `skills/tdd-workflow/`

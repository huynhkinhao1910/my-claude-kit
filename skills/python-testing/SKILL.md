---
name: python-testing
description: >-
  pytest testing for Python and FastAPI: TDD red-green-refactor, AAA tests, fixtures and conftest.py, parametrize,
  async tests with pytest-asyncio or anyio, httpx AsyncClient against the ASGI app, dependency_overrides, a real
  MySQL test database with per-test transaction rollback, respx for outbound HTTP, freezegun/time-machine, and
  pytest-cov at 80%+. Use when writing or fixing Python tests, reproducing a Python bug with a failing test, or
  when asked "viết test python", "test fail", "tăng coverage". Do NOT use for production code idioms
  (python-patterns), browser E2E (e2e-testing) or Django test runner specifics.
origin: My Claude Kit
---

# Python Testing

pytest only. Tests assert behavior through the public surface; mocks only at the process edge.

## When to Use

- Starting any Python task (tests come first: RED → GREEN → REFACTOR)
- Adding a regression test for a bug
- Testing a FastAPI endpoint, service, repository or worker
- Coverage below 80%

## How It Works

### 1. Dependencies and config

```bash
uv add --dev pytest pytest-asyncio pytest-cov httpx respx time-machine
```

```toml
[tool.pytest.ini_options]
addopts = "-q --strict-markers --cov=src --cov-report=term-missing --cov-fail-under=80"
testpaths = ["tests"]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "session"
filterwarnings = ["error"]
```

`filterwarnings = ["error"]` turns deprecation warnings into failures, so they get fixed when introduced.

### 2. Layout

```
tests/
├── conftest.py            # shared fixtures: settings, db, client
├── unit/                  # pure logic, no I/O, milliseconds
│   └── test_money.py
└── integration/           # real DB, ASGI app, fakes at the network edge
    └── test_orders_api.py
```

Name tests for behavior: `test_returns_404_when_order_belongs_to_other_user`, not `test_get_order_2`.

### 3. AAA and parametrize

```python
import pytest

from my_service.money import Money, CurrencyMismatchError


def test_add_sums_amounts_in_same_currency() -> None:
    # Arrange
    a, b = Money(1000, "VND"), Money(500, "VND")

    # Act
    total = a.add(b)

    # Assert
    assert total == Money(1500, "VND")


def test_add_rejects_different_currency() -> None:
    with pytest.raises(CurrencyMismatchError):
        Money(1, "VND").add(Money(1, "USD"))


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("  a@b.com ", "a@b.com"),
        ("A@B.COM", "a@b.com"),
    ],
    ids=["strips-space", "lowercases"],
)
def test_normalize_email(raw: str, expected: str) -> None:
    assert normalize_email(raw) == expected
```

- One behavior per test. Several `assert`s are fine when they describe one outcome.
- `pytest.raises(..., match="...")` to pin the message only when the message is the contract.
- Never `assert` on logs or private attributes when a return value or DB state can be checked.

### 4. Fixtures

- Put shared fixtures in `conftest.py`; keep single-use setup inside the test.
- Use `yield` fixtures for teardown. Scope: `function` by default, `session` only for expensive, read-only things (engine, app).
- Factories beat giant fixtures: a `make_order(**overrides)` fixture returns a builder.

```python
@pytest.fixture
def make_order(db_session: AsyncSession) -> Callable[..., Awaitable[Order]]:
    async def _make(**overrides: object) -> Order:
        order = Order(**{"user_id": 1, "status": "pending", "total_minor": 1000, **overrides})
        db_session.add(order)
        await db_session.flush()
        return order

    return _make
```

### 5. Database: real MySQL, rolled back per test

Never mock the ORM or repository in integration tests. Point `DATABASE_URL` at a dedicated test schema (`app_test`), migrate once per session, and wrap each test in a transaction that is rolled back.

```python
# tests/conftest.py
import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine

from my_service.config import get_settings


@pytest.fixture(scope="session")
async def engine() -> AsyncIterator[AsyncEngine]:
    settings = get_settings()
    assert settings.database_url.endswith("_test"), "refusing to run tests on a non-test database"
    eng = create_async_engine(settings.database_url)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)  # or run Alembic upgrade head
    yield eng
    await eng.dispose()


@pytest.fixture
async def db_session(engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    async with engine.connect() as conn:
        trans = await conn.begin()
        session = AsyncSession(bind=conn, join_transaction_mode="create_savepoint", expire_on_commit=False)
        try:
            yield session
        finally:
            await session.close()
            await trans.rollback()
```

`join_transaction_mode="create_savepoint"` lets code under test call `commit()` while the outer transaction still rolls everything back.

### 6. FastAPI endpoints

Drive the real app through `httpx.AsyncClient` + `ASGITransport`; swap dependencies with `app.dependency_overrides`, never by patching modules.

```python
@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncIterator[httpx.AsyncClient]:
    app.dependency_overrides[get_session] = lambda: db_session
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def auth_as(client: httpx.AsyncClient) -> Callable[[int], None]:
    def _auth(user_id: int) -> None:
        app.dependency_overrides[get_current_user] = lambda: CurrentUser(id=user_id)

    return _auth


async def test_create_order_returns_201_with_contract(client: httpx.AsyncClient, auth_as) -> None:
    auth_as(1)

    resp = await client.post("/api/v1/orders", json={"items": [{"sku": "A1", "quantity": 2}]})

    assert resp.status_code == 201
    body = resp.json()
    assert body["data"]["status"] == "pending"
    assert body["meta"]["message"] == "Order created"
    assert "request_id" in body["meta"]


async def test_create_order_returns_422_for_zero_quantity(client: httpx.AsyncClient, auth_as) -> None:
    auth_as(1)

    resp = await client.post("/api/v1/orders", json={"items": [{"sku": "A1", "quantity": 0}]})

    assert resp.status_code == 422
    assert resp.json()["meta"]["code"] == "validation_failed"
    assert "items.0.quantity" in resp.json()["meta"]["errors"]
```

For every endpoint, cover: happy path, 401 (no auth), 403/404 (other user's resource), 422 (invalid input), and each business error code. Assert the exact response contract (`api-design`).

### 7. Mocking: only the edge

| Thing | How |
|-------|-----|
| Outbound HTTP | `respx` (for httpx) — assert the request was made with the right payload |
| Time | `time_machine.travel("2026-01-01T00:00:00Z", tick=False)` |
| Randomness / IDs | inject a generator, or seed |
| Message broker publish | override the publisher dependency with an in-memory fake that records messages |
| Your own services / repositories | **don't** — use the real ones against the test DB |

```python
@respx.mock
async def test_charge_sends_amount_to_gateway() -> None:
    route = respx.post("https://pay.example.com/charges").respond(201, json={"id": "ch_1"})

    charge_id = await gateway.charge(order_id=7, amount_minor=1000)

    assert charge_id == "ch_1"
    assert json.loads(route.calls.last.request.content) == {"order_id": 7, "amount": 1000}
```

`unittest.mock.patch` is a last resort; when needed, use `autospec=True` so the mock breaks when the signature changes.

### 8. Running

```bash
uv run pytest                                   # full suite with coverage gate
uv run pytest tests/integration/test_orders_api.py::test_create_order_returns_201_with_contract -x
uv run pytest -k "order and not slow" -x --lf  # last failed first
uv run pytest --cov=src --cov-report=html       # open htmlcov/index.html
```

Flaky test? Reproduce with `uv run --with pytest-repeat pytest <test> --count=20` before touching it. Never "fix" flakiness with `sleep`.

## Examples

### Bug → failing test first

Report: "cancelling a paid order returns 200 and refunds twice".

```python
async def test_cancel_paid_order_twice_refunds_once(client, auth_as, make_order, fake_gateway) -> None:
    auth_as(1)
    order = await make_order(user_id=1, status="paid")

    first = await client.post(f"/api/v1/orders/{order.id}/cancel")
    second = await client.post(f"/api/v1/orders/{order.id}/cancel")

    assert first.status_code == 200
    assert second.status_code == 409
    assert second.json()["meta"]["code"] == "order_already_cancelled"
    assert len(fake_gateway.refunds) == 1
```

Run it, see it fail for the reported reason, then fix the code.

### Checklist before done

- [ ] Test was seen failing (RED) before the fix
- [ ] Integration tests hit the real test DB, not mocks of our own code
- [ ] Every endpoint has 401 / 403-or-404 / 422 / business-error cases
- [ ] No `sleep`, no network, no dependency on test order
- [ ] `uv run pytest` green with coverage ≥ 80%

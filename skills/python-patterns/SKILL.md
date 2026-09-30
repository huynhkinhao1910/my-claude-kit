---
name: python-patterns
description: >-
  House style for production Python 3.12+: uv + pyproject.toml, src/ layout, ruff (lint + format), mypy --strict,
  type hints on every public function, Protocol over ABC, frozen dataclasses and Pydantic models at boundaries,
  explicit error hierarchy, tz-aware UTC datetimes, pathlib, logging, asyncio with timeouts. Use when writing,
  refactoring or reviewing any .py file, pyproject.toml, a CLI, a worker or a library. Trigger on "viết Python",
  "viết hàm python", "tách module", "thêm type hint", "sửa script python". Do NOT use for FastAPI endpoints and
  wiring (use fastapi-patterns, which builds on this), tests (use python-testing) or notebooks/ML training code.
origin: My Claude Kit
---

# Python Patterns

Boring, typed, explicit Python. The toolchain enforces style so reviews argue about behavior, not whitespace.

## When to Use

- Writing or refactoring any `.py` file outside the FastAPI wiring layer
- Starting a new Python project or package
- Adding type hints, fixing `mypy`/`ruff` findings by hand
- Reviewing Python for idiom and correctness (`python-reviewer` preloads this skill)

## How It Works

### 1. Project layout and toolchain

```
my-service/
├── pyproject.toml
├── uv.lock
├── src/my_service/
│   ├── __init__.py
│   ├── config.py
│   ├── errors.py
│   └── orders/          # feature packages, not "models/", "utils/"
│       ├── __init__.py
│       ├── service.py
│       └── repository.py
└── tests/
```

- **uv** manages Python, venv and lockfile: `uv init --package`, `uv add httpx`, `uv add --dev pytest`, `uv run pytest`. Commit `uv.lock`.
- **`src/` layout**: tests run against the installed package, never against the working directory by accident.
- Organize by feature/domain. A `utils.py` that grows past one screen means a missing module.

```toml
[project]
name = "my-service"
requires-python = ">=3.12"

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "W", "I", "N", "UP", "B", "A", "C4", "SIM", "RUF", "S", "ASYNC", "PT", "DTZ", "TRY", "PL"]
ignore = ["PLR0913"]

[tool.ruff.lint.per-file-ignores]
"tests/**" = ["S101", "PLR2004"]

[tool.mypy]
strict = true
plugins = ["pydantic.mypy"]

[tool.pytest.ini_options]
addopts = "-q --strict-markers"
testpaths = ["tests"]
```

Check loop, in order: `ruff format .` → `ruff check --fix .` → `mypy src` → `pytest`.

### 2. Typing

- Every public function, method and module-level constant has type hints. Private helpers too when non-obvious.
- Use builtin generics and `|`: `list[str]`, `dict[str, int]`, `User | None`. Never `typing.List`, `Optional`.
- Accept the widest useful type, return the narrowest: take `Iterable[int]` / `Mapping[str, str]`, return `list[int]` / `dict[str, str]`.
- `Any` is a leak. Use `object` for "anything", a `TypeVar`/PEP 695 generic for "same type in and out", `TypedDict` for dict-shaped JSON you do not own.
- Narrow `X | None` before use (`if user is None: raise ...`). No `# type: ignore` without an error code and a reason.
- `Final` for constants, `Literal` for closed string sets, `enum.StrEnum` when the set has behavior.

```python
from collections.abc import Iterable
from typing import Final, Literal

MAX_BATCH: Final = 500
Status = Literal["pending", "paid", "cancelled"]


def chunk[T](items: Iterable[T], size: int = MAX_BATCH) -> list[list[T]]:
    """Split items into lists of at most `size` elements."""
    batch: list[T] = []
    out: list[list[T]] = []
    for item in items:
        batch.append(item)
        if len(batch) == size:
            out.append(batch)
            batch = []
    if batch:
        out.append(batch)
    return out
```

### 3. Interfaces: Protocol over ABC

Define the interface where it is consumed. Implementations do not inherit from it.

```python
from typing import Protocol


class PaymentGateway(Protocol):
    async def charge(self, order_id: int, amount_minor: int) -> str: ...


class OrderService:
    def __init__(self, gateway: PaymentGateway) -> None:
        self._gateway = gateway
```

One implementation and no test double? Skip the Protocol and depend on the concrete class.

### 4. Data: immutable by default

| Need | Use |
|------|-----|
| Internal value object | `@dataclass(frozen=True, slots=True)` |
| Data crossing a trust boundary (HTTP, queue, file, env) | Pydantic `BaseModel` (validates) |
| DB row | SQLAlchemy model (see `fastapi-patterns`) |
| Dict-shaped JSON from a library | `TypedDict` |

```python
from dataclasses import dataclass, replace


@dataclass(frozen=True, slots=True)
class Money:
    amount_minor: int
    currency: str

    def add(self, other: "Money") -> "Money":
        if other.currency != self.currency:
            raise CurrencyMismatchError(self.currency, other.currency)
        return replace(self, amount_minor=self.amount_minor + other.amount_minor)
```

- Money is `int` minor units or `Decimal`, never `float`.
- No mutable default arguments: `def f(tags: list[str] | None = None)`, or `field(default_factory=list)`.
- No module-level mutable state shared across requests or tasks.

### 5. Errors

One base exception per package, specific subclasses carrying context. Callers catch the specific ones.

```python
class AppError(Exception):
    """Base class for expected, domain-level failures."""

    code: str = "app_error"


class NotFoundError(AppError):
    code = "not_found"

    def __init__(self, resource: str, key: object) -> None:
        super().__init__(f"{resource} {key!r} not found")
        self.resource = resource
        self.key = key


class OrderAlreadyPaidError(AppError):
    code = "order_already_paid"
```

Rules:
- Never bare `except:`. `except Exception` only at a process boundary (request handler, job runner, `main`), and it must log with `logger.exception(...)` and re-raise or map to a response.
- Chain on translate: `raise StorageError("upload failed") from exc`. Never lose the original traceback.
- Do not return `None` to signal failure. Raise, or return an explicit result type.
- `try` blocks wrap only the line that can fail; put the happy path in `else`.
- Clean up with `with` / `async with` / `contextlib.ExitStack`, not `try/finally` by hand.

### 6. Configuration and secrets

Read env once at startup into a typed, validated object. Missing secret = crash at boot, not at first use.

```python
from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: SecretStr
    http_timeout_seconds: float = 5.0


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]  # values come from env
```

### 7. Dates, paths, strings

- `datetime.now(UTC)`; never `datetime.utcnow()` or naive datetimes. Store UTC, convert at the edge. (`ruff` rule `DTZ` enforces this.)
- `pathlib.Path` over `os.path`; `path.read_text(encoding="utf-8")` always names the encoding.
- f-strings for text, but `logger.info("paid order_id=%s", order_id)` for logs (lazy formatting, structured).

### 8. Logging

```python
import logging

logger = logging.getLogger(__name__)
```

- One `logging.getLogger(__name__)` per module. Configure handlers once in the entrypoint, never in library code.
- `print` is for CLIs' user output only.
- Never log secrets, tokens, full request bodies or PII. `SecretStr` keeps them out of `repr`.

### 9. Async

- Only use `async def` when the function awaits I/O. CPU work stays sync; offload with `asyncio.to_thread` or a process pool.
- No blocking calls inside `async def`: `requests`, `time.sleep`, sync DB drivers, `open()` on large files. Use `httpx.AsyncClient`, `asyncio.sleep`, async drivers, `anyio.Path` / `to_thread`.
- Every outbound call has a timeout: `httpx.AsyncClient(timeout=settings.http_timeout_seconds)`, `asyncio.timeout(5)`.
- Concurrency with `asyncio.TaskGroup` (structured, cancels siblings on error), not bare `create_task` that nobody awaits.
- Bound fan-out with `asyncio.Semaphore`; never `gather` 10k coroutines at once.

```python
async def fetch_all(client: httpx.AsyncClient, urls: list[str], limit: int = 10) -> list[bytes]:
    sem = asyncio.Semaphore(limit)

    async def one(url: str) -> bytes:
        async with sem:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.content

    async with asyncio.TaskGroup() as tg:
        tasks = [tg.create_task(one(u)) for u in urls]
    return [t.result() for t in tasks]
```

### 10. Functions and modules

- Functions < 50 lines, early returns over nesting, keyword-only args (`*,`) once there are more than 3 parameters or any boolean flag.
- Comprehensions for simple transforms; a loop once it needs a condition and a side effect.
- Import order is `ruff`'s job (`I`). No wildcard imports. No imports inside functions except to break a real cycle.
- Google-style docstrings on public API. Comments explain *why*, never *what*.

### 11. Security basics

- `subprocess.run([...], check=True)` with a list; never `shell=True` with any external input.
- Never `eval`, `exec`, `pickle.loads`, `yaml.load` (use `yaml.safe_load`) on untrusted data.
- SQL only through bound parameters (SQLAlchemy `text("... :id")` with params, or the ORM).
- `secrets` for tokens, `hmac.compare_digest` for comparing them.
- Scan dependencies: `uv run pip-audit` (or `uvx pip-audit`); `ruff` rule set `S` (bandit) catches the rest.

## Examples

### Refactor: mutable default + swallowed error

```python
# Before
def load(path, cache={}):
    try:
        return json.load(open(path))
    except Exception:
        return None
```

```python
# After
def load_config(path: Path) -> dict[str, object]:
    """Load a JSON config file.

    Raises:
        ConfigError: if the file is missing or not valid JSON.
    """
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ConfigError(f"config not found: {path}") from exc
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ConfigError(f"invalid JSON in {path}: {exc.msg}") from exc
    if not isinstance(data, dict):
        raise ConfigError(f"{path}: top level must be an object")
    return data
```

### Checklist before done

- [ ] `ruff format --check . && ruff check . && mypy src` are clean
- [ ] No `Any`, no untyped public function, no bare `except`
- [ ] No naive datetime, no float money, no mutable default
- [ ] Every outbound I/O has a timeout
- [ ] Tests written first (`python-testing`)

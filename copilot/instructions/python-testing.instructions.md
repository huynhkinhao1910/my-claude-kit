---
applyTo: "**/*.py,**/*.pyi,**/pyproject.toml"
---

# Python Testing

> This file extends [common/testing.md](../common/testing.md) with Python specific content.

## Framework

Use **pytest** with fixtures and `parametrize`; `asyncio_mode = "auto"` for async code.
FastAPI endpoints are tested through `httpx.AsyncClient` + `ASGITransport` with `app.dependency_overrides`.

## Database

Integration tests use a real MySQL test schema with per-test transaction rollback. Never mock your own repositories.

## Coverage

```bash
uv run pytest --cov=src --cov-report=term-missing --cov-fail-under=80
```

## Reference

See skill: `python-testing` for fixtures, DB isolation, endpoint and mocking patterns.

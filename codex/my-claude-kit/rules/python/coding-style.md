---
paths:
  - "**/*.py"
  - "**/*.pyi"
  - "**/pyproject.toml"
---
# Python Coding Style

> This file extends [common/coding-style.md](../common/coding-style.md) with Python specific content.

## Tooling

- **ruff format** + **ruff check** are mandatory — no style debates
- **mypy --strict** on `src/`; no untyped public function, no `Any` leaks
- **uv** for dependencies; commit `uv.lock`; `src/` layout

## Typing

- Builtin generics and `|`: `list[str]`, `User | None` (not `List`, `Optional`)
- `Protocol` over ABC, defined where it is consumed
- `@dataclass(frozen=True, slots=True)` for internal values; Pydantic models at trust boundaries

## Error Handling

Raise specific exceptions and chain the cause:

```python
try:
    raw = path.read_text(encoding="utf-8")
except FileNotFoundError as exc:
    raise ConfigError(f"config not found: {path}") from exc
```

Never bare `except:`; `except Exception` only at a process boundary, with `logger.exception(...)`.

## Reference

See skill: `python-patterns` for comprehensive Python idioms; `fastapi-patterns` for FastAPI layering.

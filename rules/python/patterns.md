---
paths:
  - "**/*.py"
  - "**/*.pyi"
  - "**/pyproject.toml"
---
# Python Patterns

> This file extends [common/patterns.md](../common/patterns.md) with Python specific content.

## Dependency Injection

Pass collaborators into the constructor; depend on a `Protocol` only when there are two implementations (real + fake):

```python
class OrderService:
    def __init__(self, repo: OrderRepository, events: OrderEvents) -> None:
        self._repo = repo
        self._events = events
```

## Layers (FastAPI)

Pydantic schema → router (HTTP only) → service (rules, commit) → repository (every query) → SQLAlchemy model.
Services raise `AppError` subclasses; one exception handler renders the `api-design` contract.

## Config

Read env once into a `pydantic-settings` `Settings` object; missing secrets fail at startup.

## Reference

See skills: `python-patterns`, `fastapi-patterns`.

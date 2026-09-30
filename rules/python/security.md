---
paths:
  - "**/*.py"
  - "**/*.pyi"
  - "**/pyproject.toml"
---
# Python Security

> This file extends [common/security.md](../common/security.md) with Python specific content.

## Secret Management

```python
class Settings(BaseSettings):
    jwt_secret: SecretStr  # required: app refuses to start without it
```

## Never on Untrusted Input

- `eval`, `exec`, `pickle.loads`, `yaml.load` (use `yaml.safe_load`)
- `subprocess` with `shell=True`; pass an argument list instead
- SQL built with f-strings or `%`; use bound parameters / the ORM

## Validation

- Pydantic input models with `extra="forbid"`, max lengths and numeric bounds
- Scope queries by owner (`where(Order.user_id == user.id)`) to prevent IDOR

## Security Scanning

```bash
ruff check --select S .      # bandit rules
uvx pip-audit                # vulnerable dependencies
```

## Timeouts

Every outbound call has a timeout: `httpx.AsyncClient(timeout=5.0)`, `asyncio.timeout(...)`.

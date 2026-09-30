---
name: fastapi-patterns
description: >-
  House style for FastAPI REST APIs (SPA/mobile clients): Pydantic v2 schemas -> router -> service -> repository ->
  SQLAlchemy 2.0 async model on MySQL, Depends for session/auth/services, responses per the api-design contract (the
  project's existing format, or data/paging/meta for a new project), central exception handlers, request_id
  middleware, /api/v1 routers, lifespan-managed engine and clients, Alembic migrations, RabbitMQ (aio-pika) workers and
  Redis cache. Use when writing or refactoring FastAPI routers, endpoints, schemas, dependencies, services,
  repositories, SQLAlchemy models, Alembic migrations or workers. Trigger on "tạo endpoint FastAPI", "viết API
  python", "thêm router", "thêm schema", "sửa model SQLAlchemy". Do NOT use for Django/Flask, plain Python libraries
  (python-patterns) or tests (python-testing).
origin: My Claude Kit
---

# FastAPI Patterns

Thin routers, fat services, repositories own every query. Same layering as the Laravel house style, in Python.

```
Request → Pydantic schema (validation) → router (HTTP only) → service (rules, transaction) → repository (queries) → SQLAlchemy model
                                                                ↘ raises AppError → central handler → contract error
```

Builds on `python-patterns` (typing, errors, async) and `api-design` (response contract). Read those first when new to the codebase.

## When to Use

- Adding or changing an endpoint, schema, dependency, service, repository or model
- Starting a new FastAPI service
- Adding a background job, cache or outbound integration to a FastAPI app

## How It Works

### Step 0 — Existing project? Follow it

Before writing code, read `app/main.py` (or `src/<pkg>/main.py`), one existing router + its service/repository + its test, and the response helper. Reuse what exists: its layout, its response helper, its session dependency. Only a new project gets the defaults below.

### 1. Layout (feature packages)

```
src/app/
├── main.py              # create_app(), lifespan, handlers, middleware
├── config.py            # Settings (pydantic-settings)
├── db.py                # engine, session factory, get_session, Base
├── errors.py            # AppError hierarchy
├── responses.py         # ok(), paged() envelope helpers
├── deps.py              # get_current_user, shared Annotated deps
└── orders/
    ├── router.py        # APIRouter, HTTP only
    ├── schemas.py       # Pydantic request/response models
    ├── service.py       # business rules, transactions
    ├── repository.py    # SQLAlchemy queries
    └── models.py        # SQLAlchemy ORM models
migrations/              # Alembic
tests/
```

### 2. App factory and lifespan

Create engine, HTTP clients and broker connections once in `lifespan`, close them on shutdown. Never at import time.

```python
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from app.config import get_settings
from app.db import engine
from app.errors import register_exception_handlers
from app.middleware import RequestIdMiddleware
from app.orders.router import router as orders_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    async with httpx.AsyncClient(timeout=settings.http_timeout_seconds) as http:
        app.state.http = http
        yield
    await engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(title="Orders API", lifespan=lifespan)
    app.add_middleware(RequestIdMiddleware)
    register_exception_handlers(app)
    app.include_router(orders_router, prefix="/api/v1")
    return app


app = create_app()
```

### 3. Database: SQLAlchemy 2.0 async on MySQL

```python
# app/db.py
from collections.abc import AsyncIterator
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.config import get_settings

engine = create_async_engine(
    get_settings().database_url,  # mysql+asyncmy://user:pass@host/db?charset=utf8mb4
    pool_size=10,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=1800,
)
SessionFactory = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionFactory() as session:
        yield session
```

```python
# app/orders/models.py
class Order(TimestampMixin, Base):
    __tablename__ = "orders"
    __table_args__ = (Index("ix_orders_user_id_created_at", "user_id", "created_at"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    total_minor: Mapped[int] = mapped_column(BigInteger)
    items: Mapped[list["OrderItem"]] = relationship(back_populates="order", lazy="raise")
```

- `lazy="raise"` on relationships: async sessions cannot lazy-load, so load explicitly with `selectinload` in the repository. N+1 becomes an error, not a slow page.
- Schema changes only through Alembic: `alembic revision --autogenerate -m "add orders"`, then **read and edit** the generated file. See `database-migrations` for large-table safety.
- Use a sync driver never in async code. MySQL async driver: `asyncmy` or `aiomysql`.

### 4. Schemas (Pydantic v2)

Separate input and output models. Never return ORM objects or accept them as input.

```python
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


class OrderItemIn(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    sku: Annotated[str, Field(min_length=1, max_length=64)]
    quantity: Annotated[int, Field(ge=1, le=1000)]


class OrderCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: Annotated[list[OrderItemIn], Field(min_length=1, max_length=100)]


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    total_minor: int
    created_at: datetime
```

- `extra="forbid"` on inputs blocks mass assignment (`user_id`, `status`, `is_admin` smuggled in the body).
- Every string and list input has a max length; every number has bounds.
- Output models whitelist fields. Adding a column never leaks it.

### 5. Responses (api-design contract)

```python
# app/responses.py
from typing import Any

from starlette.requests import Request


def ok(request: Request, data: Any, message: str = "OK") -> dict[str, Any]:
    return {"data": data, "meta": {"message": message, "request_id": request.state.request_id}}


def paged(request: Request, items: list[Any], *, page: int, per_page: int, total: int) -> dict[str, Any]:
    return {
        "data": items,
        "paging": {
            "current_page": page,
            "per_page": per_page,
            "total": total,
            "last_page": max(1, -(-total // per_page)),
        },
        "meta": {"message": "OK", "request_id": request.state.request_id},
    }
```

For the typed OpenAPI schema, declare generic envelope models (`Envelope[OrderOut]`, `Paged[OrderOut]`) and set `response_model=`. Keep one helper; never build the envelope inline in routers.

### 6. Errors: one handler, one shape

Services raise `AppError` subclasses (`python-patterns` §5) with `status_code` and `code`. Handlers translate them; routers never build error responses.

```python
# app/errors.py
class AppError(Exception):
    status_code = 400
    code = "bad_request"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotFoundError(AppError):
    status_code, code = 404, "not_found"


class ConflictError(AppError):
    status_code = 409

    def __init__(self, message: str, code: str) -> None:
        super().__init__(message)
        self.code = code


def _error(request: Request, status: int, message: str, code: str, errors: dict[str, list[str]] | None = None) -> JSONResponse:
    meta: dict[str, object] = {"message": message, "code": code, "request_id": request.state.request_id}
    if errors is not None:
        meta["errors"] = errors
    return JSONResponse({"data": None, "meta": meta}, status_code=status)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error(request: Request, exc: AppError) -> JSONResponse:
        return _error(request, exc.status_code, exc.message, exc.code)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        errors: dict[str, list[str]] = {}
        for err in exc.errors():
            field = ".".join(str(p) for p in err["loc"] if p not in ("body", "query", "path"))
            errors.setdefault(field, []).append(err["msg"])
        return _error(request, 422, "Validation failed", "validation_failed", errors)

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = {401: "unauthenticated", 403: "forbidden", 404: "not_found", 405: "method_not_allowed"}
        return _error(request, exc.status_code, str(exc.detail), code.get(exc.status_code, "http_error"))

    @app.exception_handler(Exception)
    async def unhandled(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled error request_id=%s", request.state.request_id)
        return _error(request, 500, "Internal server error", "server_error")
```

The 500 handler logs the traceback and returns a generic message: no exception text, SQL or class names reach the client.

### 7. Request ID middleware

```python
class RequestIdMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = dict(scope["headers"])
        rid = headers.get(b"x-request-id", b"").decode()[:64] or uuid.uuid4().hex
        scope.setdefault("state", {})["request_id"] = rid

        async def send_with_id(message: Message) -> None:
            if message["type"] == "http.response.start":
                message.setdefault("headers", []).append((b"x-request-id", rid.encode()))
            await send(message)

        await self.app(scope, receive, send_with_id)
```

Pure ASGI middleware, not `BaseHTTPMiddleware` (which breaks streaming and contextvars). Put the request id into a `contextvars.ContextVar` + logging filter so every log line carries it.

### 8. Dependencies (`Depends` + `Annotated`)

```python
# app/deps.py
SessionDep = Annotated[AsyncSession, Depends(get_session)]
bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    session: SessionDep,
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> CurrentUser:
    if creds is None:
        raise HTTPException(status_code=401, detail="Unauthenticated")
    user_id = decode_access_token(creds.credentials)  # raises 401 on bad/expired token
    user = await UserRepository(session).get(user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="Unauthenticated")
    return CurrentUser(id=user.id, role=user.role)


CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]


def get_order_service(session: SessionDep) -> OrderService:
    return OrderService(OrderRepository(session))


OrderServiceDep = Annotated[OrderService, Depends(get_order_service)]
```

- JWT: `PyJWT` with an explicit `algorithms=["HS256"]` (or RS256) list, `exp` required, secret from `Settings.jwt_secret`.
- Auth on the router (`APIRouter(dependencies=[Depends(get_current_user)])`) so a new endpoint cannot forget it.
- Every dependency swaps in tests with `app.dependency_overrides` (`python-testing`).

### 9. Router: HTTP only

```python
router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("", status_code=201)
async def create_order(
    request: Request, body: OrderCreate, user: CurrentUserDep, service: OrderServiceDep
) -> dict[str, object]:
    order = await service.create(user_id=user.id, data=body)
    return ok(request, OrderOut.model_validate(order).model_dump(mode="json"), "Order created")


@router.get("")
async def list_orders(
    request: Request,
    user: CurrentUserDep,
    service: OrderServiceDep,
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=100)] = 20,
) -> dict[str, object]:
    items, total = await service.paginate_for_user(user.id, page=page, per_page=per_page)
    data = [OrderOut.model_validate(o).model_dump(mode="json") for o in items]
    return paged(request, data, page=page, per_page=per_page, total=total)


@router.get("/{order_id}")
async def get_order(request: Request, order_id: int, user: CurrentUserDep, service: OrderServiceDep) -> dict[str, object]:
    order = await service.get_for_user(order_id, user_id=user.id)  # 404 when not owned: no IDOR
    return ok(request, OrderOut.model_validate(order).model_dump(mode="json"))
```

- `async def` endpoints must only await async I/O. A sync library call → plain `def` endpoint (runs in threadpool) or `await asyncio.to_thread(...)`.
- Every list endpoint is paginated with a capped `per_page`.

### 10. Service: rules and the transaction

```python
class OrderService:
    def __init__(self, repo: OrderRepository) -> None:
        self._repo = repo

    async def cancel(self, order_id: int, *, user_id: int) -> Order:
        order = await self._repo.find_for_update(order_id, user_id=user_id)
        if order is None:
            raise NotFoundError("Order not found")
        if order.status == "cancelled":
            raise ConflictError("Order already cancelled", "order_already_cancelled")
        order.status = "cancelled"
        await self._repo.session.commit()
        return order
```

- The service owns the transaction: it calls `commit()` once, at the end. An exception skips the commit and `get_session` closes the session, which rolls back. Repositories only `flush()`, never commit.
- Don't wrap service code in `session.begin()`: the request session has usually auto-begun already (e.g. `get_current_user` queried it), and `begin()` then raises.
- Money/stock changes lock the row (`with_for_update()`) inside the transaction.
- No HTTP concepts (`Request`, `HTTPException`) in services; they raise `AppError`.

### 11. Repository: every query

```python
class OrderRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def paginate_for_user(self, user_id: int, *, page: int, per_page: int) -> tuple[list[Order], int]:
        base = select(Order).where(Order.user_id == user_id)
        total = await self.session.scalar(select(func.count()).select_from(base.subquery())) or 0
        rows = await self.session.scalars(
            base.options(selectinload(Order.items))
            .order_by(Order.created_at.desc(), Order.id.desc())
            .limit(per_page)
            .offset((page - 1) * per_page)
        )
        return list(rows), total

    async def find_for_update(self, order_id: int, *, user_id: int) -> Order | None:
        stmt = select(Order).where(Order.id == order_id, Order.user_id == user_id).with_for_update()
        return await self.session.scalar(stmt)
```

Name methods for what the caller needs (`paginate_for_user`, `find_for_update`). Scope by owner in the query itself.

### 12. Background work, cache, outbound calls

- `BackgroundTasks` only for fire-and-forget work that may be lost (a log ping). Anything that must happen → RabbitMQ.
- Details and templates: [references/workers-and-cache.md](references/workers-and-cache.md).

## Examples

### New endpoint checklist

1. Test first (`python-testing` §6): happy path, 401, 404 for other user's resource, 422, each business code.
2. Schema in `schemas.py` with `extra="forbid"` and bounds.
3. Repository method scoped by owner; service method with the transaction and `AppError`s.
4. Router: parse → call service → `ok()`/`paged()`. No logic.
5. `ruff format . && ruff check . && mypy src && pytest`.

### Anti-patterns

| Don't | Do |
|-------|----|
| `return order` (ORM object) from a router | `OrderOut.model_validate(order)` inside `ok()` |
| `raise HTTPException(409, ...)` in a service | `raise ConflictError(..., code=...)` |
| `requests.get(...)` inside `async def` | `app.state.http` (`httpx.AsyncClient`) with timeout |
| `session.commit()` in a repository | one `commit()` at the end of the service method |
| `create_async_engine(...)` per request | one engine per process (`app/db.py`) |
| `order.items` in async code without eager load | `selectinload(Order.items)`; `lazy="raise"` |
| `Model(**body.model_dump())` for all fields | map allowed fields explicitly |

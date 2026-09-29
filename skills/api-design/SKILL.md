---
name: api-design
description: >-
  The API contract for every REST API in the kit (Laravel, NestJS, Go). In an existing project, detect the
  response format it already uses and follow it exactly. In a new project, use the default contract:
  data + paging (lists only) + meta, with errors as data null plus meta.message, meta.code and meta.errors. Also covers
  resource naming, HTTP methods, status codes, error codes, offset and keyset pagination, filtering, sorting, rate-limit
  headers and /api/v1 versioning. Use when adding or changing an endpoint, designing a response, reviewing an API
  contract, or when asked "format response", "chuẩn hoá API", "thiết kế API". Do NOT use for GraphQL, gRPC or
  front-end data fetching.
origin: My Claude Kit
---

# API Contract

One project has one response format. The format is **discovered, not invented**: an existing project keeps the format it already has, and only a brand-new project gets the default below.

## When to Use

- Adding or changing any endpoint
- Writing the response helper, exception rendering or pagination for a new project
- Reviewing a diff that touches responses, errors or pagination
- A client (SPA, mobile) reports an inconsistent response

## How It Works

### Step 0 — Existing project? Detect and follow its format

Before writing any response code, find out what the project already returns:

1. **Find the helper.**
   - Laravel: `grep -rnE "ApiResponse|ResponseTrait|sendResponse|respondWith|->json\(" app/Http app/Support app/Traits`
   - NestJS: `grep -rnE "Interceptor|ExceptionFilter|class .*Response" src`
   - Go: `grep -rnE "func (write|respond|render)JSON|func .*Error\(w" .`
2. **Read 2–3 existing endpoints and their tests** (or the OpenAPI/Postman collection). Capture: the success shape, the list/pagination shape, the error shape, the validation-error shape, key casing (`snake_case` vs `camelCase`) and the date format.
3. **Write it down.** If the project `CLAUDE.md` has no "API contract" section, propose one with the captured shapes, so the next session does not have to rediscover it.
4. **Follow it exactly**, even where it differs from the default below. Reuse the project's helper, and never add a second helper next to it.
5. **Mixed formats inside one project:** follow the format of the module you are in (or the newest `/api/vN`), and report the inconsistency. Never introduce a third format.
6. **Changing an existing format is a breaking change.** It happens only under a new version (`/api/v2`), with the client teams agreeing to it.

Only when there is no existing API (a new project, or a new service) does the default contract apply.

### Default contract for new projects

**Top-level keys:** `data`, `paging` (lists only), `meta`. Nothing else at the top level.

| Response | `data` | `paging` | `meta` |
|----------|--------|----------|--------|
| Single resource / action result | object | absent | `message`, `request_id` |
| List | array | present | `message`, `request_id` |
| No content (DELETE) | — | — | — (HTTP 204, empty body) |
| Error (any 4xx/5xx) | `null` | absent | `message`, `code`, `errors` (validation only), `request_id` |

```json
// 200 — list (offset paging)
{
  "data": [{ "id": 1, "status": "pending" }],
  "paging": { "current_page": 1, "per_page": 20, "total": 42, "last_page": 3 },
  "meta": { "message": "OK", "request_id": "01J9ZC4K2T" }
}

// 200 — list (keyset paging, for feeds and large tables)
{
  "data": [{ "id": 981, "status": "paid" }],
  "paging": { "per_page": 20, "next_cursor": "961", "has_more": true },
  "meta": { "message": "OK", "request_id": "01J9ZC4K2T" }
}

// 201 — created
{
  "data": { "id": 12, "status": "pending", "created_at": "2026-09-29T10:30:00+07:00" },
  "meta": { "message": "Order created", "request_id": "01J9ZC4K2T" }
}

// 422 — validation error
{
  "data": null,
  "meta": {
    "message": "Validation failed",
    "code": "validation_failed",
    "errors": { "quantity": ["The quantity field is required."] },
    "request_id": "01J9ZC4K2T"
  }
}

// 409 — business rule error
{
  "data": null,
  "meta": { "message": "Order already paid", "code": "order_already_paid", "request_id": "01J9ZC4K2T" }
}
```

Rules:
- **Keys are `snake_case`** in new projects, both in payloads and in `paging`/`meta`.
- **`meta.message`** is short and human-readable. It is safe to show, and never contains stack traces, SQL or class names.
- **`meta.code`** is a stable, machine-readable `snake_case` string that clients switch on. Never change a published code.
- **`meta.errors`** exists only for validation errors, as `field → [messages]`. Nested fields use dot keys (`items.0.quantity`).
- **`meta.request_id`** echoes the `X-Request-Id` request header, or a generated one. It is also returned as a response header and written into every log line.
- **Dates** are ISO-8601 with an offset. **Money** is an integer in minor units (or a decimal string), never a float. **IDs** are serialised the same way everywhere.
- **Don't add top-level keys** like `success` or `status`. The HTTP status code carries success or failure.

### Standard error codes

| HTTP | `meta.code` | When |
|------|-------------|------|
| 400 | `bad_request` | Malformed JSON, or a wrong content type |
| 401 | `unauthenticated` | Missing or invalid token/session |
| 403 | `forbidden` | Authenticated but not allowed |
| 404 | `not_found` | Resource doesn't exist, or is not visible to this user |
| 405 | `method_not_allowed` | Wrong verb |
| 409 | `<domain>_conflict` or a specific code (`order_already_paid`) | State conflict, duplicate |
| 422 | `validation_failed` | Field validation (with `errors`) |
| 422 | a specific business code (`insufficient_stock`) | A business rule violated by valid input |
| 429 | `rate_limited` | Too many requests (plus a `Retry-After` header) |
| 500 | `server_error` | Unexpected failure; generic message |
| 503 | `service_unavailable` | Dependency down or maintenance (plus `Retry-After`) |

## Examples

### Laravel — `App\Support\ApiResponse` (new projects)

```php
<?php

namespace App\Support;

use Illuminate\Http\JsonResponse;
use Illuminate\Http\Resources\Json\JsonResource;
use Illuminate\Http\Resources\Json\ResourceCollection;

final class ApiResponse
{
    public static function success(mixed $data = null, string $message = 'OK', int $status = 200): JsonResponse
    {
        return response()->json([
            'data' => $data instanceof JsonResource ? $data->resolve(request()) : $data,
            'meta' => self::meta($message),
        ], $status);
    }

    /** @param ResourceCollection $collection built from a LengthAwarePaginator */
    public static function paginated(ResourceCollection $collection, string $message = 'OK'): JsonResponse
    {
        $page = $collection->resource;

        return response()->json([
            'data' => $collection->resolve(request()),
            'paging' => [
                'current_page' => $page->currentPage(),
                'per_page' => $page->perPage(),
                'total' => $page->total(),
                'last_page' => $page->lastPage(),
            ],
            'meta' => self::meta($message),
        ]);
    }

    public static function cursor(ResourceCollection $collection, ?string $nextCursor, int $perPage, string $message = 'OK'): JsonResponse
    {
        return response()->json([
            'data' => $collection->resolve(request()),
            'paging' => ['per_page' => $perPage, 'next_cursor' => $nextCursor, 'has_more' => $nextCursor !== null],
            'meta' => self::meta($message),
        ]);
    }

    public static function error(string $message, int $status, string $code, ?array $errors = null): JsonResponse
    {
        $meta = ['message' => $message, 'code' => $code];
        if ($errors !== null) {
            $meta['errors'] = $errors;
        }

        return response()->json(['data' => null, 'meta' => $meta + ['request_id' => self::requestId()]], $status);
    }

    private static function meta(string $message): array
    {
        return ['message' => $message, 'request_id' => self::requestId()];
    }

    private static function requestId(): string
    {
        return (string) (request()->headers->get('X-Request-Id') ?? request()->attributes->get('request_id', ''));
    }
}
```

A small `AssignRequestId` middleware sets `request_id` (from `X-Request-Id` or `Str::ulid()`), adds it to the log context (`Log::withContext`), and returns it as the `X-Request-Id` response header. Exception rendering: `laravel-patterns/references/exceptions.md`.

### NestJS — interceptor + exception filter (new projects)

```ts
// common/http/response.interceptor.ts
@Injectable()
export class ResponseInterceptor implements NestInterceptor {
  intercept(ctx: ExecutionContext, next: CallHandler): Observable<unknown> {
    const req = ctx.switchToHttp().getRequest();
    return next.handle().pipe(
      map((body: { data: unknown; paging?: Paging; message?: string }) => ({
        data: body.data,
        ...(body.paging ? { paging: body.paging } : {}),
        meta: { message: body.message ?? 'OK', request_id: req.id },
      })),
    );
  }
}

// common/http/all-exceptions.filter.ts
@Catch()
export class AllExceptionsFilter implements ExceptionFilter {
  catch(e: unknown, host: ArgumentsHost) {
    const http = host.switchToHttp();
    const req = http.getRequest();
    const { status, code, message, errors } = toApiError(e); // maps HttpException, ValidationError, BusinessError, unknown -> 500
    http.getResponse().status(status).json({
      data: null,
      meta: { message, code, ...(errors ? { errors } : {}), request_id: req.id },
    });
  }
}
```

Services return `{ data, paging? , message? }`. Controllers never build the envelope by hand. Configure `ValidationPipe` with an `exceptionFactory` that produces `field → [messages]`.

### Go — `writeData` / `writeList` / `writeError` (new projects)

```go
type Meta struct {
	Message   string              `json:"message"`
	Code      string              `json:"code,omitempty"`
	Errors    map[string][]string `json:"errors,omitempty"`
	RequestID string              `json:"request_id"`
}

type Paging struct {
	CurrentPage int    `json:"current_page,omitempty"`
	PerPage     int    `json:"per_page"`
	Total       int64  `json:"total,omitempty"`
	LastPage    int    `json:"last_page,omitempty"`
	NextCursor  string `json:"next_cursor,omitempty"`
	HasMore     *bool  `json:"has_more,omitempty"`
}

type envelope struct {
	Data   any     `json:"data"`
	Paging *Paging `json:"paging,omitempty"`
	Meta   Meta    `json:"meta"`
}

func writeData(w http.ResponseWriter, r *http.Request, status int, data any, msg string) {
	writeJSON(w, status, envelope{Data: data, Meta: Meta{Message: msg, RequestID: requestID(r)}})
}

func writeList(w http.ResponseWriter, r *http.Request, data any, p Paging) {
	writeJSON(w, http.StatusOK, envelope{Data: data, Paging: &p, Meta: Meta{Message: "OK", RequestID: requestID(r)}})
}

func writeError(w http.ResponseWriter, r *http.Request, status int, code, msg string, fields map[string][]string) {
	writeJSON(w, status, envelope{Data: nil, Meta: Meta{Message: msg, Code: code, Errors: fields, RequestID: requestID(r)}})
}
```

## Resource Design

```
GET    /api/v1/orders              list (paged)
GET    /api/v1/orders/{id}         detail
POST   /api/v1/orders              create           → 201 + Location
PATCH  /api/v1/orders/{id}         partial update   → 200
DELETE /api/v1/orders/{id}         delete           → 204
GET    /api/v1/users/{id}/orders   sub-resource (ownership)
POST   /api/v1/orders/{id}/cancel  action that is not CRUD (verbs sparingly)
```

- Resources are plural nouns in kebab-case (`/team-members`): no verbs in paths, no `snake_case` paths.
- `PUT` only for a genuine full replacement. `PATCH` for partial updates.
- `GET` never changes state. `DELETE` and `PUT` are idempotent. Make `POST` creates safe to retry with an `Idempotency-Key` (`scalability/references/resilience.md`).

## Status Codes

- `200` for reads and updates with a body, `201` + `Location` for creates, `202` for accepted async work (with a status resource), and `204` for deletes.
- Never return `200` with an error body. Never return `500` for bad input.
- `404` rather than `403` when revealing that a resource exists would leak information (another tenant's record).

## Pagination

| Use | Type | Query | `paging` |
|-----|------|-------|----------|
| Admin tables, page numbers, small/medium data | offset | `?page=2&per_page=20` | `current_page`, `per_page`, `total`, `last_page` |
| Feeds, infinite scroll, exports, big tables | keyset | `?cursor=<id>&per_page=20` | `per_page`, `next_cursor`, `has_more` |

- Cap `per_page` (default 20, max 100) on the server.
- Keyset pagination orders by a unique, indexed column (usually `id`) and fetches `per_page + 1` rows to compute `has_more`. Details: `scalability/references/code-level.md`.
- `total` on huge tables is expensive. Drop it, or cache it, rather than counting on every request.

## Filtering, Sorting, Search

```
GET /api/v1/orders?status=paid&customer_id=42
GET /api/v1/products?price_min=10&price_max=100
GET /api/v1/products?category=phones,tablets
GET /api/v1/products?sort=-created_at,price
GET /api/v1/products?q=wireless+headphones
```

- Every filter and sort field is **allow-listed** and validated (a FormRequest, DTO or validator). Never pass raw column names to the query.
- Sorted and filtered columns need indexes (`database-reviewer` checks this).

## Authentication and Rate Limits

- Auth: `Authorization: Bearer <token>` for mobile and third-party clients; a cookie session for the first-party SPA (Laravel Sanctum). Server-to-server: an API key header, scoped and rotatable.
- Rate limits return `429`, `meta.code = rate_limited`, a `Retry-After` header, and `X-RateLimit-Limit` / `X-RateLimit-Remaining` headers. Limits by tier: `scalability/references/resilience.md`.

## Versioning

- URL versioning only: `/api/v1/...`. Start at v1, and keep at most two live versions.
- **Non-breaking** (no new version): adding fields, optional parameters, endpoints or error codes.
- **Breaking** (new version): removing or renaming fields, changing types, changing the response format, changing auth.
- Deprecate with a `Sunset` header and notice to the client teams, then `410 Gone` after the date.

## Checklist before shipping an endpoint

- [ ] Existing project: response matches the format detected in Step 0 (same helper, same casing, same pagination fields)
- [ ] New project: `data` + `paging` (lists only) + `meta`; errors are `data: null` + `meta.message/code[/errors]`
- [ ] Plural kebab-case resource under `/api/v1`, correct verb and status code
- [ ] Input validated; filters and sorts allow-listed; `per_page` capped
- [ ] Lists paginated (keyset for large or unbounded data)
- [ ] Auth required unless explicitly public; ownership checked (403/404)
- [ ] Rate limit set; `Idempotency-Key` supported on retryable creates
- [ ] No internal details in `meta.message`; stable `meta.code`
- [ ] Tests assert the exact envelope (`laravel-tdd`)

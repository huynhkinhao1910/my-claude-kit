---
name: laravel-patterns
description: >-
  House style for Laravel REST APIs (SPA/mobile clients): FormRequest -> Controller -> Service -> Repository -> Model,
  responses per the api-design contract (the project's existing format, or data/paging/meta for a new project)
  built from API Resources, central exception rendering, /api/v1 routes,
  Sanctum, RabbitMQ queues and Redis cache. Use when writing or refactoring controllers, routes, services,
  repositories, Eloquent models or queries, migrations, form requests, resources, jobs or caching in a Laravel
  codebase. Trigger on requests like "tạo controller", "viết API", "thêm endpoint", "sửa model", "thêm migration",
  "tách service", "viết repository", "thêm job", or any task touching .php files in app/, routes/, config/ or
  database/. Do NOT use for non-Laravel PHP, Blade/Inertia front ends, or front-end-only work.
origin: My Claude Kit
---

# Laravel House Style

These are the conventions for every Laravel API project. They are decisions, not options: when a project's own `CLAUDE.md` says otherwise, the project wins, and nothing else overrides this file.

## When to Use

- Adding or changing an API endpoint, service, repository, model, migration, job or cache
- Refactoring code that breaks the layer rules below
- Reviewing Laravel code (`laravel-reviewer` checks against this file)

## How It Works

Every request goes through the same five layers, and each layer has one job:

```
Request ─▶ FormRequest ─▶ Controller ─▶ Service ─▶ Repository ─▶ Model
           validate        HTTP only      business    queries       schema,
           + authorize     + response     rules, tx   only          casts, relations
                              ▲
                              └── API Resource shapes the output
```

| Layer | Owns | Never does |
|-------|------|------------|
| FormRequest | `rules()`, `authorize()`, input normalisation | business rules, queries beyond `exists`/`unique` rules |
| Controller | call one service method, return it through the project's response helper (`ApiResponse` in new projects) | queries, `DB::`, `try/catch`, business `if`s |
| Service | business rules, `DB::transaction`, dispatching jobs/events, cache invalidation | `Model::where()`/`query()`, building HTTP responses |
| Repository | every Eloquent query, eager loading, locking, pagination | business decisions, transactions, HTTP |
| Model | `$fillable`, `$casts`, relations, scopes | queries called from outside a repository |

Rules that apply across layers:

1. Input reaches a service as `$request->validated()` (a plain array). Never pass the `Request` object down.
2. Every response uses the project's API format (`api-design`, Step 0). In an **existing project**, reuse its helper and shape. In a **new project**, use `ApiResponse` (`data` + `paging` for lists + `meta`). Never hand-build `response()->json()` in a controller.
3. Errors are thrown, not returned: throw `BusinessException` (or let Laravel throw), and the exception handler renders them in the project's format.
4. Repositories are concrete classes injected by the container. They have no interface and no binding.
5. Transactions live in services. Jobs and events dispatched inside a transaction use `afterCommit()`.
6. Routes live under `/api/v1`, and controllers under `App\Http\Controllers\Api\V1`.

## Examples

### Layout

```
app/
├── Exceptions/
│   ├── BusinessException.php
│   └── Handler.php                 # renders every API error in the project's format
├── Http/
│   ├── Controllers/Api/V1/
│   ├── Requests/Api/V1/            # StoreOrderRequest, IndexOrderRequest
│   └── Resources/                  # OrderResource
├── Jobs/                           # queued on RabbitMQ
├── Models/
├── Policies/
├── Repositories/                   # OrderRepository (concrete, no interface)
├── Services/                       # OrderService
└── Support/ApiResponse.php         # new projects; existing ones keep their helper
routes/api.php                      # Route::prefix('v1')
tests/Feature/Api/V1/
```

### Response format

Follow `api-design`:

- **Existing project:** detect the format first (Step 0). Grep for the helper, read two endpoints and their tests, and reuse exactly that helper and shape. The examples below use `ApiResponse`. Swap in the project's own helper and keep everything else.
- **New project:** copy `ApiResponse` from `api-design` into `app/Support/ApiResponse.php`. It produces:

```json
{ "data": { "id": 12, "status": "pending" }, "meta": { "message": "Order created", "request_id": "01J9ZC4K2T" } }
{ "data": [ ... ], "paging": { "current_page": 1, "per_page": 20, "total": 42, "last_page": 3 }, "meta": { "message": "OK", "request_id": "01J9ZC4K2T" } }
{ "data": null, "meta": { "message": "Validation failed", "code": "validation_failed", "errors": { "quantity": ["The quantity field is required."] }, "request_id": "01J9ZC4K2T" } }
```

### Routes

```php
// routes/api.php  (already prefixed with /api)
use App\Http\Controllers\Api\V1\AuthController;
use App\Http\Controllers\Api\V1\OrderController;

Route::prefix('v1')->name('api.v1.')->group(function () {
    Route::post('auth/token', [AuthController::class, 'token'])->middleware('throttle:login');

    Route::middleware('auth:sanctum')->group(function () {
        Route::apiResource('orders', OrderController::class)->only(['index', 'store', 'show']);
    });
});
```

### FormRequest

```php
namespace App\Http\Requests\Api\V1;

use Illuminate\Foundation\Http\FormRequest;

final class StoreOrderRequest extends FormRequest
{
    public function authorize(): bool
    {
        return $this->user()->can('create', \App\Models\Order::class);
    }

    public function rules(): array
    {
        return [
            'product_id' => ['required', 'integer', 'exists:products,id'],
            'quantity' => ['required', 'integer', 'min:1', 'max:100'],
            'note' => ['nullable', 'string', 'max:500'],
        ];
    }
}
```

### Controller: HTTP only

```php
namespace App\Http\Controllers\Api\V1;

use App\Http\Controllers\Controller;
use App\Http\Requests\Api\V1\IndexOrderRequest;
use App\Http\Requests\Api\V1\StoreOrderRequest;
use App\Http\Resources\OrderResource;
use App\Models\Order;
use App\Services\OrderService;
use App\Support\ApiResponse;
use Illuminate\Http\JsonResponse;

final class OrderController extends Controller
{
    public function __construct(private readonly OrderService $orders) {}

    public function index(IndexOrderRequest $request): JsonResponse
    {
        $page = $this->orders->listFor($request->user(), $request->validated());

        return ApiResponse::paginated(OrderResource::collection($page));
    }

    public function store(StoreOrderRequest $request): JsonResponse
    {
        $order = $this->orders->place($request->user(), $request->validated());

        return ApiResponse::success(new OrderResource($order), 'Order created', 201);
    }

    public function show(Order $order): JsonResponse
    {
        $this->authorize('view', $order);

        return ApiResponse::success(new OrderResource($this->orders->detail($order)));
    }
}
```

Implicit route model binding (`Order $order`) is the one allowed lookup outside a repository. Loading relations for that model still goes through the repository.

### Service: business rules and transactions

```php
namespace App\Services;

use App\Exceptions\BusinessException;
use App\Jobs\SendOrderConfirmation;
use App\Models\Order;
use App\Models\User;
use App\Repositories\OrderRepository;
use App\Repositories\ProductRepository;
use Illuminate\Contracts\Pagination\LengthAwarePaginator;
use Illuminate\Support\Facades\Cache;
use Illuminate\Support\Facades\DB;

final class OrderService
{
    public function __construct(
        private readonly OrderRepository $orders,
        private readonly ProductRepository $products,
    ) {}

    public function listFor(User $user, array $filters): LengthAwarePaginator
    {
        return $this->orders->paginateForUser($user->id, $filters, (int) ($filters['per_page'] ?? 15));
    }

    public function place(User $user, array $data): Order
    {
        $order = DB::transaction(function () use ($user, $data): Order {
            $product = $this->products->findForUpdate($data['product_id']);

            if ($product->stock < $data['quantity']) {
                throw new BusinessException('Not enough stock', 422, 'insufficient_stock', ['quantity' => ['Only '.$product->stock.' left.']]);
            }

            $this->products->decrementStock($product, $data['quantity']);

            $order = $this->orders->create([
                'user_id' => $user->id,
                'product_id' => $product->id,
                'quantity' => $data['quantity'],
                'total' => $product->price * $data['quantity'],
                'note' => $data['note'] ?? null,
                'status' => 'pending',
            ]);

            SendOrderConfirmation::dispatch($order->id)->afterCommit();

            return $order;
        });

        Cache::forget("v1:orders:user:{$user->id}:summary");

        return $order;
    }

    public function detail(Order $order): Order
    {
        return $this->orders->loadDetail($order);
    }
}
```

### Repository: every query, nothing else

```php
namespace App\Repositories;

use App\Models\Order;
use Illuminate\Contracts\Pagination\LengthAwarePaginator;
use Illuminate\Database\Eloquent\Builder;

final class OrderRepository
{
    public function paginateForUser(int $userId, array $filters, int $perPage = 15): LengthAwarePaginator
    {
        return Order::query()
            ->where('user_id', $userId)
            ->when($filters['status'] ?? null, fn (Builder $q, string $status) => $q->where('status', $status))
            ->with('product:id,name,price')
            ->latest('id')
            ->paginate(min($perPage, 100));
    }

    public function create(array $attributes): Order
    {
        return Order::query()->create($attributes);
    }

    public function loadDetail(Order $order): Order
    {
        return $order->load(['product', 'user:id,name']);
    }
}
```

```php
namespace App\Repositories;

use App\Models\Product;

final class ProductRepository
{
    public function findForUpdate(int $id): Product
    {
        return Product::query()->lockForUpdate()->findOrFail($id);   // only inside a service transaction
    }

    public function decrementStock(Product $product, int $quantity): void
    {
        $product->decrement('stock', $quantity);
    }
}
```

Repository methods are named for what the caller needs (`paginateForUser`, `findForUpdate`), not generic `getAll()`. Always cap `per_page`.

### API Resource

```php
namespace App\Http\Resources;

use Illuminate\Http\Request;
use Illuminate\Http\Resources\Json\JsonResource;

final class OrderResource extends JsonResource
{
    public function toArray(Request $request): array
    {
        return [
            'id' => $this->id,
            'status' => $this->status,
            'quantity' => $this->quantity,
            'total' => $this->total,
            'note' => $this->note,
            'product' => new ProductResource($this->whenLoaded('product')),
            'created_at' => $this->created_at?->toIso8601String(),
        ];
    }
}
```

- Use `whenLoaded()` for relations, so a Resource never triggers a lazy query.
- Format dates as ISO-8601. Money is an integer in the smallest unit, or a decimal string, never a float.
- Never expose internal columns such as `password`, `remember_token`, or soft-delete flags unless the client needs them.

### Errors: `BusinessException` + central Handler

```php
namespace App\Exceptions;

use RuntimeException;
use Throwable;

final class BusinessException extends RuntimeException
{
    public function __construct(
        string $message,
        private readonly int $status = 422,
        private readonly string $errorCode = 'business_rule_violated',
        private readonly ?array $errors = null,
        ?Throwable $previous = null,
    ) {
        parent::__construct($message, 0, $previous);
    }

    public function status(): int { return $this->status; }
    public function errorCode(): string { return $this->errorCode; }
    public function errors(): ?array { return $this->errors; }
}
```

The Handler maps every exception on `api/*` to the project's error format (new projects: `data: null` + `meta.message/code[/errors]`). See `references/exceptions.md` for the full Laravel 10 `Handler` and the Laravel 11+ `bootstrap/app.php` versions.

| Exception | Status | `meta.code` (new projects) |
|-----------|--------|----------|
| `ValidationException` | 422 | `validation_failed` (+ `meta.errors`) |
| `AuthenticationException` | 401 | `unauthenticated` |
| `AuthorizationException` / `AccessDeniedHttpException` | 403 | `forbidden` |
| `ModelNotFoundException` / `NotFoundHttpException` | 404 | `not_found` |
| `BusinessException` | its own status | its own `errorCode()` |
| anything else | 500 | `server_error`; generic message unless `app.debug` |

### Models and migrations

```php
namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

final class Order extends Model
{
    protected $fillable = ['user_id', 'product_id', 'quantity', 'total', 'note', 'status'];

    protected $casts = [
        'quantity' => 'integer',
        'total' => 'integer',
        'created_at' => 'immutable_datetime',
    ];

    public function product(): BelongsTo { return $this->belongsTo(Product::class); }
    public function user(): BelongsTo { return $this->belongsTo(User::class); }
}
```

- Every new column goes into `$fillable` and `$casts` in the same change.
- Migrations: one concern per file; `foreignId()->constrained()` with an explicit `cascadeOnDelete()` or `restrictOnDelete()`; index every column used in `where` or `orderBy`. Changes to big MySQL tables go past `database-reviewer`.

### Queues (RabbitMQ) and cache (Redis)

- Jobs take IDs, never models or large payloads. They are idempotent, declare `$tries`, `$backoff` and `$timeout`, and implement `failed()`.
- A job dispatched from inside a transaction uses `->afterCommit()`.
- Cache keys follow `v1:<resource>:<scope>:<id>[:<variant>]`, always with a TTL. The service that writes the data invalidates the key.

See `references/rabbitmq-queues.md` for connection config, workers, dead-lettering and a full job example.

### Checklist before finishing a change

- [ ] Controller contains only a service call plus the project's response helper
- [ ] No `Model::` or `->query()` calls outside `app/Repositories` (route model binding excepted)
- [ ] Multi-write paths wrapped in `DB::transaction` inside the service; jobs use `afterCommit()`
- [ ] New inputs validated in a FormRequest; service receives `validated()`
- [ ] Response matches the project's format (`api-design` Step 0), or `data`/`paging`/`meta` in a new project; lists paginated with a capped `per_page`
- [ ] Errors thrown, not caught and re-shaped in controllers
- [ ] Feature test covers success, 422, 401/403 and 404 paths (`laravel-tdd`)
- [ ] `vendor/bin/pint --test` passes

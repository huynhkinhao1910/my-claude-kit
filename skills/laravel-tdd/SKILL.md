---
name: laravel-tdd
description: >-
  Test-driven development for Laravel APIs in the house style: PHPUnit only, a MySQL test database, feature tests
  against /api/v1 that assert the exact response format (the project's own, or data/paging/meta), Sanctum auth, the 401/403/404/422 paths,
  service tests with real repositories, and Queue/Mail/Http fakes for RabbitMQ jobs and external calls. Use when
  writing or fixing tests for a Laravel endpoint, service, repository, job or policy, or reproducing a Laravel bug
  with a failing test. Trigger on "viết test", "thêm test cho API", "test fail", "reproduce bug". Do NOT use for
  Pest, Blade/Inertia pages, front-end tests or non-Laravel PHP.
origin: My Claude Kit
---

# Laravel TDD (house style)

Every behaviour change ships with a PHPUnit test that fails first. Tests exercise the API the way a client does and assert the response format, not the implementation.

## When to Use

- New endpoint or change to an existing one
- Bug fix: reproduce with a failing test before touching code
- New service rule, repository query, job or policy

## How It Works

1. **Red:** write the feature test for the endpoint, covering the success path and at least one failure path. Run it and confirm it fails for the right reason (404 route missing, or an assertion on the response shape), not because of a typo.
2. **Green:** implement through the layers (FormRequest → Controller → Service → Repository) until it passes.
3. **Refactor:** keep the test green while you clean up, then run `vendor/bin/pint --test`.

| Layer | Test type | Location | Database |
|-------|-----------|----------|----------|
| Endpoint (routing, validation, auth, response format) | Feature | `tests/Feature/Api/V1/<Resource>/` | yes |
| Service business rules | Feature-style with real repositories | `tests/Feature/Services/` | yes |
| Repository queries that are complex (filters, locking, aggregates) | Feature | `tests/Feature/Repositories/` | yes |
| Pure PHP (value objects, calculators) | Unit | `tests/Unit/` | no |

Repositories are concrete classes, so tests use the real ones against MySQL. Mock only things outside the app: HTTP APIs, payment gateways, mail.

## Examples

### Test database: MySQL, not SQLite

Production runs MySQL, and SQLite behaves differently on JSON columns, collation, `lockForUpdate`, strict mode and foreign keys. Use a dedicated database:

```xml
<!-- phpunit.xml -->
<php>
    <env name="APP_ENV" value="testing"/>
    <env name="DB_CONNECTION" value="mysql"/>
    <env name="DB_DATABASE" value="app_testing"/>
    <env name="CACHE_DRIVER" value="array"/>
    <env name="QUEUE_CONNECTION" value="sync"/>
    <env name="MAIL_MAILER" value="array"/>
    <env name="SESSION_DRIVER" value="array"/>
</php>
```

- Create the database once with `CREATE DATABASE app_testing`. Never point tests at the dev or prod database.
- Every test that touches the database uses `RefreshDatabase`. It migrates once per run and wraps each test in a transaction.
- On Laravel 11+ the cache variable is `CACHE_STORE`.

### Response assertions: `tests/Concerns/AssertsApiResponse.php`

**Existing project:** if the suite already has response assertions, use them. Otherwise write this trait **in the project's own format**, as detected in `api-design` Step 0. **New project:** use it as is. It asserts the default contract (`data` + `paging` for lists + `meta`).

```php
<?php

namespace Tests\Concerns;

use Illuminate\Testing\TestResponse;

trait AssertsApiResponse
{
    protected function assertApiSuccess(TestResponse $response, int $status = 200): TestResponse
    {
        return $response->assertStatus($status)
            ->assertJsonStructure(['data', 'meta' => ['message', 'request_id']])
            ->assertJsonMissingPath('paging')
            ->assertJsonMissingPath('meta.code');
    }

    protected function assertApiPaginated(TestResponse $response): TestResponse
    {
        return $response->assertOk()
            ->assertJsonStructure(['data', 'paging' => ['current_page', 'per_page', 'total', 'last_page'], 'meta' => ['message', 'request_id']]);
    }

    protected function assertApiError(TestResponse $response, int $status, string $code, ?array $errorFields = null): TestResponse
    {
        $response->assertStatus($status)
            ->assertJsonPath('data', null)
            ->assertJsonPath('meta.code', $code)
            ->assertJsonStructure(['meta' => ['message', 'code', 'request_id']])
            ->assertJsonMissingPath('paging');

        if ($errorFields !== null) {
            $response->assertJsonStructure(['meta' => ['errors' => $errorFields]]);
        }

        return $response;
    }
}
```

Use this trait in `Tests\TestCase`, so every test gets these helpers.

### Feature test for an endpoint

```php
<?php

namespace Tests\Feature\Api\V1\Orders;

use App\Jobs\SendOrderConfirmation;
use App\Models\Order;
use App\Models\Product;
use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Queue;
use Laravel\Sanctum\Sanctum;
use Tests\TestCase;

final class StoreOrderTest extends TestCase
{
    use RefreshDatabase;

    private const URL = '/api/v1/orders';

    public function test_user_can_place_an_order(): void
    {
        Queue::fake();
        $user = User::factory()->create();
        $product = Product::factory()->create(['stock' => 5, 'price' => 1000]);
        Sanctum::actingAs($user);

        $response = $this->postJson(self::URL, ['product_id' => $product->id, 'quantity' => 2]);

        $this->assertApiSuccess($response, 201)
            ->assertJsonPath('data.quantity', 2)
            ->assertJsonPath('data.total', 2000);
        $this->assertDatabaseHas('orders', ['user_id' => $user->id, 'product_id' => $product->id, 'quantity' => 2]);
        $this->assertSame(3, $product->fresh()->stock);
        Queue::assertPushedOn('mail', SendOrderConfirmation::class);
    }

    public function test_it_rejects_invalid_input(): void
    {
        Sanctum::actingAs(User::factory()->create());

        $response = $this->postJson(self::URL, ['quantity' => 0]);

        $this->assertApiError($response, 422, 'validation_failed', ['product_id', 'quantity']);
    }

    public function test_it_rejects_quantity_above_stock(): void
    {
        Sanctum::actingAs(User::factory()->create());
        $product = Product::factory()->create(['stock' => 1]);

        $response = $this->postJson(self::URL, ['product_id' => $product->id, 'quantity' => 2]);

        $this->assertApiError($response, 422, 'insufficient_stock', ['quantity']);
        $this->assertDatabaseCount('orders', 0);
        $this->assertSame(1, $product->fresh()->stock);   // transaction rolled back
    }

    public function test_guest_gets_401(): void
    {
        $this->assertApiError($this->postJson(self::URL, []), 401, 'unauthenticated');
    }
}
```

Each endpoint needs these cases, as they apply:

| Case | Status |
|------|--------|
| success | 200 / 201 |
| invalid input | 422, `validation_failed`, with `meta.errors` keyed by field |
| unauthenticated | 401 |
| authenticated but not allowed (someone else's resource) | 403 |
| missing resource | 404 |
| business rule violation (`BusinessException`) | its status and its `meta.code` |

### Ownership and 404

```php
public function test_user_cannot_view_someone_elses_order(): void
{
    $order = Order::factory()->create();              // belongs to another user
    Sanctum::actingAs(User::factory()->create());

    $this->assertApiError($this->getJson("/api/v1/orders/{$order->id}"), 403, 'forbidden');
}

public function test_missing_order_returns_404(): void
{
    Sanctum::actingAs(User::factory()->create());

    $this->assertApiError($this->getJson('/api/v1/orders/999999'), 404, 'not_found');
}
```

### Pagination

```php
public function test_index_is_paginated_and_scoped_to_the_user(): void
{
    $user = User::factory()->create();
    Order::factory()->count(3)->for($user)->create();
    Order::factory()->count(2)->create();             // other users
    Sanctum::actingAs($user);

    $response = $this->getJson('/api/v1/orders?per_page=2');

    $this->assertApiPaginated($response)
        ->assertJsonCount(2, 'data')
        ->assertJsonPath('paging.total', 3);
}
```

### Query budget (N+1 guard)

A list or detail endpoint gets a test that fails when an N+1 comes back. Create more rows than the page shows, so that a per-row query becomes visible.

```php
public function test_index_runs_a_fixed_number_of_queries(): void
{
    $user = User::factory()->create();
    Order::factory()->count(30)->for($user)->has(OrderItem::factory()->count(2), 'items')->create();
    Sanctum::actingAs($user);

    DB::enableQueryLog();
    $this->getJson('/api/v1/orders?per_page=20')->assertOk();

    // page + count + one per eager load. The number must not grow with the row count.
    $this->assertLessThanOrEqual(6, count(DB::getQueryLog()));
}
```

Also call `Model::preventLazyLoading(! app()->isProduction())` in `AppServiceProvider::boot()`. A lazy load in a test then throws instead of silently adding queries. The budget comes from the spec NFR, or from the measured count after a `database-reviewer` `profile` fix.

### Service test with real repositories

```php
final class OrderServiceTest extends TestCase
{
    use RefreshDatabase;

    public function test_place_throws_business_exception_when_stock_is_short(): void
    {
        $product = Product::factory()->create(['stock' => 1]);

        $this->expectException(BusinessException::class);

        app(OrderService::class)->place(User::factory()->create(), ['product_id' => $product->id, 'quantity' => 3]);
    }
}
```

Resolve services from the container (`app(OrderService::class)`) so that the real repositories are injected. Use `$this->mock()` only for classes that call outside the app.

### Jobs (RabbitMQ)

- In endpoint tests, `Queue::fake()` asserts that the right job was dispatched on the right queue.
- In job tests, call `handle()` directly with real repositories and faked externals, and assert idempotency:

```php
public function test_confirmation_is_sent_only_once(): void
{
    Mail::fake();
    $order = Order::factory()->create(['confirmation_sent_at' => null]);
    $job = new SendOrderConfirmation($order->id);

    app()->call([$job, 'handle']);
    app()->call([$job, 'handle']);                    // redelivery

    Mail::assertSentCount(1);
}
```

### External services

```php
Http::fake(['api.shipping.test/*' => Http::response(['tracking' => 'X1'], 200)]);
// ... act ...
Http::assertSent(fn ($request) => $request->url() === 'https://api.shipping.test/shipments');
```

Unfaked outbound HTTP is a bug. Add `Http::preventStrayRequests()` in `TestCase::setUp()`.

### Factories

- Every model has a factory. Use states for meaningful variants (`->paid()`, `->cancelled()`), not raw arrays spread across tests.
- Use `for($user)` and `has()` for relations instead of hard-coded foreign IDs.

### Commands

```bash
php artisan test                                  # full suite
php artisan test --filter=StoreOrderTest          # one class
php artisan test --parallel                       # needs brianium/paratest
XDEBUG_MODE=coverage php artisan test --coverage --min=80
```

### Rules

- Assert outcomes: the response format and `meta.code`, the database state, dispatched jobs and sent mail. Don't assert which methods were called internally.
- One behaviour per test, with the name stating it: `test_guest_gets_401`, not `test_store_2`.
- No `sleep()` and no real network. Freeze time with `$this->travelTo(now())` when dates matter.
- A bug fix starts with a test that reproduces the bug and fails before the fix.

# Resilience: fail fast instead of piling up

Under load, the dangerous failure is not a dependency going down, but a dependency getting **slow**. Slow calls hold workers, connections and memory until everything queues behind them. Every rule here bounds how long and how often you wait.

## 1. Timeouts on every outbound call

Budget the request: if the SLO is 500 ms p95, a third-party call cannot be allowed 30 s.

| Call | Laravel | NestJS | Go |
|------|---------|--------|----|
| HTTP | `Http::connectTimeout(2)->timeout(5)` | axios `timeout: 5000` (HttpModule `timeout`) | `http.Client{Timeout: 5 * time.Second}` + `context.WithTimeout` per call |
| MySQL | connect: `options => [PDO::ATTR_TIMEOUT => 5]` | connect: mysql2 `connectTimeout` | connect: DSN `timeout=5s`; per query: `QueryContext(ctx, ...)`, where the ctx deadline cancels the query |
| MySQL read cap (all stacks) | `SELECT /*+ MAX_EXECUTION_TIME(2000) */ ...` on heavy reads, or `SET SESSION max_execution_time = 2000` for a report connection. SELECT only | | |
| Redis | `'read_timeout' => 2` in `config/database.php` redis options | ioredis `connectTimeout`, `commandTimeout` | go-redis `ReadTimeout`, `WriteTimeout`, `DialTimeout` |
| Request as a whole | PHP-FPM `request_terminate_timeout`; proxy `proxy_read_timeout` | server `requestTimeout`; proxy timeout | `http.Server{ReadHeaderTimeout, ReadTimeout, WriteTimeout, IdleTimeout}` |

```go
srv := &http.Server{
	Addr:              ":8080",
	Handler:           mux,
	ReadHeaderTimeout: 5 * time.Second,
	ReadTimeout:       10 * time.Second,
	WriteTimeout:      15 * time.Second,
	IdleTimeout:       60 * time.Second,
}
client := &http.Client{
	Timeout: 5 * time.Second,
	Transport: &http.Transport{MaxIdleConnsPerHost: 50, IdleConnTimeout: 90 * time.Second},
}
```

## 2. Retries: only idempotent calls, with backoff and jitter

- Retry on network errors, `429`, `502`, `503` and `504`. **Never** retry other 4xx.
- Use exponential backoff with full jitter (`sleep = random(0, base × 2^attempt)`), capped at 3 attempts. The retries must fit inside the request's own deadline.
- A non-idempotent call (charging a card, creating an order at a partner) is retried only with an **idempotency key** that the partner honours.

```php
// Laravel: retry 3 times, 200 ms base, only on connection errors or retryable statuses
Http::timeout(5)->retry(3, fn (int $attempt) => random_int(0, 200 * 2 ** $attempt), function (Throwable $e) {
    return $e instanceof ConnectionException
        || ($e instanceof RequestException && in_array($e->response->status(), [429, 502, 503, 504], true));
}, throw: true)->post($url, $payload);
```

In the queue, retries come from the job's `$tries` / `$backoff`. Don't stack HTTP retries inside job retries without accounting for the total.

## 3. Circuit breaker for flaky dependencies

After N consecutive failures (for example, 5 within 30 s), **open** the breaker: fail immediately for a cool-down (30 s), then let one probe through (**half-open**). Close it on success.

- **Laravel:** keep the state in Redis so every node shares it. Key `v1:cb:<service>`: a failure counter with a TTL, and an `open_until` timestamp. Wrap the client in a small `CircuitBreaker` service, and throw `BusinessException('Partner unavailable', 503)` while it is open.
- **NestJS:** `opossum` wraps a function with timeout, error threshold and reset timeout. It is per-process, which is acceptable for fail-fast behaviour.
- **Go:** `sony/gobreaker` around the client call.

Combine it with graceful degradation: when the breaker for a non-critical dependency is open, return the core response without that part.

## 4. Rate limiting

| Scope | Limit (starting point) | Where |
|-------|------------------------|-------|
| Authenticated API | 60–120 req/min per user or token | app |
| Anonymous | 30 req/min per IP | app or proxy |
| Login / OTP / password reset | 5 per min per IP + per identifier | app |
| Search / export | 10 per min per user | app |

**Laravel** (Redis cache store, so all nodes share counters):

```php
// AppServiceProvider::boot (Laravel 10: RouteServiceProvider::configureRateLimiting)
RateLimiter::for('api', fn (Request $r) => Limit::perMinute(120)->by($r->user()?->id ?: $r->ip()));
RateLimiter::for('login', fn (Request $r) => [
    Limit::perMinute(5)->by($r->ip()),
    Limit::perMinute(5)->by((string) $r->input('email')),
]);
```

**NestJS:** `@nestjs/throttler` with `@nest-lab/throttler-storage-redis`, so limits are shared across instances. Use `@Throttle({ default: { limit: 5, ttl: 60_000 } })` on the login endpoint.

**Go:** `golang.org/x/time/rate` for per-process limits, and a Redis sliding window (`INCR` + `EXPIRE`, or `redis_rate`) for limits shared across nodes.

Always return `429` in the project's error format (new projects: `meta.code = rate_limited`), with a `Retry-After` header.

## 5. Idempotency keys for client retries

Mobile networks retry. Without idempotency, "Place order" can create two orders.

1. The client sends `Idempotency-Key: <uuid>` on unsafe requests (POST create, payment).
2. Middleware checks Redis for `v1:idem:<user>:<key>`:
   - **found with a response**: return the stored response and status unchanged
   - **found "in progress"**: return `409`
   - **absent**: `SET NX` it to "in progress" with a 24h TTL, run the handler, then store the response
3. Scope keys per user, and reject a reused key whose request body hash differs (`422`).

```php
final class Idempotency
{
    public function handle(Request $request, Closure $next): Response
    {
        $key = $request->header('Idempotency-Key');
        if (! $key || ! $request->isMethod('post')) {
            return $next($request);
        }
        $cacheKey = 'v1:idem:'.$request->user()->id.':'.$key;

        if ($stored = Cache::get($cacheKey)) {
            return $stored === 'pending'
                ? ApiResponse::error('Request already in progress', 409, 'request_in_progress')
                : response()->json($stored['body'], $stored['status']);
        }
        if (! Cache::add($cacheKey, 'pending', now()->addDay())) {
            return ApiResponse::error('Request already in progress', 409, 'request_in_progress');
        }

        $response = $next($request);
        if ($response instanceof JsonResponse && $response->getStatusCode() < 500) {
            Cache::put($cacheKey, ['status' => $response->getStatusCode(), 'body' => $response->getData(true)], now()->addDay());
        } else {
            Cache::forget($cacheKey);   // let the client retry a server error
        }

        return $response;
    }
}
```

## 6. Backpressure in queues

- RabbitMQ prefetch of 1–10 per consumer, and bounded worker concurrency.
- A dead-letter exchange for messages that are rejected or have expired. Alert on the DLQ depth.
- Message TTL for work that is useless when late (e.g. a "typing" notification).
- When the queue depth keeps rising, scale consumers, shed low-priority work, or slow producers down (`202` plus a longer poll interval). Never let memory absorb it.

## 7. Graceful shutdown

On SIGTERM, first stop accepting, then drain within a deadline, then exit.

- **Laravel HTTP:** PHP-FPM finishes in-flight requests on a graceful reload (`kill -QUIT`). Keep `process_control_timeout` at or above the request timeout.
- **Laravel workers:** `queue:work` finishes the current job on SIGTERM. The container `stop_grace_period` must be at least the job `$timeout`.
- **NestJS:** call `app.enableShutdownHooks()`, close consumers and pools in `onApplicationShutdown`, and set the readiness endpoint to fail first so the LB drains the node.
- **Go:**

```go
ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
defer stop()
go func() { _ = srv.ListenAndServe() }()
<-ctx.Done()
shutdownCtx, cancel := context.WithTimeout(context.Background(), 20*time.Second)
defer cancel()
_ = srv.Shutdown(shutdownCtx) // stops accepting, waits for in-flight requests
```

In Docker Compose, set `stop_grace_period` (for example `30s`) above the drain deadline, or Docker sends SIGKILL first.

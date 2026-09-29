---
name: scalability
description: >-
  Scalability rules for Laravel, NestJS and Go APIs on MySQL, Redis and RabbitMQ, growing from one Docker Compose
  VPS to a few VPS behind a load balancer. Covers code-level load (bounded queries, keyset pagination, N+1, bulk
  writes, queue offload, short transactions), horizontal scaling (stateless nodes, Redis sessions and cache, object
  storage, read replicas, connection budgets), resilience (timeouts, retries with jitter, circuit breakers, rate
  limits, idempotency keys, RabbitMQ prefetch, graceful shutdown) and measurement (SLOs, slow query log, metrics,
  k6 load tests, capacity math). Use when designing or reviewing an endpoint, job, query or integration that must
  hold up under load, when planning the next infrastructure step, or when asked "scale", "chịu tải", "tối ưu hiệu
  năng", "load test", "chạy nhiều node". Do NOT use for index or migration detail (mysql-patterns,
  database-reviewer), front-end rendering performance (react-performance), or Kubernetes.
origin: My Claude Kit
---

# Scalability

Scale comes from **bounding work per request**, **keeping nodes interchangeable**, **failing fast instead of piling up**, and **measuring before changing**. The rules below apply to all three stacks. The references hold stack-specific code.

## When to Use

- A new endpoint, job, query or third-party integration that will see real traffic
- A list, export, import or report that will grow with the data
- Deciding whether to add a server, and which one
- Preparing for a launch, a campaign, or a known traffic spike
- Reviewing a diff for load behaviour (`scalability-reviewer` applies this skill)

## How It Works

### 1. Know which level you are at

| Level | Shape | Typical ceiling | Move up when |
|-------|-------|-----------------|--------------|
| **L1** | One VPS, Docker Compose: app, worker, MySQL, Redis, RabbitMQ | tens to low hundreds of rps | CPU > 70% sustained at peak, memory swapping, or p95 above the SLO while the DB is healthy |
| **L2** | Stateful services on their own hosts (MySQL, then Redis + RabbitMQ). App and worker stay together | a few hundred rps | App CPU is the bottleneck, workers starve the app, or one app host is a single point of failure |
| **L3** | 2+ stateless app nodes behind a load balancer, workers on separate nodes, MySQL primary + read replica | high hundreds of rps and beyond | Reads dominate and the primary is saturated, or a deploy must not drop requests |

The ceilings are orders of magnitude only. Measure your own with a load test (`references/observability-load-test.md`). Do not jump levels: fix code-level problems first, because they are cheaper than servers and they follow you to every level.

**L3 prerequisites** (the app must already satisfy these at L1, so moving up is only a config change):
- no local session, cache or uploaded files (`references/horizontal.md`)
- scheduled tasks run once (`onOneServer` / a leader lock)
- config comes from env, and caches are warmed at deploy time
- health endpoint for the load balancer (`/health/live`, `/health/ready`)

### 2. Code-level rules (every level)

1. **Every query is bounded.** Lists paginate with a capped page size. Exports and imports stream (`chunkById`, cursors, batches). Never `->get()` or `findAll()` an unbounded table.
2. **Use keyset pagination for deep or infinite lists** (`WHERE id < :last ORDER BY id DESC LIMIT n`). Offset pagination slows down linearly with page depth.
3. **No N+1.** Eager-load in the repository, and batch lookups by ID (`WHERE id IN (...)`).
4. **Select only the columns you need**, and never load large `TEXT`/JSON columns into list views.
5. **Write in bulk:** use `upsert` / multi-row `INSERT`, in batches of 500 to 1,000 rows. Per-row inserts inside a loop are banned.
6. **Keep the request path short.** Anything slower than about 200 ms that the client does not need right away (email, PDF, webhooks out, image processing, reports) goes to RabbitMQ. Return `202 Accepted` with a status resource when the client needs to poll.
7. **Keep transactions and locks short.** No HTTP calls or queue publishes inside a transaction (use `afterCommit`). Lock rows in a consistent order. Lock rows, not tables.
8. **Avoid exact `COUNT(*)` on big tables in hot paths.** Use an approximate count, a cached counter, or a "has more" flag instead.
9. **Cache reads that are hot and slow-changing** in Redis with a TTL, and let the writer invalidate them. Prevent stampedes with a lock or early refresh on very hot keys.
10. **Fan out through the queue, not in a loop.** Dispatch one batch job that chunks internally, not one job per row from a web request.

Details and code: `references/code-level.md`.

### 3. Horizontal rules (L2 and L3, designed in from L1)

1. **Keep nodes stateless.** Sessions, cache and locks live in Redis. Files go to S3/MinIO (never the local disk). Nothing is kept in process memory across requests unless a stale copy is harmless.
2. **Budget connections.** `app nodes × pool size + workers × pool size + headroom ≤ MySQL max_connections`. Each PHP-FPM child holds its own connection.
3. **Split reads to a replica** only once the primary is the bottleneck. After a write, read your own writes from the primary (Laravel `sticky`, or an explicit primary read).
4. **Scale workers independently of the app**, per queue. Set RabbitMQ prefetch so a slow consumer does not hoard messages.
5. **Run scheduled jobs exactly once:** Laravel `onOneServer()` + `withoutOverlapping()`, and a Redis lock or a single scheduler container for NestJS and Go.
6. **Deploy without dropping requests:** readiness check, drain, graceful shutdown, and migrations that are backwards compatible with the version still running (expand, then contract).

Details and code: `references/horizontal.md`.

### 4. Resilience rules (every level)

1. **Every outbound call has a timeout**, covering HTTP, DB and Redis. The request budget is spent in this order: DB queries, then external calls, then everything else. There is no default "wait forever".
2. **Retry only idempotent operations**, with exponential backoff, jitter and a cap (e.g. 3 tries). Never retry a 4xx.
3. **Put a circuit breaker on flaky dependencies.** After N consecutive failures, fail fast for a cool-down period, then probe.
4. **Rate-limit per user or token and per IP** on the API, with stricter limits on login, OTP, search and exports. Return `429` with `Retry-After`.
5. **Idempotency keys on unsafe retries from clients:** payments, order creation and anything a mobile client may resend. Store the key and the response in Redis for 24h.
6. **Backpressure over collapse:** bounded queues and worker concurrency, RabbitMQ prefetch, and a dead-letter queue. When overloaded, shed low-priority work first.
7. **Degrade gracefully.** If a non-critical dependency (recommendations, analytics) is down, return the core response without it.
8. **Shut down gracefully.** On SIGTERM, stop accepting work, finish in-flight requests and jobs within a deadline, then exit.

Details and code: `references/resilience.md`.

### 5. Measure before and after

1. Define SLOs per endpoint class, for example: reads p95 < 300 ms, writes p95 < 500 ms, error rate < 0.5%.
2. Track the **four golden signals**: latency (p50/p95/p99), traffic (rps), errors (5xx rate), and saturation (CPU, memory, DB connections, queue depth and consumer lag).
3. Keep the MySQL slow query log on (`long_query_time` 0.5–1 s) and `EXPLAIN` every new query on a table that will exceed about 100k rows.
4. Load-test any endpoint that will be hot before launch, and after any change to it. Use k6 with thresholds that match the SLO, against a staging environment sized like production.
5. Do the capacity math: **concurrency = rps × latency** (Little's law). Size PHP-FPM children, Node instances and Go pools from it, then leave 30% headroom.

Details, a k6 script, and sizing formulas: `references/observability-load-test.md`.

## Examples

### Unbounded list → bounded, keyset, cached

```php
// BAD: loads every row, then paginates in PHP
return Order::where('user_id', $userId)->get()->forPage($page, 20);

// GOOD (repository, house style): bounded, indexed (user_id, id), columns selected
return Order::query()
    ->select(['id', 'status', 'total', 'created_at'])
    ->where('user_id', $userId)
    ->when($beforeId, fn ($q) => $q->where('id', '<', $beforeId))
    ->orderByDesc('id')
    ->limit(min($limit, 100))
    ->get();
```

### Slow side effect in the request → queue

```ts
// BAD (NestJS): the client waits for the PDF and the SMTP server
await this.pdf.render(invoice); await this.mailer.send(user, pdf);

// GOOD: publish and return 202; a consumer does the work with retries
await this.queue.publish('invoices.render', { invoiceId: invoice.id });
return { data: { invoiceId: invoice.id, status: 'processing' }, message: 'Queued' };   // interceptor adds meta (api-design)
```

### Outbound call without a deadline → bounded

```go
// BAD: http.DefaultClient has no timeout; one slow partner exhausts every goroutine
resp, err := http.Get(url)

// GOOD: per-call deadline derived from the request context
ctx, cancel := context.WithTimeout(r.Context(), 2*time.Second)
defer cancel()
req, _ := http.NewRequestWithContext(ctx, http.MethodGet, url, nil)
resp, err := client.Do(req) // client has Timeout and a tuned Transport
```

## Checklist for a change that will see load

- [ ] Every query bounded; lists paginated (keyset for deep lists); no N+1; only needed columns
- [ ] New `WHERE`/`ORDER BY` columns indexed (`database-reviewer` for big tables)
- [ ] Slow or non-essential side effects moved to RabbitMQ; no I/O inside transactions
- [ ] No local state: files to object storage; session, cache and locks in Redis
- [ ] Every outbound call has a timeout; retries only on idempotent calls, with backoff and jitter
- [ ] Rate limit on the endpoint; idempotency key where clients may retry writes
- [ ] Metrics and logs make the new path visible (latency, errors, queue depth)
- [ ] Load-tested against the SLO if the endpoint is on a hot path

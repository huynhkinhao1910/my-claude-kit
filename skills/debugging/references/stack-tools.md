# Debugging tools by stack

Use read-only tools first. Anything that changes state (clearing caches, purging queues, killing queries) is an action to confirm, never a diagnostic step.

## Laravel

| Need | Tool |
|------|------|
| Logs for one request | `storage/logs/laravel-*.log`, grep by `request_id` (set by the request-ID middleware, see `api-design`) |
| Log more around a suspect | `Log::debug('orders.place', ['order_id' => $id, 'stock' => $p->stock])`; remove it after |
| See the SQL a query runs | `DB::enableQueryLog(); …; dump(DB::getQueryLog());` in a test, or `->toRawSql()` (Laravel 10.15+) |
| Catch N+1 | `Model::preventLazyLoading(! app()->isProduction())` throws on lazy loads in tests |
| Poke at state | `php artisan tinker` against a local or staging copy. Never run Tinker writes against prod |
| Routes, middleware, config actually loaded | `php artisan route:list --path=api/v1/orders -v`, `php artisan config:show queue` (10+), `php artisan about` |
| Stale config or route cache | `php artisan optimize:clear` locally. On servers, rebuild the caches as part of the deploy, don't clear them ad hoc |
| Step through code | Xdebug (`XDEBUG_MODE=debug`) with the IDE, or `dd()` in a failing test (never commit it) |
| Failing jobs | `php artisan queue:failed`, the `failed_jobs.exception` column; `php artisan queue:retry <id>` only after the fix |
| Scheduler | `php artisan schedule:list`, `php artisan schedule:test` |

## NestJS

| Need | Tool |
|------|------|
| Structured logs | `nestjs-pino` with `req.id`; set `LOG_LEVEL=debug` temporarily |
| Debugger | `node --inspect-brk -r ts-node/register src/main.ts`, or `nest start --debug --watch`, then attach Chrome DevTools or VS Code |
| SQL from TypeORM | `logging: ['query', 'error']` in dev, or `.getQueryAndParameters()` on a query builder |
| Unhandled rejections | run with `--unhandled-rejections=strict` in dev; check that every `async` path is awaited |
| Event loop stalls | `perf_hooks.monitorEventLoopDelay()`, `clinic doctor` / `clinic flame` |
| One spec | `npx jest path/to/file.spec.ts -t "name" --runInBand` (runInBand removes parallelism as a variable) |

## Go

| Need | Tool |
|------|------|
| Data races | `go test -race ./...`; run flaky tests with `-count=50` |
| Debugger | `dlv test ./internal/orders -- -test.run TestPlace`, `dlv debug ./cmd/api` |
| Goroutine leaks and hangs | `curl localhost:6060/debug/pprof/goroutine?debug=2` (import `net/http/pprof` on an internal port) |
| CPU / memory | `go tool pprof …/profile?seconds=30`, `…/heap`; `go test -bench . -benchmem -cpuprofile cpu.out` |
| Context cancellations and timeouts | log `ctx.Err()` at the boundary; `errors.Is(err, context.DeadlineExceeded)` |
| Pool exhaustion | `db.Stats()`: `WaitCount` and `WaitDuration` rising means `SetMaxOpenConns` is too low or connections are leaking (a missing `rows.Close()`) |

## MySQL

```sql
SHOW FULL PROCESSLIST;                                   -- what runs now, and for how long
SELECT * FROM sys.innodb_lock_waits\G                    -- who blocks whom
SHOW ENGINE INNODB STATUS\G                              -- LATEST DETECTED DEADLOCK section
EXPLAIN ANALYZE SELECT ...;                              -- real plan and timings (8.0.18+)
SELECT * FROM performance_schema.events_statements_summary_by_digest ORDER BY SUM_TIMER_WAIT DESC LIMIT 10;
SHOW VARIABLES LIKE 'max_connections'; SHOW STATUS LIKE 'Threads_connected';
```

- A slow query that "sometimes" happens usually means a missing index, or a plan change with the data distribution. Compare `EXPLAIN` on staging and prod-like data.
- Deadlocks come from inconsistent lock order, or from gap locks on non-unique indexes. Read the deadlock section before changing isolation levels.
- `KILL <id>` is an action, not a diagnostic step. Confirm it first.

## Redis

- `redis-cli --latency`, `INFO memory`, `INFO stats` (evictions, keyspace hits and misses)
- `redis-cli --bigkeys` or `--memkeys` for memory hogs
- `SCAN 0 MATCH v1:orders:* COUNT 100` to inspect keys. **Never `KEYS *`** on a shared instance
- `MONITOR` only briefly, on non-prod: it slows the server
- `TTL <key>` and `OBJECT ENCODING <key>` when cache behaviour surprises you

## RabbitMQ

- `rabbitmqctl list_queues name messages messages_unacknowledged consumers`: messages piling up with 0 consumers means the workers are down; many unacked messages mean slow or stuck consumers
- Management UI → queue → *Get messages* (Ack mode: *Nack, requeue*) to inspect a payload without consuming it
- A growing dead-letter queue means consumers keep rejecting. Read one message and match it to the worker log
- A worker seems to run old code → it was not restarted after the deploy (`php artisan queue:restart`, or restart the container)

## Browser (Vue / React)

- DevTools Network tab: the exact request, response, status and timing. Copy it as cURL to reproduce against the API
- The Console for errors and hydration warnings (Nuxt/Next), Vue/React DevTools for component state
- Use `browser-qa` or Playwright (`npx playwright test --debug`, `--trace on`) to reproduce a UI flow deterministically
- CORS or cookie issues (Sanctum SPA): check `SANCTUM_STATEFUL_DOMAINS`, `SESSION_DOMAIN`, `withCredentials`, and whether the `XSRF-TOKEN` cookie was sent

## Docker / VPS

- `docker compose ps`, `docker compose logs -f --since=10m app worker`
- `docker stats` for CPU and memory per container; exit code 137 means OOM-killed
- `docker compose exec app php artisan about` or `env | sort` for the config actually inside the container, not the one you think is deployed

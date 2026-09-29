# Horizontal scaling: L1 → L2 → L3

The target is **any request can hit any node, and any node can die**. Design for it at L1, so each move up is only a config and infrastructure change.

## Topology by level

```
L1  one VPS
    [caddy/nginx] → app ×1 ── mysql
                     worker ─┤ redis
                             └ rabbitmq

L2  stateful services moved out
    VPS-A: [proxy] → app, worker
    VPS-B: mysql            (backups + slow log here)
    VPS-C: redis, rabbitmq  (or managed services)

L3  interchangeable app nodes
    [load balancer] → app-1, app-2, ...   (stateless)
    worker-1..n (separate hosts, scaled per queue)
    mysql primary ── replica (reads)
    redis, rabbitmq
    object storage (S3 / MinIO) for files
```

Move one piece at a time and measure between steps. MySQL usually moves out first, because it competes hardest for RAM and disk I/O.

## Stateless checklist

| Concern | L1 default that breaks at L3 | Use instead |
|---------|------------------------------|-------------|
| Sessions (Sanctum SPA cookie) | `SESSION_DRIVER=file` | `redis` |
| Cache | `file` / in-process memory | `redis` |
| Locks / unique jobs / rate-limit counters | `file` cache | `redis` |
| Uploaded and generated files | `storage/app` local disk | S3 / MinIO (`FILESYSTEM_DISK=s3`), with signed URLs for private files |
| Scheduler | cron on every node | one scheduler, or `onOneServer()` with a Redis cache store |
| WebSocket / SSE state | in-process maps | Redis pub/sub adapter |
| App config | edited files on the server | env vars + `config:cache` at build/deploy |
| Logs | files on the node | stdout → a collector (Loki, ELK, cloud logs) |

**NestJS / Go:** no module-level `Map` caches that must stay consistent across nodes. An in-process cache is fine only for data that tolerates staleness (e.g. 30 s TTL feature flags). Anything shared goes to Redis.

## Reverse proxy / load balancer

- Health checks: `/health/live` means the process is up. `/health/ready` means the DB, Redis and RabbitMQ are reachable. The LB routes only to *ready* nodes.
- Keep-alive to upstreams, sensible timeouts (`proxy_read_timeout` just above the app's own request timeout), and a body size limit.
- Forward `X-Forwarded-For` / `X-Forwarded-Proto`, and trust only the LB's IP (Laravel `TrustProxies`, Nest `app.set('trust proxy', ...)`, Go: read the header only when the peer is the LB). Otherwise rate limits and logs see the LB instead of the client.
- No sticky sessions. If something needs stickiness, it is state that should move to Redis.

## MySQL connection budget

Every connection costs memory on the MySQL server. Budget before you add nodes:

```
total = app_nodes × per_node_connections + worker_nodes × per_worker_connections + admin/cron headroom (~10)
total ≤ max_connections × 0.8
```

| Stack | Per-node connections |
|-------|---------------------|
| Laravel (PHP-FPM) | = `pm.max_children`, because each child holds one connection while it runs a request |
| Laravel queue workers | 1 per `queue:work` process |
| NestJS (TypeORM, mysql2 pool) | `extra.connectionLimit` (e.g. 10–20) × instances (PM2 cluster / containers) |
| Go (`database/sql`) | `SetMaxOpenConns` (e.g. 20–50); also set `SetMaxIdleConns` and `SetConnMaxLifetime` below MySQL `wait_timeout` |

```go
db.SetMaxOpenConns(30)
db.SetMaxIdleConns(10)
db.SetConnMaxLifetime(5 * time.Minute)
db.SetConnMaxIdleTime(2 * time.Minute)
```

When the budget no longer fits, add ProxySQL, or scale reads to a replica before raising `max_connections`.

## Read replicas

Add a replica when the **primary is saturated by reads**. It does not help a write-bound primary.

**Laravel** (`config/database.php`):

```php
'mysql' => [
    'read' => ['host' => [env('DB_READ_HOST')]],
    'write' => ['host' => [env('DB_WRITE_HOST')]],
    'sticky' => true,   // after a write in this request, reads go to the primary
    'driver' => 'mysql',
    // database, username, password, charset... as usual
],
```

- `sticky` covers read-your-writes within one request. Across requests (write, then an immediate redirect or refetch), read from the primary explicitly: `DB::connection('mysql')->useWritePdo()` in the repository, or `Model::query()->useWritePdo()`.
- Queue jobs that act on a row just written should read from the write connection, because replica lag can make the row "missing".
- Watch the replica's `Seconds_Behind_Source`, and alert above a few seconds.

**NestJS (TypeORM):**

```ts
TypeOrmModule.forRoot({
  type: 'mysql',
  replication: {
    master: { host: env.DB_WRITE_HOST, port: 3306, username, password, database },
    slaves: [{ host: env.DB_READ_HOST, port: 3306, username, password, database }],
  },
});
// read-your-writes: run the read in the same QueryRunner / transaction, which uses the master
```

**Go:** keep two `*sql.DB` handles (`primary`, `replica`). Repositories take the one they need explicitly, and anything following a write uses `primary`.

## Workers and RabbitMQ at scale

- Run workers on their own hosts at L3, so a job spike cannot starve HTTP.
- Scale per queue: `mail` ×2, `reports` ×1, `default` ×4. Scale up on queue depth and consumer lag, not CPU.
- Prefetch (`basic.qos`) of 1–10 per consumer. A high prefetch lets one slow worker hoard messages that others could process.
- Keep long jobs on their own queue, with a longer timeout, so they don't block short ones.

## Scheduled tasks run once

- **Laravel:** `$schedule->job(new ExpireOrdersJob)->everyFiveMinutes()->onOneServer()->withoutOverlapping();` The cache store must be Redis, shared by all nodes.
- **NestJS (`@nestjs/schedule`):** every instance runs `@Cron`. Guard it with a Redis lock, `SET lock:expire-orders <id> NX EX 300`, and skip when the lock is not acquired. Or run crons only in a dedicated scheduler container (`ENABLE_CRON=true`).
- **Go:** same approach: a Redis `SET NX EX` lock, or a single scheduler deployment.

## Zero-downtime deploys

1. **Migrations are backwards compatible** with the running version (expand → deploy → contract):
   - add a nullable column or a new table first; backfill in a job; switch the code; drop the old column in a later release
   - never rename or drop a column in the same deploy as the code change
2. **Rolling update:** take a node out of the LB (readiness fails), let it drain, update it, wait for ready, then do the next node.
3. **Graceful shutdown:** on SIGTERM, stop accepting work, then finish in-flight requests and jobs (`references/resilience.md`).
4. **Laravel:** `php artisan config:cache route:cache` at build time. Run `queue:restart` after deploying, so workers load the new code.
5. **Cache keys** carry a version prefix (`v1:`), so a changed payload shape can't be read by old code.

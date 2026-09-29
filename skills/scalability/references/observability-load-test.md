# Measure, load-test, size

Never scale on a hunch. Find the bottleneck with numbers, change one thing, and measure again.

## 1. SLOs per endpoint class

| Class | p95 latency | p99 latency | Error rate (5xx) |
|-------|-------------|-------------|------------------|
| Read (list, detail) | < 300 ms | < 800 ms | < 0.5% |
| Write (create, update) | < 500 ms | < 1.5 s | < 0.5% |
| Auth (login, token) | < 400 ms | < 1 s | < 0.5% |
| Async accept (`202`) | < 200 ms | < 500 ms | < 0.1% |

These are starting points. Agree on the real numbers per product, and write them in the project `CLAUDE.md` or `docs/`.

## 2. Golden signals and where they come from

| Signal | Measure | Source |
|--------|---------|--------|
| Latency | p50 / p95 / p99 per route | access log with `$request_time` / `upstream_response_time`, or app metrics (Prometheus histogram) |
| Traffic | rps per route | proxy log / metrics |
| Errors | 5xx rate, plus the rate of each 4xx family | proxy log, app log with `meta.code` |
| Saturation | CPU, RAM, PHP-FPM active vs `max_children`, DB connections vs `max_connections`, Redis memory, RabbitMQ queue depth and unacked count | node exporter, php-fpm status, `SHOW STATUS`, RabbitMQ management API |

Minimum tooling at L1: Uptime Kuma or a similar uptime check, plus Netdata, or node exporter with Prometheus and Grafana, on the VPS. Keep structured JSON logs (Laravel `daily` + JSON formatter, `nestjs-pino`, Go `slog`) with a request ID.

**Per-stack metrics endpoint**

- **Laravel:** expose PHP-FPM status (`pm.status_path = /fpm-status`, internal only) and the RabbitMQ management metrics. Add a `/health/ready` route that pings the DB, Redis and RabbitMQ with short timeouts.
- **NestJS:** `@willsoto/nestjs-prometheus` or `prom-client` for an HTTP histogram, and `@nestjs/terminus` for health checks.
- **Go:** `prometheus/client_golang` with a histogram middleware, and `/metrics` bound to an internal port.

Keep label cardinality low: route templates (`/api/v1/orders/{id}`), never raw URLs or user IDs.

## 3. MySQL visibility

```sql
-- my.cnf equivalents: slow_query_log=1, long_query_time=0.5, log_queries_not_using_indexes=1 (staging)
SET GLOBAL slow_query_log = 1;
SET GLOBAL long_query_time = 0.5;
```

- Summarise the slow log weekly with `pt-query-digest`, and fix the top 5 by total time, not by single worst.
- `EXPLAIN ANALYZE` every new query on a table that will exceed about 100k rows. Red flags: `type: ALL` (full scan), `Using filesort` / `Using temporary` on a hot path, and `rows` far above what is returned.
- Watch `Threads_connected` against `max_connections`, `Innodb_row_lock_waits`, and replica lag.

## 4. Load testing with k6

Test against **staging sized like production**, with realistic data volume (seed millions of rows when production has millions). Test one scenario at a time.

```js
// load/orders.js — run: k6 run -e BASE_URL=https://staging.example.com -e TOKEN=... load/orders.js
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  scenarios: {
    browse: {
      executor: 'ramping-arrival-rate',   // fixed rps, independent of response time
      startRate: 10,
      timeUnit: '1s',
      preAllocatedVUs: 50,
      maxVUs: 300,
      stages: [
        { target: 50, duration: '2m' },    // warm up
        { target: 200, duration: '5m' },   // expected peak
        { target: 400, duration: '3m' },   // 2x peak: find the knee
        { target: 0, duration: '1m' },
      ],
    },
  },
  thresholds: {
    'http_req_duration{kind:read}': ['p(95)<300', 'p(99)<800'],
    http_req_failed: ['rate<0.005'],
  },
};

const headers = { Authorization: `Bearer ${__ENV.TOKEN}`, Accept: 'application/json' };

export default function () {
  const res = http.get(`${__ENV.BASE_URL}/api/v1/orders?per_page=20`, { headers, tags: { kind: 'read' } });
  check(res, {
    'status 200': (r) => r.status === 200,
    'has data': (r) => r.json('data') !== null,
  });
  sleep(Math.random());
}
```

- Use an **arrival-rate** executor (`ramping-arrival-rate`), so that slow responses show up as queued requests, as with real users. A closed VU loop slows itself down and hides the problem.
- Run **smoke** (1–2 VUs, a correctness check), **load** (expected peak for 10–30 min), **stress** (ramp until the SLO breaks, to find the knee), and **soak** (peak for 1–4 h, to find leaks and pool exhaustion).
- Watch the server-side saturation metrics during the test. The first resource to hit its limit is the bottleneck, and the next change should target it.
- Record the results (rps at the knee, p95, and the bottleneck) in `docs/perf/<date>-<endpoint>.md`, so the next change has a baseline.

## 5. Capacity math

**Little's law:** `concurrency = throughput × latency`.

At 200 rps with an average latency of 150 ms, 30 requests are in flight at any moment.

### PHP-FPM (Laravel)

```
pm.max_children = floor((RAM for PHP) / (avg RSS per child))
```

- Measure the average RSS per child under load: `ps -o rss= -C php-fpm | awk '{s+=$1} END {print s/NR/1024 " MB"}'`, typically 40–80 MB.
- Example: 4 GB reserved for PHP at 60 MB per child gives about 65 children. Check that this is at least `rps × latency × 1.3` (30 in flight × 1.3 = 39, so it fits).
- Use `pm = static` or `dynamic`, with `pm.max_requests = 500` to recycle leaking workers.
- `max_children` is also your MySQL connection count per node (`references/horizontal.md`).

### Node (NestJS)

- One process uses one core for JS. Run `instances = cores` (PM2 cluster or containers), and keep the event loop lag p99 under 50 ms.
- CPU-bound work (PDF, image, crypto, heavy JSON) goes to a worker or the queue, never the request loop.

### Go

- Goroutines are cheap. The limits are the DB pool (`SetMaxOpenConns`), the outbound HTTP pool (`MaxIdleConnsPerHost`), and CPU (`GOMAXPROCS` = container CPUs; Go 1.25+ reads cgroup limits).
- Size the DB pool from the concurrency that actually touches the DB, not from the goroutine count.

### Headroom and the next step

- Plan for **peak × 1.3**, and move to the next level (`SKILL.md` table) when sustained peak utilisation passes about 70% on the bottleneck resource.
- Scale the bottleneck only. More app nodes don't help a saturated primary DB, and a replica doesn't help a write-bound one.

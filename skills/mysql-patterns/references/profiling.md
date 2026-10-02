# Profile, optimize, verify on the web

Use this loop when a page or endpoint is slow, or when someone asks to "tối ưu database", "query chậm" or "trang load lâu". The goal is to start from measured numbers, change one thing at a time and re-measure. Without a before/after number, nothing counts as optimized.

Server-level visibility (slow log, `performance_schema` digests, SLO targets, load tests) lives in `scalability` → `references/observability-load-test.md`. This file covers the per-request loop.

## 0. Is it the database?

A slow page is often not a DB problem: front-end rendering, external APIs, synchronous work and worker saturation are common too. Before this loop, confirm that DB time is the biggest share of the request (at least half of server time), using `debugging` → `references/slow-triage.md`. If it is not, stop and report the breakdown instead of tuning queries.

## Safety

- Run against **local, dev or staging** only. Never point profiling at a production connection unless the user explicitly says so and names the read replica to use.
- `EXPLAIN` is safe. `EXPLAIN ANALYZE` **executes** the statement, so use it on `SELECT` only and expect it to take as long as the query itself.
- `SET GLOBAL ...` changes server config. Do it only on a local or dev DB the user has handed over, and note every change so it can be reverted.
- Browser checks stay read-only. Open pages and read timings, but do not submit forms or click delete, checkout or mass-update buttons.

## 1. Baseline

Pick the target: a URL, an API route or a job. Then record:

| Metric | How |
|--------|-----|
| Response time (TTFB and total) | `curl -s -o /dev/null -w 'ttfb=%{time_starttransfer} total=%{time_total}\n' <url>`, run 5 times, report the median |
| Queries per request | app query log (section 2) |
| Total DB time per request | sum of query durations from the same log |
| Slowest 3 queries | same log, sorted by duration |
| Rows examined vs rows returned | `EXPLAIN ANALYZE` or `performance_schema.events_statements_summary_by_digest` |

Warm the cache with one request first, then measure. Report cold and warm separately when they differ a lot.

## 2. Capture queries per request

**Laravel**

```php
// Temporary, local only. Remove before commit.
DB::listen(function ($q) {
    logger()->debug('sql', ['ms' => $q->time, 'sql' => $q->sql, 'bindings' => $q->bindings]);
});
```

You can also use Telescope (`/telescope/requests` shows query count and duration per request) or Debugbar on local. `Model::preventLazyLoading(! app()->isProduction())` turns hidden N+1 into exceptions.

**NestJS**: TypeORM `logging: ['query', 'error'], maxQueryExecutionTime: 100`, or Prisma `log: [{ emit: 'event', level: 'query' }]` with `e.duration`.

**Go**: wrap the driver (`github.com/qustavo/sqlhooks`, `otelsql`) or log in the repository layer with `time.Since`.

**MySQL side** (MySQL 8+):

```sql
SELECT DIGEST_TEXT, COUNT_STAR, ROUND(SUM_TIMER_WAIT/1e12, 3) AS total_s,
       ROUND(AVG_TIMER_WAIT/1e9, 1) AS avg_ms, SUM_ROWS_EXAMINED, SUM_ROWS_SENT
FROM performance_schema.events_statements_summary_by_digest
ORDER BY SUM_TIMER_WAIT DESC LIMIT 10;
```

Run `TRUNCATE performance_schema.events_statements_summary_by_digest` (local or dev only) before hitting the page, so that the digest shows just that request.

## 3. Read the plan

```sql
EXPLAIN FORMAT=TREE SELECT ...;
EXPLAIN ANALYZE SELECT ...;   -- executes; SELECT only
```

| Signal | Meaning | Usual fix |
|--------|---------|-----------|
| `type: ALL` / `Table scan` on a large table | no usable index | index on the filter columns |
| `rows` examined ≫ rows returned | index not selective, or wrong column order | composite index: equality → range → sort |
| `Using filesort` on a big result | ORDER BY does not follow the index | add the sort column to the end of the composite index |
| `Using temporary` | GROUP BY or DISTINCT on unindexed columns | index the group columns, or pre-aggregate |
| `key: NULL` while an index exists | function on the column, implicit cast, leading `%` | rewrite the predicate (range instead of `DATE(col)`, matching types) |
| Same statement repeated N times | N+1 | eager load (`with`, `withCount`), or `WHERE id IN (...)` |
| `LIMIT 20 OFFSET 100000` | deep offset scans | keyset or cursor pagination |

The index and query rules themselves are in the main `SKILL.md` (Indexing, Query Patterns). Do not restate them in a report; cite them.

## 4. One hypothesis, one change

For each finding, write: *query → evidence (plan line, numbers) → proposed change → expected effect*. Then apply **one** change at a time. In the kit the `implementer` applies it; the reviewer only proposes.

Order the options by cost:

1. Remove the query (N+1 → eager load, duplicate lookups → load once).
2. Shrink it (select only needed columns, bounded `LIMIT`, keyset pagination).
3. Index it (new or reordered composite index; on big tables use `ALGORITHM=INPLACE, LOCK=NONE` or gh-ost, see `database-migrations`).
4. Rewrite it (split an `OR` into a `UNION`, replace correlated subqueries with joins, use a generated column for JSON or expressions).
5. Cache it (Redis with explicit invalidation, see `redis-patterns`). Only do this after 1–4, and never to hide a missing index.

## 5. Re-measure

Repeat section 1 with the same request, data and warm or cold state. Keep a change only if it measurably improves the target metric. Revert it if it only moves the cost (for example a faster read with a much slower write path) and nobody accepted that trade-off.

## 6. Verify on the web

Confirm the improvement where the user feels it, not only in SQL.

**Browser (claude-in-chrome or Playwright MCP)**

1. Open the page in a new tab. Load it once to warm up, then reload.
2. Read the network requests. For each XHR/fetch call to the API, record status, duration, and TTFB where the tool exposes it.
3. Read navigation timing from the page:
   ```js
   (() => { const n = performance.getEntriesByType('navigation')[0];
     return { ttfb: n.responseStart - n.requestStart, dcl: n.domContentLoadedEventEnd, load: n.loadEventEnd }; })()
   ```
4. Read API timings, including `Server-Timing` when the backend sends it:
   ```js
   performance.getEntriesByType('resource')
     .filter(r => ['fetch', 'xmlhttprequest'].includes(r.initiatorType))
     .map(r => ({ url: r.name, ms: Math.round(r.duration), ttfb: Math.round(r.responseStart - r.requestStart), server: r.serverTiming }))
   ```
5. Check for errors: no new 4xx/5xx responses and no new console errors.

**Server-Timing header (optional, recommended)**

Let the backend report DB time per request so that both the browser and curl can see it:

```php
// Laravel middleware, local/staging only
$response->headers->set('Server-Timing', sprintf('db;dur=%.1f;desc="%d queries", app;dur=%.1f',
    $dbMs, $queryCount, (microtime(true) - LARAVEL_START) * 1000));
```

Keep this off in production, or limit it to internal IPs, because it leaks timing information.

**Without a browser**, run the curl loop from section 1 for every API the page calls.

## 7. Report

```markdown
## database-reviewer (profile)

Target: GET /api/v1/orders?status=paid (staging, 120k orders)

| Metric | Before | After | Δ |
|--------|--------|-------|---|
| TTFB (median of 5) | 840 ms | 120 ms | -86% |
| Queries / request | 52 | 3 | -49 |
| DB time / request | 610 ms | 18 ms | -97% |
| Rows examined (main query) | 118,402 | 25 | |

| # | Query / location | Evidence | Change | Status |
|---|------------------|----------|--------|--------|
| 1 | OrderResource → customer (app/Http/Resources/OrderResource.php:21) | 50× same SELECT | `with('customer')` in OrderRepository::paginate | applied, verified |
| 2 | orders WHERE status ORDER BY created_at | type ALL, filesort | `INDEX (status, created_at)` | applied, verified |

Web check: /orders page, API p50 830 → 115 ms, no new 4xx/5xx or console errors.
Not verified: production data distribution (staging has 10% of the rows).
```

Always list what was **not** verified. Never claim an improvement without the before and after numbers.

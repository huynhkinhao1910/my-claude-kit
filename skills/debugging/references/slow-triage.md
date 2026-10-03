# Slow page or endpoint: find where the time goes

"Trang chậm" is a symptom, not a cause. Before optimizing anything, split the time into buckets and look at the biggest one. Most wasted effort comes from tuning the database when the time is spent in the browser, an external API, or a queue that runs synchronously.

## 1. Browser or server?

Open the page in claude-in-chrome, load it once to warm up, then reload and read:

```js
(() => {
  const n = performance.getEntriesByType('navigation')[0];
  const api = performance.getEntriesByType('resource')
    .filter(r => ['fetch', 'xmlhttprequest'].includes(r.initiatorType))
    .map(r => ({ url: r.name, ms: Math.round(r.duration), ttfb: Math.round(r.responseStart - r.requestStart), server: r.serverTiming }));
  return {
    ttfb: Math.round(n.responseStart - n.requestStart),
    download: Math.round(n.responseEnd - n.responseStart),
    domContentLoaded: Math.round(n.domContentLoadedEventEnd),
    load: Math.round(n.loadEventEnd),
    api,
  };
})()
```

Cross-origin API (SPA on :3000, API on :8000): `ttfb` reads 0 and `server` is empty unless the API sends `Timing-Allow-Origin`. `ms` is always correct; use it, or add the header (`mysql-patterns` → `references/profiling.md` §6).

| What dominates | Bucket | Go to |
|----------------|--------|-------|
| Document TTFB or one API's TTFB is high | **server** | section 2 |
| TTFB is fine, but `domContentLoaded`/`load` is late, or LCP/INP is bad | **front end**: bundle size, render, hydration, images, fonts | `react-performance`, `vue-patterns`, `nuxt4-patterns`, `browser-qa` (Core Web Vitals) |
| Many API calls in sequence (a waterfall), each one fast | **front end**: request chaining | batch the calls, or parallelize them, or move them to an aggregate endpoint |
| `download` is large | **payload** too big | paginate, select fewer fields, compress (gzip/brotli) |
| Slow only for the first request after idle | **cold start**: opcache, connection setup, cache miss | warm-up, persistent connections, cache |

## 2. Inside the server request

Time one request end to end and split it. Either add a temporary `Server-Timing` header with one entry per bucket, or log `microtime`/`performance.now()`/`time.Since` at each boundary.

| Bucket | How to measure | Typical cause | Go to |
|--------|----------------|---------------|-------|
| **DB** | sum of query durations, query count (Telescope, `DB::listen`, ORM logging) | N+1, missing index, deep offset, big scans | `database-reviewer` mode `profile` (`mysql-patterns` → `references/profiling.md`) |
| **External HTTP** | wrap the client, log the duration per call | slow third party, no timeout, calls in a loop | `scalability` (timeouts, retries, circuit breaker, queue offload) |
| **Cache / Redis** | client timing, hit and miss counters | cache misses, huge values, `KEYS *` | `redis-patterns` |
| **Synchronous work** | timing around the mail, PDF, image or report step | work that belongs in a queue | `scalability` → queue offload |
| **App CPU** | profiler: Xdebug/SPX/Blackfire (PHP), `--cpu-prof` / clinic (Node), `pprof` (Go) | serialization of big collections, loops, regex, heavy Resources | `debugging` → `stack-tools.md` |
| **Waiting for a worker** | PHP-FPM status `listen queue`, Node event-loop lag, Go goroutine count | saturation under load, not a slow request | `scalability-reviewer` |
| **Lock wait** | `SHOW ENGINE INNODB STATUS`, `performance_schema.data_lock_waits` | long transactions, hot rows | `database-reviewer` (locking) |

## 3. Decide

- One bucket holds **≥ 50%** of the time: that is the target. Hand it to the matching skill or agent above.
- No bucket dominates: fix the largest one first, and re-measure after every change.
- The time cannot be accounted for (the buckets sum to much less than the total): add more boundaries until it can. Do not guess.

Write the breakdown down before any fix:

```
Target:   GET /orders (staging), TTFB 1.9 s (median of 5)
Buckets:  DB 220 ms (14 queries) · external HTTP 1.4 s (shipping API ×3, sequential) · app 180 ms · other 100 ms
Decision: not a DB problem. Move the shipping API calls to a cached background refresh (scalability).
```

---
name: debugging
description: >-
  Systematic debugging for Laravel, NestJS, Go and Vue/React apps on MySQL, Redis and RabbitMQ: reproduce, narrow
  down, form one hypothesis at a time, prove the root cause with evidence, then fix with a regression test. Includes
  the stack tools for logs, queries, locks, queues, profiling and the browser. Use when something fails, errors,
  hangs, is slow, is flaky, or behaves differently than expected, including "lỗi", "bug", "không chạy", "chạy sai",
  "test fail", "500", "timeout", or before proposing any fix whose cause is not yet proven. Do NOT use for build or type
  errors with an obvious message (use /build-fix) or for designing new features.
origin: My Claude Kit
---

# Debugging

**No fix without a proven root cause.** A change that makes a symptom disappear without explaining it is a guess, and guesses create the next bug. The goal is a one-sentence cause backed by evidence, then the smallest fix, then a test that would have caught it.

## When to Use

- An error, exception, a 5xx or a wrong result
- A hang, timeout, a slow endpoint or a stuck queue
- A flaky test, or "works locally, fails on staging"
- Before `/quick` or `implementer` touch code when the cause is unknown

## How It Works

### 1. Reproduce

- Get the **exact** failing input: the request (method, URL, body, headers, user), the command, or the job payload. Also the environment (local, staging, prod), the time, and the `request_id`.
- Reproduce it with the cheapest tool that shows the failure: a failing test (best), then `curl`/HTTPie, then Tinker or a REPL.
- Can't reproduce it? That is information. Compare the environments: config, env vars, data, versions, the queue driver, the cache state, the time zone, and concurrency.
- **Flaky:** run the test 20–50× (`--repeat`, `-count=50`). Record what differs between the passes and the failures: order, time, shared state or parallelism.

### 2. Read the evidence before theorising

- Read the whole error, the stack trace and the log line around the `request_id`. The first frame in *your* code is usually where to look.
- Check what changed recently: `git log -p --since=... -- <area>`, deploys, migrations, config, and dependency bumps (`composer.lock` / `package-lock.json` / `go.sum` diff).
- For a regression with a known good commit, run `git bisect run <test command>`.

### 3. Narrow down

- Split the path in half: the request, then validation, service, repository, DB, and the response. Which half is wrong? Log or assert at the boundary, and repeat.
- **Slow page or endpoint:** split the time into buckets first (browser vs server, then DB, external HTTP, cache, sync work, CPU, worker wait) with `references/slow-triage.md`. Optimize only the bucket that dominates; send DB-bound cases to `database-reviewer` in `profile` mode.
- Shrink the input to the smallest case that still fails.
- Remove variables one at a time: cache off, queue `sync`, a single worker, a fresh DB state, one tenant/user.

### 4. One hypothesis at a time

Write it as: *"X fails because Y, which means that if I do Z, I will observe W."* Then do Z.
- The prediction held: move on to confirming the fix.
- It didn't: **discard the hypothesis**, and don't stack a second change on top of the first. Revert any exploratory edits before the next hypothesis.
- After 3 failed hypotheses, stop and re-read the evidence, or widen the scope: the bug is probably somewhere you have not looked yet.

### 5. Prove the root cause

The cause is proven when you can **turn the failure on and off** by changing only that one thing, or explain every observed symptom from it. Write it down:

```
Symptom:     POST /api/v1/orders returns 500 for ~2% of requests at peak
Evidence:    log request_id=... shows "Deadlock found when trying to get lock"; SHOW ENGINE INNODB STATUS lists orders + products rows locked in opposite order
Root cause:  OrderService locks orders before products; RefundService locks products before orders
Fix:         lock in a single order (products, then orders) in both services
Regression:  test runs place() and refund() concurrently and asserts no deadlock / both succeed
```

### 6. Fix and guard

- Write the regression test **first**: it must fail before the fix and pass after.
- Make the smallest fix that addresses the root cause, not the symptom. No `try/catch` that swallows the error, no retry that hides it, no `sleep`.
- Search for the same pattern elsewhere (`Grep`) and list the other occurrences. Fixing them is a separate, approved change.
- Remove every debugging leftover: `dd()`, `dump()`, `console.log`, `fmt.Println`, temporary log levels, `->toSql()` echoes.

### Anti-patterns

| Don't | Instead |
|-------|---------|
| Change several things, then see if it works | One change per hypothesis, reverted if wrong |
| Add a `try/catch`, a retry or a null check to make the error go away | Find out why the value is null or the call fails |
| "Probably a cache issue" and clear the caches | Prove it: reproduce with the cache off and on |
| Fix it in prod data by hand and move on | Fix the code path, then repair the data with a reviewed script |
| Blame the framework or the library first | Assume your code until the evidence says otherwise, then check the issue tracker and the changelog |

## Examples

Stack-specific tools (logs, SQL, locks, queues, Redis, profiling, the browser) are in `references/stack-tools.md`. The most used ones:

```bash
# Laravel: follow logs for one request
tail -f storage/logs/laravel-$(date +%F).log | grep <request_id>
# Laravel: run one test in isolation, stop on the first failure
php artisan test --filter=StoreOrderTest --stop-on-failure

# MySQL: what is running and what is waiting right now
SHOW FULL PROCESSLIST;
SELECT * FROM sys.innodb_lock_waits\G

# Go: data races and a CPU profile
go test -race -count=20 ./internal/orders/...
go tool pprof http://localhost:6060/debug/pprof/profile?seconds=30

# NestJS: attach the debugger
node --inspect-brk -r ts-node/register src/main.ts
```

## Output

When reporting a debugging result, always give: **Symptom → Evidence → Root cause → Fix → Regression test**, as in step 5. If the root cause is not proven yet, say so, and list the next experiment instead of proposing a fix.

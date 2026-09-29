# Code-level scalability

These rules cut the work each request does. They are the cheapest fixes, so apply them before adding servers.

## 1. Bounded lists and keyset pagination

Offset pagination (`LIMIT 20 OFFSET 200000`) makes MySQL read and throw away 200,000 rows. Use offset pagination only for shallow admin lists that show page numbers. Use a keyset (cursor) for feeds, infinite scroll, exports and any list that grows without bound.

Index the keyset columns together with the filter: `INDEX (user_id, id)` for `WHERE user_id = ? AND id < ? ORDER BY id DESC`.

**Laravel (repository)**

```php
public function feedForUser(int $userId, ?int $beforeId, int $limit): Collection
{
    return Order::query()
        ->select(['id', 'status', 'total', 'created_at'])
        ->where('user_id', $userId)
        ->when($beforeId, fn (Builder $q, int $id) => $q->where('id', '<', $id))
        ->orderByDesc('id')
        ->limit(min($limit, 100) + 1)          // one extra row tells us whether there is a next page
        ->get();
}
```

The service trims the extra row and returns `meta.next_cursor` = the last `id` (or `null`). `cursorPaginate()` is also fine when its opaque cursor suits the client.

**NestJS (TypeORM)**

```ts
async feedForUser(userId: number, beforeId: number | undefined, limit: number) {
  const qb = this.orders
    .createQueryBuilder('o')
    .select(['o.id', 'o.status', 'o.total', 'o.createdAt'])
    .where('o.userId = :userId', { userId })
    .orderBy('o.id', 'DESC')
    .take(Math.min(limit, 100) + 1);
  if (beforeId) qb.andWhere('o.id < :beforeId', { beforeId });
  return qb.getMany();
}
```

**Go (database/sql)**

```go
func (r *OrderRepo) FeedForUser(ctx context.Context, userID int64, beforeID *int64, limit int) ([]Order, error) {
	if limit > 100 {
		limit = 100
	}
	q := `SELECT id, status, total, created_at FROM orders WHERE user_id = ?`
	args := []any{userID}
	if beforeID != nil {
		q += ` AND id < ?`
		args = append(args, *beforeID)
	}
	q += ` ORDER BY id DESC LIMIT ?`
	args = append(args, limit+1)

	rows, err := r.db.QueryContext(ctx, q, args...)
	if err != nil {
		return nil, fmt.Errorf("feed for user %d: %w", userID, err)
	}
	defer rows.Close()

	out := make([]Order, 0, limit+1)
	for rows.Next() {
		var o Order
		if err := rows.Scan(&o.ID, &o.Status, &o.Total, &o.CreatedAt); err != nil {
			return nil, err
		}
		out = append(out, o)
	}
	return out, rows.Err()
}
```

## 2. N+1 and batched lookups

- **Laravel:** eager-load in the repository with `->with('product:id,name,price')`. In development, turn on `Model::preventLazyLoading(! app()->isProduction())` in `AppServiceProvider::boot()`, so N+1 throws during tests.
- **NestJS/TypeORM:** use `leftJoinAndSelect` or `relations` in the query builder. Never `await` a relation inside a `for` loop.
- **Go:** collect the IDs, run one `WHERE id IN (?, ?, ...)` query, then build a map by ID. Don't query inside a loop.

```go
// one query for all products referenced by the orders
ids := make([]any, 0, len(orders))
for _, o := range orders { ids = append(ids, o.ProductID) }
q := `SELECT id, name, price FROM products WHERE id IN (` + placeholders(len(ids)) + `)`
```

## 3. Streaming large reads (exports, backfills)

**Laravel:** `chunkById` is safe while you update rows. `lazyById` gives a memory-flat iterator.

```php
Order::query()->where('status', 'pending')->chunkById(1000, function (Collection $orders) {
    $this->orders->markExpired($orders->pluck('id')->all());
});
```

- Never use `chunk()` (offset-based) when the loop changes the filtered column, because it skips rows.
- For an export, stream to a file in object storage from a job and hand the client a signed URL. Don't build a 100k-row CSV in a web request.

**NestJS:** page by ID in a loop (`WHERE id > :last ORDER BY id LIMIT 1000`), or use `.stream()` on the query builder for the mysql2 driver.

**Go:** iterate `rows.Next()` and write each row straight to the encoder or writer. Don't collect everything into a slice first.

## 4. Bulk writes

| Stack | Bulk insert / upsert |
|-------|----------------------|
| Laravel | `Model::query()->upsert($rows, ['unique_key'], ['col_a', 'col_b'])`, or `insert($rows)`, in chunks of 500–1000 |
| NestJS | `repo.createQueryBuilder().insert().values(rows).orUpdate(['col_a'], ['unique_key']).execute()` |
| Go | one multi-row `INSERT ... VALUES (?,?),(?,?) ... ON DUPLICATE KEY UPDATE col_a = VALUES(col_a)` per batch, inside one transaction |

- Bulk writes bypass model events and observers. When those matter, dispatch one batch event after the write.
- Keep each batch's transaction short, and commit per batch instead of across the whole import.

## 5. Short transactions, careful locks

- Inside a transaction only DB work happens: no HTTP, no RabbitMQ publish, no `sleep`. Publish after commit (Laravel `afterCommit()`, or the outbox pattern for NestJS and Go).
- Lock rows with `SELECT ... FOR UPDATE` through the repository, only on the rows you will change, and **always in the same order** (for example, ascending ID) to avoid deadlocks.
- Retry once on a deadlock (MySQL 1213) for idempotent units of work. Laravel's `DB::transaction($fn, 3)` retries deadlocks.
- A counter on a hot row (likes, stock) becomes a lock hotspot. Update it atomically (`UPDATE ... SET stock = stock - ? WHERE id = ? AND stock >= ?`), or aggregate in Redis and flush periodically.

## 6. Cheap counts and existence checks

- Use `exists()` / `SELECT 1 ... LIMIT 1` instead of `count() > 0`.
- On large lists, drop `total`: return `has_more` from the extra keyset row.
- For dashboards, use counters maintained on write, or a summary table refreshed by a job.

## 7. Caching reads

```php
// Laravel service: cache a hot, slow-changing read; the writer calls Cache::forget on change
$categories = Cache::remember('v1:categories:all', now()->addHour(), fn () => $this->categories->allActive());
```

```ts
// NestJS: ioredis with a stampede guard (only one caller rebuilds)
const cached = await this.redis.get(key);
if (cached) return JSON.parse(cached);
const gotLock = await this.redis.set(`${key}:lock`, '1', 'EX', 10, 'NX');
if (!gotLock) { await sleep(50); return this.getCategories(); }   // someone else is rebuilding
const fresh = await this.repo.allActive();
await this.redis.set(key, JSON.stringify(fresh), 'EX', 3600);
await this.redis.del(`${key}:lock`);
return fresh;
```

- Cache what is **read often and changes rarely**: config, catalogs, permissions, aggregates.
- Don't cache per-user data with a low hit rate.
- Always set a TTL, and let the writer invalidate the key.
- Cache values are plain data, never ORM entities or models.

## 8. Offloading to RabbitMQ

- Offload anything that is slow (over about 200 ms), talks to a third party, or produces a file: mail, SMS, push, PDF, image resize, webhooks out, reports, search indexing.
- The endpoint validates, writes the minimal record, publishes after commit, and returns `201`, or `202` with a status resource.
- Fan out from a single job: the web request dispatches one `ExpireOrdersJob`, which chunks internally, instead of 10,000 jobs in a loop.
- Every consumer is idempotent, because RabbitMQ is at-least-once (`laravel-patterns/references/rabbitmq-queues.md`).

## 9. Payload and response size

- Return only the fields the client uses, and use a separate detail endpoint for heavy fields.
- Enable gzip/brotli at the reverse proxy.
- Cap request bodies at the proxy (for example, 10 MB) and in validation. Uploads go straight to object storage through a signed URL, not through PHP or Node.

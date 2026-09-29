# Queues on RabbitMQ, cache on Redis

Background jobs run on RabbitMQ through `vladimir-yuldashev/laravel-queue-rabbitmq`. Redis serves cache and locks. Check the package README for the exact config keys of the installed version; the rules below do not depend on the version.

## Setup

```bash
composer require vladimir-yuldashev/laravel-queue-rabbitmq
```

```dotenv
QUEUE_CONNECTION=rabbitmq
RABBITMQ_HOST=rabbitmq
RABBITMQ_PORT=5672
RABBITMQ_USER=app
RABBITMQ_PASSWORD=
RABBITMQ_VHOST=/
RABBITMQ_QUEUE=default

CACHE_DRIVER=redis        # CACHE_STORE on Laravel 11+
REDIS_HOST=redis
```

- Add the `rabbitmq` connection to `config/queue.php` as the package README shows.
- Secrets stay in `.env` and the secret store. Never commit them in `config/*`.
- Use one queue per workload with distinct latency needs: `default`, `mail`, `reports`. Don't create one queue per job class.

## Dead-lettering

Configure dead-lettering on the broker, not in PHP. Messages that are rejected or have expired then land somewhere you can inspect:

```bash
rabbitmqctl set_policy DLX "^(default|mail|reports)$" \
  '{"dead-letter-exchange":"dlx"}' --apply-to queues
```

Laravel's own `failed_jobs` table still records jobs that exhausted `$tries`. Keep it (`php artisan queue:failed-table` on older versions), and treat it as the first place to look.

## Workers

```bash
php artisan queue:work rabbitmq --queue=default,mail --tries=3 --backoff=10 --timeout=90 --max-jobs=1000 --max-time=3600
```

- Run the workers under Supervisor or a separate container (`worker` service in Compose), never as a web-server background process.
- `--max-jobs` / `--max-time` recycle workers so memory leaks don't accumulate.
- Workers keep the code in memory, so every deploy must run `php artisan queue:restart`.
- `--timeout` must stay below the broker/consumer timeout. The job's `$timeout` must be less than or equal to the worker's `--timeout`.

## Job template

```php
<?php

namespace App\Jobs;

use App\Repositories\OrderRepository;
use App\Services\OrderMailer;
use Illuminate\Bus\Queueable;
use Illuminate\Contracts\Queue\ShouldQueue;
use Illuminate\Foundation\Bus\Dispatchable;
use Illuminate\Queue\InteractsWithQueue;
use Illuminate\Support\Facades\Log;
use Throwable;

final class SendOrderConfirmation implements ShouldQueue
{
    use Dispatchable, InteractsWithQueue, Queueable;

    public int $tries = 5;
    public array $backoff = [10, 60, 300];   // seconds between attempts
    public int $timeout = 60;

    public function __construct(public readonly int $orderId)
    {
        $this->onQueue('mail');
    }

    public function handle(OrderRepository $orders, OrderMailer $mailer): void
    {
        $order = $orders->findOrNull($this->orderId);

        // Idempotent: a redelivered message must not send a second email.
        if ($order === null || $order->confirmation_sent_at !== null) {
            return;
        }

        $mailer->sendConfirmation($order);
        $orders->markConfirmationSent($order);
    }

    public function failed(Throwable $e): void
    {
        Log::error('SendOrderConfirmation failed', ['order_id' => $this->orderId, 'error' => $e->getMessage()]);
    }
}
```

Rules:
- **Pass IDs, not models.** The model may have changed or been deleted by the time the job runs.
- **Make the job idempotent.** RabbitMQ delivers *at least once*, so check a state flag or use a unique key before any side effect.
- **Dispatch after commit.** Inside `DB::transaction` call `Job::dispatch($id)->afterCommit()`. Otherwise a worker can pick the job up before the row exists.
- **Prevent duplicates** when the same job can be dispatched twice: implement `ShouldBeUnique`. The lock lives in Redis, so set `uniqueFor`.
- **No business logic in `handle()`.** Load through a repository and call a service, just as a controller would.
- **Cross-service messages** consumed by non-Laravel services must not use Laravel jobs, because the payload is PHP-serialized. Publish plain JSON to a dedicated exchange and document the schema.

## Redis cache

```php
$summary = Cache::remember(
    "v1:orders:user:{$userId}:summary",
    now()->addMinutes(10),
    fn () => $this->orders->summaryForUser($userId),
);
```

- Key format: `v1:<resource>:<scope>:<id>[:<variant>]`. Bump `v1` when the cached shape changes.
- Always set a TTL, and never use `rememberForever` for data that users change.
- The service that writes the data invalidates the related keys right after the write, or after commit when the write happens inside a transaction.
- Cache values are arrays or scalars built by the repository or service, not Eloquent models.
- Use `Cache::lock("v1:lock:order:{$id}", 10)` for cross-process mutual exclusion. Use `lockForUpdate()` for row-level consistency inside a transaction.

## Tests

```php
Queue::fake();
// ... call the endpoint ...
Queue::assertPushedOn('mail', SendOrderConfirmation::class, fn ($job) => $job->orderId === $order->id);
```

`Queue::fake()` never touches RabbitMQ. Test `handle()` itself by calling it directly with real repositories and a faked mailer (see `laravel-tdd`).

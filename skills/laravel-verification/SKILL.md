---
name: laravel-verification
description: "Pre-PR and pre-deploy verification for Laravel APIs in the house style: env and Composer checks, Pint, PHPUnit on the MySQL test database with coverage, composer audit, migration review, cache warmup, and RabbitMQ worker and scheduler checks. Use before opening a PR, after a large refactor or dependency upgrade, or before deploying. Do NOT use for writing tests (laravel-tdd) or non-Laravel projects."
origin: My Claude Kit
---

# Laravel Verification Loop

Run before PRs, after major changes, and pre-deploy.

## When to Use

- Before opening a pull request for a Laravel project
- After major refactors or dependency upgrades
- Pre-deployment verification for staging or production
- Running full lint -> test -> security -> deploy readiness pipeline

## How It Works

- Run phases sequentially from environment checks through deployment readiness so each layer builds on the last.
- Environment and Composer checks gate everything else; stop immediately if they fail.
- Linting/static analysis should be clean before running full tests and coverage.
- Security and migration reviews happen after tests so you verify behavior before data or release steps.
- Build/deploy readiness and queue/scheduler checks are final gates; any failure blocks release.

## Phase 1: Environment Checks

```bash
php -v
composer --version
php artisan --version
```

- Verify `.env` is present and required keys exist
- Confirm `APP_DEBUG=false` for production environments
- Confirm `APP_ENV` matches the target deployment (`production`, `staging`)

If using Laravel Sail locally:

```bash
./vendor/bin/sail php -v
./vendor/bin/sail artisan --version
```

## Phase 1.5: Composer and Autoload

```bash
composer validate
composer dump-autoload -o
```

## Phase 2: Formatting

```bash
vendor/bin/pint --test          # gate: must pass
vendor/bin/pint --dirty         # fix only the files you changed
```

Pint is the house formatter. Run PHPStan/Larastan only when the project already ships a `phpstan.neon`, and never add it as part of an unrelated change.

## Phase 3: Tests and Coverage

```bash
php artisan test
```

Coverage (CI):

```bash
XDEBUG_MODE=coverage php artisan test --coverage
```

CI example (format -> tests):

```bash
vendor/bin/pint --test
XDEBUG_MODE=coverage php artisan test --coverage --min=80
```

Tests run against the MySQL test database from `phpunit.xml` (see `laravel-tdd`), never SQLite.

## Phase 4: Security and Dependency Checks

```bash
composer audit
```

## Phase 5: Database and Migrations

```bash
php artisan migrate --pretend
php artisan migrate:status
```

- Review destructive migrations carefully
- Ensure migration filenames follow `Y_m_d_His_*` (e.g., `2025_03_14_154210_create_orders_table.php`) and describe the change clearly
- Ensure rollbacks are possible
- Verify `down()` methods and avoid irreversible data loss without explicit backups

## Phase 6: Build and Deployment Readiness

```bash
php artisan optimize:clear
php artisan config:cache
php artisan route:cache
php artisan view:cache
```

- Ensure cache warmups succeed in production configuration
- Verify queue workers and scheduler are configured
- Confirm `storage/` and `bootstrap/cache/` are writable in the target environment

## Phase 7: Queue and Scheduler Checks

```bash
php artisan schedule:list
php artisan queue:failed
php artisan queue:restart        # after every deploy: RabbitMQ workers keep old code in memory
```

If Horizon is used:

```bash
php artisan horizon:status
```

If `queue:monitor` is available, use it to check backlog without processing jobs:

```bash
php artisan queue:monitor default --max=100
```

Active verification (staging only): dispatch a no-op job to a dedicated queue and run a single worker to process it (ensure a non-`sync` queue connection is configured).

```bash
php artisan tinker --execute="dispatch((new App\\Jobs\\QueueHealthcheck())->onQueue('healthcheck'))"
php artisan queue:work --once --queue=healthcheck
```

Verify the job produced the expected side effect (log entry, healthcheck table row, or metric).

Only run this on non-production environments where processing a test job is safe.

## Examples

Minimal flow:

```bash
php -v
composer --version
php artisan --version
composer validate
vendor/bin/pint --test
php artisan test
composer audit
php artisan migrate --pretend
php artisan config:cache
php artisan queue:failed
```

CI-style pipeline:

```bash
composer validate
composer dump-autoload -o
vendor/bin/pint --test
XDEBUG_MODE=coverage php artisan test --coverage --min=80
composer audit
php artisan migrate --pretend
php artisan optimize:clear
php artisan config:cache
php artisan route:cache
php artisan view:cache
php artisan schedule:list
```

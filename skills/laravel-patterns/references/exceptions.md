# Central exception rendering

All API errors leave the app through one place and always use the envelope from `App\Support\ApiResponse`. Controllers never `try/catch` just to reshape an error.

## Laravel 10: `app/Exceptions/Handler.php`

```php
<?php

namespace App\Exceptions;

use App\Support\ApiResponse;
use Illuminate\Auth\Access\AuthorizationException;
use Illuminate\Auth\AuthenticationException;
use Illuminate\Database\Eloquent\ModelNotFoundException;
use Illuminate\Foundation\Exceptions\Handler as ExceptionHandler;
use Illuminate\Http\Request;
use Illuminate\Validation\ValidationException;
use Symfony\Component\HttpKernel\Exception\AccessDeniedHttpException;
use Symfony\Component\HttpKernel\Exception\HttpExceptionInterface;
use Symfony\Component\HttpKernel\Exception\NotFoundHttpException;
use Throwable;

class Handler extends ExceptionHandler
{
    /** Expected business outcomes are not errors worth reporting. */
    protected $dontReport = [
        BusinessException::class,
    ];

    protected $dontFlash = ['current_password', 'password', 'password_confirmation'];

    public function register(): void
    {
        $this->renderable(function (Throwable $e, Request $request) {
            if (! $request->is('api/*')) {
                return null; // non-API routes keep Laravel's default rendering
            }

            return self::toApiResponse($e);
        });
    }

    public static function toApiResponse(Throwable $e): \Illuminate\Http\JsonResponse
    {
        return match (true) {
            $e instanceof ValidationException => ApiResponse::error('Validation failed', 422, $e->errors()),
            $e instanceof AuthenticationException => ApiResponse::error('Unauthenticated', 401),
            $e instanceof AuthorizationException,
            $e instanceof AccessDeniedHttpException => ApiResponse::error('Forbidden', 403),
            $e instanceof ModelNotFoundException,
            $e instanceof NotFoundHttpException => ApiResponse::error('Not found', 404),
            $e instanceof BusinessException => ApiResponse::error($e->getMessage(), $e->status(), $e->errors()),
            $e instanceof HttpExceptionInterface => ApiResponse::error($e->getMessage() ?: 'Request failed', $e->getStatusCode()),
            default => ApiResponse::error(config('app.debug') ? $e->getMessage() : 'Server error', 500),
        };
    }
}
```

Why both `ModelNotFoundException` and `NotFoundHttpException`: Laravel converts model-not-found (and authorization failures) into Symfony HTTP exceptions before `renderable` callbacks run, so the callback receives the converted type. Listing both keeps the mapping correct across versions.

## Laravel 11+: `bootstrap/app.php`

```php
// bootstrap/app.php: add the imports at the top and the withExceptions() call to the Application::configure() chain
use App\Exceptions\BusinessException;
use App\Exceptions\ApiErrors; // holds the same toApiResponse() shown above
use Illuminate\Foundation\Configuration\Exceptions;
use Illuminate\Http\Request;

->withExceptions(function (Exceptions $exceptions) {
    $exceptions->dontReport([BusinessException::class]);

    $exceptions->render(function (Throwable $e, Request $request) {
        return $request->is('api/*') ? ApiErrors::toApiResponse($e) : null;
    });
})
```

On Laravel 11+ there is no `Handler` class by default. Put `toApiResponse()` in `App\Exceptions\ApiErrors` and call it from `bootstrap/app.php`.

## Rules

- Throw `BusinessException` for expected business failures such as out-of-stock, invalid state transitions or quota limits. Choose the status deliberately: 409 for state conflicts, 422 for rule violations, 403 for "not allowed in this state".
- Never put stack traces, SQL or exception class names in `message` unless `app.debug` is on.
- 500s are still reported to the log/Sentry. Only `BusinessException` is in `dontReport`.
- Catching inside a service is fine only to translate a third-party exception into a `BusinessException`. Keep the original as `$previous`.

```php
try {
    $this->payments->charge($order);
} catch (PaymentGatewayException $e) {
    throw new BusinessException('Payment was declined', 402, null, $e);
}
```

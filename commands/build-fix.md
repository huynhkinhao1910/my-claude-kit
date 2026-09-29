---
description: Detect the stack, run the build/type/lint step that is failing, and fix it with the matching resolver agent using minimal diffs and no behavior change
argument-hint: "[path or error text]"
---

Input: $ARGUMENTS

1. **Detect the stack and run the failing step.** Capture the output, and trim it to the error lines.

| Marker | Run | Resolver |
|---|---|---|
| `artisan` + `composer.json` | `composer dump-autoload` → `php -l <changed>` → `vendor/bin/pint --test` → PHPStan (if `phpstan.neon`) | `build-error-resolver` |
| `nest-cli.json` or `@nestjs/core` | `npx tsc --noEmit -p tsconfig.json` → `npm run build` → `npm run lint` | `build-error-resolver` |
| `vite.config.*` / `nuxt.config.*` with Vue | `npx vue-tsc --noEmit` (if present) → `npm run build` | `build-error-resolver` |
| React / Next (`next.config.*`, `*.tsx`) | `npx tsc --noEmit` → `npm run build` | `react-build-resolver` |
| `go.mod` | `go build ./...` → `go vet ./...` → `golangci-lint run` (if present) | `go-build-resolver` |

2. **Delegate** the error output and the file list to the resolver. It fixes one root cause at a time and reruns the step.
3. **Guardrails** (tell the resolver):
   - no behaviour changes, and no new dependencies without asking
   - no `@ts-ignore`, `any`, `//nolint`, `@phpstan-ignore` or disabled rules just to go green
   - stop after 3 rounds without progress
   - failing **tests** are not build errors: hand those to `implementer`
4. **Report**: `Step | Before | After`, the files changed, and anything left unresolved.

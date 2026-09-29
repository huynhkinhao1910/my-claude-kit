# My Claude Kit

My Claude Kit is a personal Claude Code kit for a PHP/Laravel, Go, TypeScript/NestJS, MySQL and Redis backend stack with a Vue/Nuxt/React/Next front end, plus the `/feature` delivery pipeline and continuous learning (instincts learned per project). Extracted from the ECC install in `~/.claude` (already partly customized) so the kit can evolve independently of upstream ECC.

## Install

```bash
./install.sh --dry-run       # preview files, retired rules and the resulting settings.json hooks/deny rules
./install.sh                 # install into ~/.claude, register hooks and deny rules
./install.sh --no-hooks      # copy files only, leave settings.json untouched
./install.sh --no-claude-md  # keep this machine's own ~/.claude/CLAUDE.md
```

Any existing file is backed up to `~/.claude/.backup/my-claude-kit-<timestamp>/` before it is overwritten. `settings.json` is backed up to `settings.json.bak-<timestamp>` whenever hooks change. Restart Claude Code after installing.

Requirements: `bash`, `git`, `python3` and **`jq`**. Without `jq`, `guard.sh` cannot block anything, and the installer warns about it. The background observer also needs the `claude` CLI.

### Safety layer

| Piece | Installed to | What it does |
|-------|--------------|--------------|
| `hooks/guard.sh` | `~/.claude/hooks/my-claude-kit/` (PreToolUse) | Blocks reading or editing `.env*` and credential files, including via the shell; blocks destructive DB commands unless `--env=testing`, force pushes, direct pushes to `main`/`master`/`develop`, hard resets to them, and `rm -rf` of root, home or cwd |
| `hooks/post-edit-format.sh` | same (PostToolUse) | Formats the edited file with the project's own Pint, ESLint, gofmt or ruff. It never blocks |
| `settings/permissions.json` | merged into `permissions.deny` | Denies `Read`/`Edit` on `.env`, `.env.local`, `.env.production`, `.env.staging`, plus `php artisan db:wipe` |
| `claude/CLAUDE.md` | `~/.claude/CLAUDE.md` (backed up first) | Global instructions: the caveman output style, and when to switch to full prose |

- Existing `guard.sh`/`post-edit-format.sh` entries that point straight at `~/.claude/hooks/` are replaced by the kit copies, so they don't run twice.
- The user's own allow and deny rules are kept. `merge-settings.py --remove` removes kit hooks only, and leaves permissions alone.
- Because `guard.sh` blocks direct pushes to `main`, Claude cannot push this kit repo for you. Push it yourself with `! git push`.
- `claude/CLAUDE.md` mentions the `graphify` skill, which is not part of the kit. On a machine without it, drop that section or install graphify separately.

| Env | Default | Meaning |
|-----|---------|---------|
| `CLAUDE_DIR` | `~/.claude` | Target config dir |
| `RULES_NS` | `my-claude-kit` | Rules subfolder (`~/.claude/rules/<ns>/`) |
| `LEGACY_RULES_NS` | `ecc .` | Old namespaces, space-separated, where `.` is the flat `rules/` root. Any rule dir the kit owns that is found there is moved to the backup so it does not load twice. Dirs the kit does not own (e.g. `angular`, `python`) are left alone |
| `RETIRE_DUPLICATES` | `zh README.md` | Extra entries retired from the old namespaces: `zh` is a Chinese copy of `common`, and the `README.md` files are ECC install notes that Claude loads as rules. Set it to an empty string to keep them |

## Naming

The kit is branded **My Claude Kit**. Some `ECC` names stay on purpose, because the code reads them by name:

- `ECC_*` env vars (`ECC_INSTINCT_CONFIDENCE_THRESHOLD`, `ECC_SKIP_OBSERVE`, …) and the `~/.local/share/ecc-homunculus` data dir. The continuous-learning scripts read these, and renaming them would break learning and orphan the instincts already stored.
- `upstream/`, which holds the original ECC files for diffing.
- Origin notes such as "from ECC". These record where a file came from and are not branding.

## Contents

Origin legend: **own** = not in ECC, **custom** = modified from ECC, **ecc** = identical to ECC.

### Pipeline (`/feature`)

`/feature` runs spec → plan → implement → verify → review → ship.

| Command | Agents used | Origin |
|---------|-------------|--------|
| `/feature` | orchestrates the phases below | own |
| `/spec` | requirement-analyst | own |
| `/plan` | code-explorer, planner | custom |
| `/implement` | test-writer, implementer, commit-message-writer | own |
| `/verify` | build-error-resolver, implementer | own |
| `/review` | laravel-reviewer, database-reviewer, security-reviewer, scalability-reviewer, silent-failure-hunter, spec-verifier, go-reviewer, typescript-reviewer, python-reviewer, code-reviewer | own |
| `/ship` | doc-writer | own |

### Agents (23)

| Agent | Origin |
|-------|--------|
| requirement-analyst, test-writer, implementer, spec-verifier, commit-message-writer, doc-writer, laravel-reviewer | own |
| planner, code-explorer, code-reviewer, build-error-resolver, security-reviewer, silent-failure-hunter, database-reviewer, go-reviewer, go-build-resolver, typescript-reviewer, python-reviewer | custom |
| e2e-runner | ecc (description rewritten to the standard) |
| vue-reviewer, react-reviewer, react-build-resolver | ecc (description rewritten to the standard) |
| scalability-reviewer | own |

`/review` routes by file type: `*.vue` goes to `vue-reviewer`, `*.tsx`/`*.jsx` to `react-reviewer`, and plain `*.ts`/`*.js` (for example NestJS) to `typescript-reviewer`. `e2e-runner` is referenced by `rules/typescript/testing.md`.

### Laravel house style

The Laravel skills and `laravel-reviewer` encode one set of decisions instead of listing alternatives:

| Topic | Convention |
|-------|------------|
| App type | REST API for SPA/mobile clients |
| Layers | FormRequest → Controller → Service → Repository (concrete class, no interface) → Model |
| Service input | `$request->validated()` array |
| Responses | Per `api-design`: an existing project keeps its format; a new project uses `{data, paging (lists), meta}` with errors as `data: null` + `meta.message/code/errors` |
| Errors | `BusinessException` + central handler; no `try/catch` in controllers |
| Routes | `/api/v1`, controllers in `Api\V1` |
| Auth | Sanctum: SPA cookie or personal access token |
| Queue / cache | RabbitMQ (`vladimir-yuldashev/laravel-queue-rabbitmq`) / Redis |
| Tests | PHPUnit on a MySQL test database, envelope assertions, real repositories |
| Formatting | Pint |
| Git | `main` only, `feature/*` branches, merged through an MR |

`laravel-reviewer` treats any break of a layer or API-format rule as MAJOR. A project can override a single rule in its own `CLAUDE.md`.

### Scalability

`skills/scalability` covers the path from one Docker Compose VPS (L1), to stateful services on their own hosts (L2), to several stateless app nodes behind a load balancer with a MySQL read replica (L3). `SKILL.md` holds the level table and the rules. `references/` holds the code for Laravel, NestJS and Go:

| Reference | Covers |
|-----------|--------|
| `code-level.md` | keyset pagination, N+1, streaming, bulk writes, short transactions, cheap counts, caching, queue offload |
| `horizontal.md` | stateless checklist, load balancer, MySQL connection budget, read replicas, workers, run-once schedulers, zero-downtime deploys |
| `resilience.md` | timeouts, retries with jitter, circuit breakers, rate limits, idempotency keys, backpressure, graceful shutdown |
| `observability-load-test.md` | SLOs, golden signals, the MySQL slow log, a k6 script, capacity math (Little's law, PHP-FPM, Node, Go) |

`/review` calls `scalability-reviewer` only when a diff touches queries, jobs, list or export endpoints, outbound HTTP clients or infra config. Each finding must name the load at which the code breaks and the resource it exhausts.

### Continuous learning

Full guide (Vietnamese): [docs/continuous-learning.md](docs/continuous-learning.md).

| Piece | What it does | Origin |
|-------|--------------|--------|
| `skills/continuous-learning-v2` | `observe.sh` records tool calls per project; the Haiku observer turns them into instincts | ecc |
| `hooks/inject-instincts.py` | SessionStart hook: injects instincts with confidence ≥ 0.5 (max 10, project first) | own |
| `scripts/merge-settings.py` | Registers or removes (`--remove`) the kit hooks in `settings.json` and leaves the user's own hooks alone | own |
| `/instinct-status`, `/instinct-export`, `/instinct-import`, `/evolve`, `/promote`, `/projects`, `/prune` | Manage instincts | custom (paths point to `~/.claude/skills`) |

The observer is **off by default**. To turn it on, set `observer.enabled: true` in `~/.local/share/ecc-homunculus/config.json` (not in the skill's own `config.json`, which a reinstall overwrites). To stop recording and injection entirely, create `~/.local/share/ecc-homunculus/disabled`.

### Language commands

| Command | Origin |
|---------|--------|
| `/go-build`, `/go-test` | custom |
| `/go-review` | ecc |
| `/vue-review`, `/react-review`, `/react-build`, `/react-test` | ecc |

### Skills (38)

- Laravel: `laravel-patterns`, `laravel-security`, `laravel-tdd`, `laravel-verification`, `laravel-plugin-discovery`
- Go: `golang-patterns`, `golang-testing`
- API contract: `api-design` (own). It detects and follows an existing project's format, and gives new projects `data` + `paging` + `meta`
- TypeScript/Node: `nestjs-patterns` (ecc), `e2e-testing`
- Data: `mysql-patterns`, `redis-patterns` (ecc)
- Front end, Vue: `vue-patterns`, `nuxt4-patterns`, `ui-to-vue`
- Front end, React: `react-patterns`, `react-performance`, `react-testing`, `nextjs-turbopack`
- Front end, shared: `vite-patterns`, `frontend-patterns` (custom), `frontend-a11y`, `accessibility`
- Design and motion: `frontend-design-direction` (custom), `design-system`, `motion-foundations`, `motion-patterns`, `motion-advanced`
- Browser QA: `browser-qa` (works with `e2e-testing` and `e2e-runner`)
- Pipeline support: `review-checklist`, `feature-spec`, `feature-docs`, `gitlab-mr` (own, from `~/claude-audit/fixed`), `database-migrations` (custom), `tdd-workflow`, `verification-loop` (ecc)
- Learning: `continuous-learning-v2` (ecc)
- Scalability: `scalability` (own), see below

Unmarked skills in the lists above are either identical to ECC (the front-end ones) or modified from ECC (the backend ones). `golang-patterns` uses the `~/claude-audit/fixed` version, because the version installed in `~/.claude` has invalid YAML frontmatter.

### Rules

`rules/common`, `rules/php`, `rules/golang`, `rules/typescript`, `rules/web` (custom), `rules/vue`, `rules/nuxt`, `rules/react`. The language rules link to `../common/`, so they all install into the same namespace.

Only `rules/common` loads in every session, about 17k chars. Every other rule dir has `paths:` frontmatter and loads only when matching files are in play, so `rules/web` loads only for Vue, React, CSS, Blade and `resources/js` work. The `common` rules reference only agents that ship in the kit, and model routing follows `AGENT_STANDARD.md`.

## Standard and lint

Every agent, skill and command follows [AGENT_STANDARD.md](AGENT_STANDARD.md). `lint.py` enforces the standard and fails on missing skills or agents, broken frontmatter, and read-only agents that hold write tools.

```bash
python3 lint.py .          # lint the kit
python3 lint.py ~/.claude  # lint an installed config
```

## Tests

```bash
python3 -m unittest discover -s tests
```

This runs the full suite: `inject-instincts.py`, `merge-settings.py` (hooks, legacy replacement, deny merge), `guard.sh` (what it blocks and what it allows), `install.sh` (rules namespace, retiring legacy rules, `CLAUDE.md`), and a check that the kit passes `lint.py` with 0 errors.

## upstream/

This folder holds the original ECC versions of the files above, including `rules/typescript`, plus `php-reviewer.md`, which ECC ships in place of `laravel-reviewer`. It is kept for reference only and is never installed. Compare a file against its ECC original with:

```bash
diff upstream/agents/go-reviewer.md agents/go-reviewer.md
```

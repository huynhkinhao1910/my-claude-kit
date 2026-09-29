# My Claude Kit

My Claude Kit is a personal Claude Code kit for a PHP/Laravel, Go, TypeScript/NestJS, MySQL and Redis backend stack with a Vue/Nuxt/React/Next front end, plus the `/feature` delivery pipeline and continuous learning (instincts learned per project). Extracted from the ECC install in `~/.claude` (already partly customized) so the kit can evolve independently of upstream ECC.

## Install

```bash
./install.sh --dry-run   # preview files and the resulting settings.json hooks
./install.sh             # install into ~/.claude and register hooks
./install.sh --no-hooks  # copy files only, leave settings.json untouched
```

Any existing file is backed up to `~/.claude/.backup/my-claude-kit-<timestamp>/` before it is overwritten. `settings.json` is backed up to `settings.json.bak-<timestamp>` whenever hooks change. Restart Claude Code after installing.

Requirements: `bash`, `git`, `python3`. The background observer also needs the `claude` CLI.

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
| `/review` | laravel-reviewer, database-reviewer, security-reviewer, silent-failure-hunter, spec-verifier, go-reviewer, typescript-reviewer, python-reviewer, code-reviewer | own |
| `/ship` | doc-writer | own |

### Agents (22)

| Agent | Origin |
|-------|--------|
| requirement-analyst, test-writer, implementer, spec-verifier, commit-message-writer, doc-writer, laravel-reviewer | own |
| planner, code-explorer, code-reviewer, build-error-resolver, security-reviewer, silent-failure-hunter, database-reviewer, go-reviewer, go-build-resolver, typescript-reviewer, python-reviewer | custom |
| e2e-runner | ecc (description rewritten to the standard) |
| vue-reviewer, react-reviewer, react-build-resolver | ecc (description rewritten to the standard) |

`/review` routes by file type: `*.vue` goes to `vue-reviewer`, `*.tsx`/`*.jsx` to `react-reviewer`, and plain `*.ts`/`*.js` (for example NestJS) to `typescript-reviewer`. `e2e-runner` is referenced by `rules/typescript/testing.md`.

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
- TypeScript/Node: `nestjs-patterns` (ecc), `backend-patterns`, `api-design`, `e2e-testing`
- Data: `mysql-patterns`, `redis-patterns` (ecc)
- Front end, Vue: `vue-patterns`, `nuxt4-patterns`, `ui-to-vue`
- Front end, React: `react-patterns`, `react-performance`, `react-testing`, `nextjs-turbopack`
- Front end, shared: `vite-patterns`, `frontend-patterns` (custom), `frontend-a11y`, `accessibility`
- Design and motion: `frontend-design-direction` (custom), `design-system`, `motion-foundations`, `motion-patterns`, `motion-advanced`
- Browser QA: `browser-qa` (works with `e2e-testing` and `e2e-runner`)
- Pipeline support: `review-checklist`, `feature-spec`, `feature-docs`, `gitlab-mr` (own, from `~/claude-audit/fixed`), `database-migrations` (custom), `tdd-workflow`, `verification-loop` (ecc)
- Learning: `continuous-learning-v2` (ecc)

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

This runs 31 tests: `inject-instincts.py`, `merge-settings.py`, `install.sh` (rules namespace and retiring the legacy namespace), and a check that the kit passes `lint.py` with 0 errors.

## upstream/

This folder holds the original ECC versions of the files above, including `rules/typescript`, plus `php-reviewer.md`, which ECC ships in place of `laravel-reviewer`. It is kept for reference only and is never installed. Compare a file against its ECC original with:

```bash
diff upstream/agents/go-reviewer.md agents/go-reviewer.md
```

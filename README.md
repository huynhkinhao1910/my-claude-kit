# my-claude-kit

Personal Claude Code kit for a PHP/Laravel, Go, TypeScript/NestJS, MySQL and Redis stack, plus the `/feature` delivery pipeline and continuous learning (instincts learned per project). Extracted from the ECC install in `~/.claude` (already partly customized) so the kit can evolve independently of upstream ECC.

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
| `RULES_NS` | `ecc` | Rules subfolder (`~/.claude/rules/<ns>/`) |

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

### Agents (19)

| Agent | Origin |
|-------|--------|
| requirement-analyst, test-writer, implementer, spec-verifier, commit-message-writer, doc-writer, laravel-reviewer | own |
| planner, code-explorer, code-reviewer, build-error-resolver, security-reviewer, silent-failure-hunter, database-reviewer, go-reviewer, go-build-resolver, typescript-reviewer, python-reviewer | custom |
| e2e-runner | ecc |

`typescript-reviewer` and `python-reviewer` are kept because `/review` routes to them by file type (for example, Vue or NestJS files). `e2e-runner` is referenced by `rules/typescript/testing.md`.

### Continuous learning

Full guide (Vietnamese): [docs/continuous-learning.md](docs/continuous-learning.md).

| Piece | What it does | Origin |
|-------|--------------|--------|
| `skills/continuous-learning-v2` | `observe.sh` records tool calls per project; the Haiku observer turns them into instincts | ecc |
| `hooks/inject-instincts.py` | SessionStart hook: injects instincts with confidence ≥ 0.5 (max 10, project first) | own |
| `scripts/merge-settings.py` | Registers or removes (`--remove`) the kit hooks in `settings.json` and leaves the user's own hooks alone | own |
| `/instinct-status`, `/instinct-export`, `/instinct-import`, `/evolve`, `/promote`, `/projects`, `/prune` | Manage instincts | custom (paths point to `~/.claude/skills`) |

The observer is **off by default**. To turn it on, set `observer.enabled: true` in `~/.local/share/ecc-homunculus/config.json` (not in the skill's own `config.json`, which a reinstall overwrites). To stop recording and injection entirely, create `~/.local/share/ecc-homunculus/disabled`.

### Go commands

| Command | Origin |
|---------|--------|
| `/go-build`, `/go-test` | custom |
| `/go-review` | ecc |

### Skills (14)

- Laravel: `laravel-patterns`, `laravel-security`, `laravel-tdd`, `laravel-verification`, `laravel-plugin-discovery`
- Go: `golang-patterns`, `golang-testing`
- TypeScript/Node: `nestjs-patterns` (ecc), `backend-patterns`, `api-design`, `e2e-testing`
- Data: `mysql-patterns`, `redis-patterns` (ecc)
- Process: `tdd-workflow` (referenced by pipeline agents)

### Rules

`rules/common`, `rules/php`, `rules/golang`, `rules/typescript`. The language rules link to `../common/`, so they all install into the same namespace.

## Tests

```bash
python3 -m unittest discover -s tests
```

This runs 22 tests covering `inject-instincts.py` and `merge-settings.py`.

## upstream/

This folder holds the original ECC versions of the files above, including `rules/typescript`, plus `php-reviewer.md`, which ECC ships in place of `laravel-reviewer`. It is kept for reference only and is never installed. Compare a file against its ECC original with:

```bash
diff upstream/agents/go-reviewer.md agents/go-reviewer.md
```

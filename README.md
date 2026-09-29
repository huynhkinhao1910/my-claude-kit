# my-claude-kit

Personal Claude Code kit for a PHP/Laravel, Go and MySQL stack, plus the `/feature` delivery pipeline. Extracted from the ECC install in `~/.claude` (already partly customized) so the kit can evolve independently of upstream ECC.

## Install

```bash
./install.sh --dry-run   # preview
./install.sh             # install into ~/.claude
```

Any existing file is backed up to `~/.claude/.backup/my-claude-kit-<timestamp>/` before it is overwritten.

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

### Agents (18)

| Agent | Origin |
|-------|--------|
| requirement-analyst, test-writer, implementer, spec-verifier, commit-message-writer, doc-writer, laravel-reviewer | own |
| planner, code-explorer, code-reviewer, build-error-resolver, security-reviewer, silent-failure-hunter, database-reviewer, go-reviewer, go-build-resolver, typescript-reviewer, python-reviewer | custom |

`typescript-reviewer` and `python-reviewer` are kept because `/review` routes to them by file type (for example, Vue files).

### Go commands

| Command | Origin |
|---------|--------|
| `/go-build`, `/go-test` | custom |
| `/go-review` | ecc |

### Skills (9)

- Laravel: `laravel-patterns`, `laravel-security`, `laravel-tdd`, `laravel-verification`, `laravel-plugin-discovery`
- Go: `golang-patterns`, `golang-testing`
- Data: `mysql-patterns`
- Process: `tdd-workflow` (referenced by pipeline agents)

### Rules

`rules/common`, `rules/php`, `rules/golang`. The php and golang rules link to `../common/`, so all three install into the same namespace.

## upstream/

This folder holds the original ECC versions of the files above, plus `php-reviewer.md`, which ECC ships in place of `laravel-reviewer`. It is kept for reference only and is never installed. Compare a file against its ECC original with:

```bash
diff upstream/agents/go-reviewer.md agents/go-reviewer.md
```

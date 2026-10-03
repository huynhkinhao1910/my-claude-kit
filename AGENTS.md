# AGENTS.md

Instructions for agents working on **my-claude-kit** itself: the agents, skills, commands, rules and hooks that `install.sh` copies into Claude Code, Codex and GitHub Copilot. User docs live in `README.md` (Vietnamese), and the authoring rules for agents, skills and commands live in `AGENT_STANDARD.md`. This file covers what neither of them says.

## Source and twins

The Claude Code format is the source of truth: `agents/`, `skills/`, `commands/`, `rules/`, `hooks/`, `settings/`, `claude/CLAUDE.md`. Every other target is a hand-maintained twin. Change a twin in the same commit as its source.

| Source | Twin | Transform |
|---|---|---|
| `agents/<name>.md` | `codex/agents/<name>.toml` | Copy `description`. Add `sandbox_mode = "read-only"` when the agent has no `Write`/`Edit`. `developer_instructions` = `Load these skills first: <skills>`, a blank line, then the body verbatim. |
| `agents/<name>.md` | `copilot/agents/<name>.agent.md` | Frontmatter `name`, `description` and `tools`, mapped Read→`read`, Write/Edit→`edit`, Bash→`execute`, Grep/Glob→`search` (MCP tools are dropped). Then the same `Load these skills first` line and the body verbatim. |
| `commands/<name>.md` | `dotagents/skills/<name>/SKILL.md` | Frontmatter `name` + `description`, then `Input: <argument-hint>`, with `$ARGUMENTS` replaced by `the user's request`. The rest is verbatim. Commands in `OUT_OF_SCOPE` (`tests/test_targets.py`) have no twin. |
| `rules/<dir>/<rule>.md` | `codex/my-claude-kit/rules/<dir>/<rule>.md` | Same text. |
| `rules/<dir>/<rule>.md` | `copilot/instructions/<dir>-<rule>.instructions.md` | Same text under an `applyTo` frontmatter. |
| `claude/CLAUDE.md` | `codex/AGENTS.md` | Same intent, at most 32 KB. |

Skills in `skills/` are shared by every target and have no twin. `upstream/` holds the original open-source files for diffing. It is not installed, so do not edit it except when syncing from upstream.

## When you add or change something

- **Agent**: add it to the roster in `AGENT_STANDARD.md` and `rules/common/agents.md` (plus that rule's twins), and to the README §6 table and count.
- **Skill**: add it to the README §7 table, and bump the count in both the heading and the table-of-contents anchor.
- **Command**: create the `dotagents` twin, and add it to the README §5 table and count.
- **Install scope**: `groups.txt` lists the stack-only items. Anything not listed there is core and gets installed with every `--only`. An agent or skill that a core command always delegates to (`e2e-runner`, `database-reviewer`, …) must be core. Stack routing stays in groups: `/review` and `/build-fix` pick a stack reviewer or resolver only when that stack is installed.
- **Always-loaded text**: agent and skill `description`s and every `rules/**/*.md` file load into every session. Keep them short, and move detail into `references/*.md`.

## Checks

```bash
npm test                 # python unittest (lint, twin parity, install, guard, …) + node CLI tests
python3 lint.py .        # lint this repo; with no argument it lints ~/.claude instead
./install.sh --dry-run
```

Commit only with 0 lint errors and green tests. Use Conventional Commits (`feat:`, `fix:`, `docs:`, …).

## Gotchas

- The installed `guard.sh` hook blocks any Bash command whose text contains destructive DB keywords. That includes heredocs that only edit Markdown mentioning those keywords. Write such edits to a script file in the scratchpad, then run the file.
- Language: `README.md` and feature docs are in Vietnamese (technical terms stay in English). Agent, skill, command and rule files are in English.
- Keep the `ECC_*` names and `ecc-homunculus` paths as they are (README §14): the continuous-learning engine reads them.

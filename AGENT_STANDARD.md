# Agent & Skill Definition Standard

Every agent, skill and command in `~/.claude` must pass these rules. `lint.py` checks them automatically.

## Agents (`agents/<name>.md`)

```yaml
---
name: kebab-case, identical to the file name
description: <What it does, 1 sentence>. Use when <concrete triggers>. Do NOT use for <out-of-scope> (use <other-agent>).
tools: [least privilege list — never omit; omitting grants ALL tools incl. MCP]
model: opus | sonnet | haiku
skills: comma-separated skills to preload (must exist)
---
```
Rules:
1. `description` ≤ 400 chars, no examples, no newlines. It is loaded into EVERY session; examples belong in the body.
2. Must contain a positive trigger ("Use when…") AND a negative scope ("Do NOT use for…").
3. "PROACTIVELY" only for agents that are cheap and safe to auto-run (read-only reviewers). Never on agents that write code.
4. Reviewers, verifiers, explorers, planners: NO `Write`/`Edit`. They report; the main session or `implementer` changes code. (Planners/analysts may `Write` only their own doc under `docs/`.)
5. Body sections in this order: Role → Inputs → Process → Output (exact contract) → Never.
6. Output contract is a fixed format the orchestrator can merge (table or fixed headings). Subagents return summaries, not full files.
7. Model routing: `opus` for ambiguity/judgment (requirements, planning, architecture, security, Laravel correctness review); `sonnet` for pattern-following work (implementation, tests, language review, docs); `haiku` for mechanical work.
8. Body ≤ 250 lines. Shared checklists live in a skill, not copied into each agent.
9. Every referenced skill/agent/MCP tool must exist.

## Skills (`skills/<name>/SKILL.md`)
1. `name` = folder name; `description` ≤ 1024 chars, valid YAML (quote or use `>-` when it contains `: `).
2. Description says when to use AND when not to.
3. SKILL.md ≤ 500 lines; move detail into `references/*.md` and link it (progressive disclosure).
4. Knowledge/procedure only — no persona. Personas are agents.

## Commands (`commands/<name>.md`)
1. `description` + `argument-hint` when it takes `$ARGUMENTS`.
2. Commands that change code or push must contain an explicit STOP / approval gate.
3. Every agent / skill / MCP tool referenced must exist; otherwise archive the command.

## Hooks & settings
1. Hooks are registered in `settings.json` → `hooks` (files in `hooks/` do nothing on their own).
2. `permissions.deny` blocks secrets and destructive commands; `guard.sh` is the second line of defense.
3. `enableAllProjectMcpServers` = false: approve project MCP servers one by one.

## Pipeline roster
| Phase | Agent | Model | Writes code? |
|---|---|---|---|
| Spec | requirement-analyst | opus | docs only |
| Explore | code-explorer | sonnet | no |
| Plan | planner (feature plan) / architect (system decisions, ADR) | opus | docs only |
| Implement | test-writer → implementer | sonnet | yes |
| Fix build | build-error-resolver, go-build-resolver | sonnet | yes |
| Review | laravel-reviewer, typescript-reviewer, go-reviewer, python-reviewer, code-reviewer (fallback), security-reviewer, database-reviewer, silent-failure-hunter | opus/sonnet | no |
| Verify | spec-verifier | sonnet | no |
| Ship | doc-writer, commit-message-writer | sonnet | docs only |
| Maintenance | refactor-cleaner | sonnet | yes |

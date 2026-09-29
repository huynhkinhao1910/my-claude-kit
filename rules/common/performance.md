# Performance Optimization

## Model Selection Strategy

Agent frontmatter uses the aliases `opus`, `sonnet` and `haiku`, which resolve to the current model in each tier (Opus 5.5, Sonnet 5, Haiku 4.5). Route by the kind of work, as `AGENT_STANDARD.md` defines:

| Alias | Use for | Kit agents |
|-------|---------|------------|
| `opus` | Ambiguity and judgment: requirements, planning, architecture, security, Laravel correctness review | requirement-analyst, planner, laravel-reviewer, security-reviewer |
| `sonnet` | Pattern-following work: implementation, tests, language review, docs | implementer, test-writer, go/typescript/vue/react reviewers, doc-writer |
| `haiku` | Mechanical, high-frequency work | commit-message-writer, continuous-learning observer |

Pick the cheapest tier that does the job well, and move up a tier only when the output is wrong, not just slow.

## Context Window Management

Avoid last 20% of context window for:

- Large-scale refactoring
- Feature implementation spanning multiple files
- Debugging complex interactions

Lower context sensitivity tasks:

- Single-file edits
- Independent utility creation
- Documentation updates
- Simple bug fixes

## Extended Thinking + Plan Mode

For complex tasks that need deep reasoning:

1. Start in **Plan Mode** and agree on the approach before editing files
2. Run several critique rounds on the plan
3. Use split-role subagents for independent perspectives (for example laravel-reviewer + security-reviewer + database-reviewer)

## Build Troubleshooting

If build fails:

1. Use the matching build resolver: **build-error-resolver** (PHP, TS, Vue, Python), **go-build-resolver** or **react-build-resolver**
2. Analyze error messages
3. Fix incrementally
4. Verify after each fix

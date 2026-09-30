# Development Workflow

> This file extends [common/git-workflow.md](./git-workflow.md) with the full feature development process that happens before git operations.

The Feature Implementation Workflow describes the development pipeline: research, planning, TDD, code review, and then committing to git.

## Feature Implementation Workflow

0. **Research & Reuse** _(mandatory before any new implementation)_
   - **Search the codebase first:** reuse existing services, helpers and components before adding new ones (`code-explorer` maps an unfamiliar area).
   - **Library docs second:** Use Context7 or primary vendor docs to confirm API behavior, package usage, and version-specific details before implementing.
   - **Check package registries:** Search Packagist, npm and Go modules before writing utility code. Prefer battle-tested libraries over hand-rolled solutions.
   - **Search for adaptable implementations:** Look for open-source projects that solve 80%+ of the problem and can be forked, ported, or wrapped.
   - Prefer adopting or porting a proven approach over writing net-new code when it meets the requirement.

1. **Plan First**
   - `/spec` turns the requirement into `docs/features/<slug>/spec.md` (requirement-analyst)
   - `/plan` turns the approved spec into `docs/features/<slug>/plan.md` with tasks T1..Tn (planner)
   - Identify dependencies and risks
   - Break down into phases

2. **TDD Approach**
   - `/implement`: **test-writer** writes tests first (RED), **implementer** makes them pass
   - Write tests first (RED)
   - Implement to pass tests (GREEN)
   - Refactor (IMPROVE)
   - Verify 80%+ coverage

3. **Code Review**
   - `/review` runs the reviewers for the changed file types in parallel
   - Address CRITICAL and HIGH issues
   - Fix MEDIUM issues when possible

4. **Commit & Push**
   - Detailed commit messages
   - Follow conventional commits format
   - See [git-workflow.md](./git-workflow.md) for commit message format and PR process

5. **Pre-Review Checks**
   - Verify all automated checks (CI/CD) are passing
   - Resolve any merge conflicts
   - Ensure branch is up to date with target branch
   - Only request review after these checks pass

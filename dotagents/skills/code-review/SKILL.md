---
name: "code-review"
description: "Quick read-only review of local changes (uncommitted, or branch vs base) routed to the kit's reviewers; findings inline, no review.md, nothing changed"
---

Input: "[base-branch] (omit to review uncommitted changes)"

Input: the user's request

1. **Scope.**
   - No argument: `git diff --name-only HEAD` plus untracked files (`git ls-files --others --exclude-standard`).
   - With a base: `git diff --name-only <base>...HEAD`.
   - Empty scope → say so and stop.
2. **Pick reviewers** with the same routing table as `/review` step 1: language reviewers by extension, plus `database-reviewer`, `security-reviewer` and `scalability-reviewer` by what the diff touches. Always add `silent-failure-hunter` when error handling changed.
3. **Launch them in parallel** (one message, several Agent calls). Pass the scope (the base, or "uncommitted"), and tell each one to review only those files.
4. **Merge** with `review-checklist` (dedupe, sort by severity), and re-check every BLOCKER/MAJOR line yourself before showing it.
5. **Output**:
   - the merged table: `# | Sev | File:Line | Issue | Failure scenario | Fix | Found by`
   - `Result: X BLOCKER · Y MAJOR · Z MINOR · W NIT`
   - one line: `ready to commit` or `fix BLOCKER/MAJOR first`

Read-only: never edit, stage or commit. To apply fixes, use `/quick fix #n …` or the `implementer`.

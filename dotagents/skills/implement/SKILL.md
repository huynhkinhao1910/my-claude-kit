---
name: "implement"
description: "Phase 3 — implement plan tasks with TDD (test-writer → implementer per task), one commit per task"
---

Input: <slug> [T1,T2,... | all]

Input: the user's request (slug, then task IDs; default = all pending tasks in plan.md)

Require Gate 2 ticked in STATUS.md. For each task in order:
1. `test-writer` (slug, Tn) → confirm tests fail for the right reason.
2. `implementer` (slug, Tn, test paths).
3. Blocked/deviation reported → **STOP** and ask me.
4. `commit-message-writer` on the staged task files → commit with that message.
5. Print one line: `Tn ✅ files — tests X/Y`.

Rules:
- Parallelize only tasks with no dependency AND disjoint files; else sequential.
- Keep your context lean: rely on subagent summaries and STATUS.md, don't read full diffs.
- After the last task run `/verify the user's request`.

---
description: Full feature pipeline — spec → plan → implement (TDD) → verify → review → ship, with human gates and resume support
argument-hint: <slug> <requirement text | file | URL>
---

You are the orchestrator. Delegate; do not write feature code yourself.

Pipeline for: $ARGUMENTS

| Phase | Follow | Gate |
|---|---|---|
| 1 Spec | `/spec` | Gate 1 — I approve spec |
| 2 Plan | `/plan` | Gate 2 — I approve plan |
| 3 Implement | `/implement` | stop on deviation |
| 4 Verify | `/verify` | must be green |
| 5 Review | `/review` | Gate 3 — I approve |
| 6 Ship | `/ship` | Final gate |

Rules:
- Resume: if `docs/features/<slug>/STATUS.md` exists, continue from its phase.
- Update STATUS.md at every transition. All handoffs go through files in `docs/features/<slug>/`.
- Status updates to me: 1–2 lines per step.
- Never skip a gate, even if I seem away.

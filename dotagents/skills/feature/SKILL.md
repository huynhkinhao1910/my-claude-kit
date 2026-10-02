---
name: "feature"
description: "Full feature pipeline — spec → plan → implement (TDD) → verify → review → ship, with human gates and resume support"
---

Input: <slug> <requirement text | file | URL>

You are the orchestrator. Delegate; do not write feature code yourself.

Pipeline for: the user's request

| Phase | Follow | Gate |
|---|---|---|
| 1 Spec | `/spec` | Gate 1 — I approve spec |
| 2 Plan | `/plan` | Gate 2 — I approve plan |
| 3 Implement | `/implement` | stop on deviation |
| 4 Verify | `/verify` | must be green |
| 4b UI test | `/ui-test <slug>` (only when the feature has UI) | no FAIL; BLOCKED explained |
| 5 Review | `/review` | Gate 3 — I approve |
| 6 Ship | `/ship` | Final gate |

Rules:
- Resume: if `docs/features/<slug>/STATUS.md` exists, continue from its phase.
- Update STATUS.md at every transition. All handoffs go through files in `docs/features/<slug>/`.
- Status updates to me: 1–2 lines per step.
- 4b needs the app running on local/staging. FAIL → `implementer` fixes → rerun that TC → back through 4 Verify. Skip 4b (and say so in STATUS.md) only when no AC is observable in the UI.
- Specs with a performance NFR: in 5 Review also run `database-reviewer` in `profile` mode against the NFR numbers.
- Never skip a gate, even if I seem away.

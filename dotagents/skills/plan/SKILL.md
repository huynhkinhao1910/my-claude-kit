---
name: "plan"
description: "Phase 2 — technical plan + task breakdown for an approved spec (planner + Gate 2). Without a slug, plans an ad-hoc task and waits for confirmation."
---

Input: <slug> | <free-text task>

Input: the user's request

**Feature mode** (`docs/features/<slug>/spec.md` exists):
1. Require `Status: approved`; otherwise stop and say so.
2. If the area is unfamiliar, delegate to `code-explorer` first and pass its map to the planner.
3. Delegate to `planner` with the slug.
4. Show me: approach (≤5 lines), tasks T1..Tn with AC mapping, top risks, blockers.
5. **STOP — Gate 2.** Wait for "approve plan" or change requests (re-invoke `planner`).
6. On approval: create/checkout `feature/<slug>` from the base branch; tick Gate 2.

**Ad-hoc mode** (no spec): restate the requirement, list risks and numbered steps (delegate to `planner` without writing files), then **WAIT for my confirmation** before touching any code.

---
name: feature-spec
description: Template and rules for a testable feature spec — user stories, Gherkin acceptance criteria with stable IDs, edge cases, NFRs, out of scope, open questions, assumptions. Use when writing or validating docs/features/<slug>/spec.md. Do NOT use for technical plans (planner) or feature docs after shipping (feature-docs).
---

# Feature Spec

## Rules
- Slug: kebab-case, ≤ 5 words. Folder: `docs/features/<slug>/`.
- AC IDs `AC1..n` and edge-case IDs `EC1..n` are stable: never renumber after approval — append.
- ACs are Given/When/Then, observable from outside (HTTP response, DB state, event/job, UI state) and automatable.
- UI ACs name what the user sees and what the network does ("the button is disabled and no POST /api/v1/cart is sent"), so that `/ui-test` can check them literally.
- NFRs have numbers (p95 < 300 ms, 10k rows/import, 50 req/s). For list or detail endpoints, add a query budget ("≤ 5 queries per request") when the data grows.
- Out of scope is mandatory. Unknowns → Open Questions; guesses → `[ASSUMPTION]`.
- No implementation details (no new table/class names).

## Template
See `references/template.md`. Also create `STATUS.md` from `references/status-template.md` if missing.

## Self-check
- [ ] Every story has ≥1 AC; every AC automatable
- [ ] Permission stated for every action
- [ ] Edge cases: empty, invalid, unauthorized, duplicate/idempotent, concurrent, large volume
- [ ] Out of scope + open questions filled

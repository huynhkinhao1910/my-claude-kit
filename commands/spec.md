---
description: Phase 1 — turn a raw requirement into an approved spec.md (requirement-analyst + Gate 1)
argument-hint: <slug> <requirement text | file path | ticket URL>
---

Input: $ARGUMENTS

1. First token = `<slug>` if kebab-case, else propose one. Create `docs/features/<slug>/` and `STATUS.md` (from `feature-spec` → `references/status-template.md`) if missing.
2. Delegate to `requirement-analyst` with the full requirement and slug.
3. Show me: spec path, counts, numbered Open Questions, assumptions.
4. **STOP — Gate 1.** Wait for my answers or "approve spec". For answers: re-invoke `requirement-analyst` to update spec.md. On approval: set `Status: approved` in spec.md and tick Gate 1 in STATUS.md.

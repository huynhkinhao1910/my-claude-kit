---
description: Phase 5 — feature docs + MR description, push branch, open draft GitLab MR (final gate)
argument-hint: <slug>
---

1. Require review.md verdict `APPROVED`; else stop.
2. Delegate to `doc-writer` (slug). When `ui-test-report.md` exists, the MR description includes its result table; a FAIL there blocks shipping.
3. Show me the deviations list and the MR description.
4. **STOP — Final gate.** On "ship": commit docs (`docs(<slug>): feature documentation`), `git push -u origin feature/<slug>`, then `glab mr create ... --draft` per the `gitlab-mr` skill (or print the description if `glab` is missing). Update STATUS.md → `phase: done` with the MR link.

---
description: Phase 4 — parallel multi-agent review routed by changed file types, consolidated into review.md (Gate 3)
argument-hint: <slug> [base-branch=main]
---

Input: $ARGUMENTS

1. `git diff --name-only <base>...HEAD` → pick reviewers:
   - `*.php` → `laravel-reviewer`
   - `*.vue`, Nuxt pages/composables/stores → `vue-reviewer`
   - `*.tsx|*.jsx`, Next.js app/pages → `react-reviewer`
   - `*.ts|*.js` (NestJS, Node, shared utils, or `.vue`/`.tsx` with non-trivial types) → `typescript-reviewer`
   - `*.go` → `go-reviewer`
   - `*.py` → `python-reviewer`
   - migrations / raw SQL / new queries → `database-reviewer`
   - routes, auth, FormRequests, uploads, webhooks, payments, config → `security-reviewer`
   - anything else (CI, Docker, shell) → `code-reviewer`
   - always → `silent-failure-hunter`; `spec-verifier` if `spec.md` exists
2. Launch the selected reviewers IN PARALLEL (one message, multiple Agent calls). Pass: slug, base branch, spec/plan paths.
3. Consolidate with the `review-checklist` skill (section 5) into `docs/features/<slug>/review.md` (round n). Personally re-check every BLOCKER/MAJOR line.
4. Show me the verdict + BLOCKER/MAJOR rows only.
5. **STOP — Gate 3.** Options: "fix all" | "fix #1,#3" | "approve".
   Fix → `implementer` with the findings → `/verify` → re-run this review. Max 3 rounds, then escalate.

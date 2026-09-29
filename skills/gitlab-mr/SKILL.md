---
name: gitlab-mr
description: Branch naming, Conventional Commits and GitLab Merge Request conventions, MR description template and glab commands. Use when committing, pushing a feature branch, or preparing/creating a GitLab MR. Do NOT use for GitHub PRs (use the /pr command or github-ops).
---

# GitLab MR

## Branch & commits
- Branch: `feature/<slug>`, `fix/<slug>`, `chore/<slug>` from `develop` (or the repo's base in CLAUDE.md).
- One commit per plan task where possible: `feat(<scope>): <summary> [T3]`.
- Never force-push shared branches; never commit to `main`/`master`/`develop`.

## MR description (English)
```
## What
## Why
<link spec.md / ticket>
## How
- key design decisions
## Changes
- DB: migrations/indexes
- API: endpoints
- Jobs/Config/Env:
## Testing
- ACs covered: X/Y (see review.md)
- Manual steps:
## Risk & rollback
## Checklist
- [ ] Migrations reversible
- [ ] New env vars documented in .env.example
- [ ] review.md verdict APPROVED
```

## Commands
```bash
git push -u origin feature/<slug>
glab mr create --source-branch feature/<slug> --target-branch develop \
  --title "<type>(<scope>): <summary>" \
  --description "$(cat docs/features/<slug>/mr-description.md)" --draft
```
Without `glab`: print the description for the user to paste.

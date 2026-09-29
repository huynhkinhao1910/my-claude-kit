---
name: review-checklist
description: Shared rules for every code reviewer agent — confidence gate, proof requirements, common false positives, severity scale, fixed output table, and how the orchestrator consolidates findings into review.md with a verdict. Use when reviewing a diff or merging reviewer outputs. Do NOT use as a language checklist (each reviewer agent has its own).
---

# Review Checklist

## 1. Confidence gate (before writing ANY finding)
Answer all four; if any is "no/unsure", downgrade or drop:
1. Can I cite the exact `file:line`?
2. Can I name the concrete failure: input/state → bad outcome?
3. Have I read the surrounding context (callers, guards, types, tests)?
4. Is the severity defensible?

BLOCKER/MAJOR additionally need: the snippet, the failure scenario, and why existing guards (types, validation, framework defaults, middleware) don't catch it.

Zero findings is a valid, expected result. Manufactured findings, filler nits and speculative "consider X" are the main failure mode of LLM reviewers.

## 2. Skip these false positives (unless evidence in THIS codebase)
- "Add error handling" when the caller/framework handles it (exception handler, middleware, error boundary).
- "Missing validation" on internal functions whose callers validate — trace one caller first.
- Magic numbers for HTTP codes, 60/24/1000/1024, index 0/-1, obvious local constants.
- "Function too long" for switch tables, config arrays, test data providers.
- "Missing docblock" on self-describing private helpers.
- N+1 on fixed tiny loops or already eager-loaded relations.
- Hardcoded values in tests/fixtures; non-crypto `rand()`/`Math.random()`.
- Suggesting a stack change (add TypeScript, switch ORM…).
Ask: "Would a senior engineer on this team change this in review?" If no, skip.

## 3. Severity
| Sev | Meaning | Merge? |
|-----|---------|--------|
| BLOCKER | Wrong behavior, data loss/corruption, exploitable security hole, AC failing | No |
| MAJOR | Likely bug, missing test for an AC/edge case, scale risk at 10x volume | Fix or justify in writing |
| MINOR | Maintainability / convention violation from CLAUDE.md | Fix if cheap |
| NIT | Taste | Optional — max 3 per review |

## 4. Output (every reviewer returns exactly this)
```
## <agent-name>
| # | Sev | File:Line | Issue | Failure scenario | Fix |
|---|-----|-----------|-------|------------------|-----|
Result: X BLOCKER · Y MAJOR · Z MINOR · W NIT
```
If none: `## <agent-name>\nNo issues.`

## 5. Consolidation (orchestrator → docs/features/<slug>/review.md)
1. Merge tables, sort by severity; dedupe same file:line + root cause (list all reviewers in "Found by").
2. Re-read the line for every BLOCKER/MAJOR yourself; move false positives to "Rejected findings" with a reason.
3. Append the spec-verifier matrix verbatim.
4. Verdict: `CHANGES REQUIRED` if any BLOCKER, unjustified MAJOR, or any AC not PASS; else `APPROVED`.
5. Max 3 review→fix rounds, then escalate to the human.

```
# Review — <slug> — round <n>
Verdict: CHANGES REQUIRED | APPROVED
## Findings
| # | Sev | File:Line | Issue | Fix | Found by | Status |
## Spec coverage
<spec-verifier table>
## Rejected findings
| Finding | Reason |
```

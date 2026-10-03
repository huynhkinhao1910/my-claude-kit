---
name: ui-test-cases
description: Write UI test cases from spec ACs, a bug report or described flows, then run them step by step in claude-in-chrome, checking UI, network and console, with a per-TC report. Use for /ui-test or reproducing a UI bug. Do NOT use for Playwright specs (e2e-testing), unit/feature tests, or post-deploy smoke/a11y (browser-qa).
origin: My Claude Kit
---

# UI test cases

Check a feature's user flows on a running app by driving a real browser step by step. No test code. `spec-verifier` checks that tests exist and assert the right thing; this run proves that the flow actually works on screen.

Always two steps, in this order: **write** the TCs into `test-cases.md` and get an OK, then **run** them.

## 1. Write

Use the first source that applies:

1. **`docs/features/<slug>/spec.md`**: one TC per AC or EC whose Then-clause is observable in the UI or on the network. Keep the ID link (`TC-03 (AC3)`).
2. **A bug report**: one TC that reproduces it.
3. **A bare URL with no docs**: ask for the flows to cover.

Save the TCs to `docs/features/<slug>/test-cases.md`, or to the scratchpad when there is no slug. Existing TCs keep their IDs; new ones are appended. TCs run only after the user has seen them and said OK.

### Format

```markdown
### TC-03 (AC3) Add to cart is blocked when out of stock
Pre:    logged in as the seeded test buyer; product "demo-a" has stock 0
Steps:
  1. Open /products/demo-a
  2. Click "Add to cart"
Expect:
  - UI: the button is disabled and "Out of stock" is visible
  - Network: no POST /api/v1/cart is sent
  - Console: no errors
Mutates: no
```

Rules:
- **Expect** is literal and checkable: exact text, element state, URL, request and status. "Works", "looks fine" and "loads correctly" are not allowed.
- Every TC has a **Network** line, or `Network: n/a` when the step makes no request.
- `Mutates: yes` when the flow creates, changes or deletes data (orders, payments, emails, deletes). See section 3.
- One flow per TC. Cover the happy path, then the AC's negative paths: invalid input, unauthorized access, an empty state, and a double submit.

## 2. Run (claude-in-chrome)

Open a new tab with `tabs_create_mcp`; never reuse the user's tabs. If no browser is connected, report `BLOCKED: no browser` and stop.

For each TC:

1. **Set up the preconditions.** Use seed or fixture data and test accounts from the project (`.env.testing`, seeders, `tests/fixtures`). Never use real user credentials. If a precondition cannot be met, the TC is `BLOCKED`.
2. For each step:
   1. **Find** the target with `find` or `read_page`, by role, label or visible text, then by `data-testid`. Do not use CSS paths.
   2. **Act** with `computer` (click, type, key), `form_input` or `navigate`. One action per step.
   3. **Wait for a condition**: re-read the page until the text shows, the URL changes or the request appears in `read_network_requests`. Give up after about 10 s and fail the step with `timeout`.
   4. If the step would open a native `alert`/`confirm`/`prompt`, do not click it: the dialog freezes the extension. Mark the TC `BLOCKED (native dialog, check by hand)`.
3. **Assert all three layers** in the Expect block:
   - **UI**: `read_page`/`find` text and element state (disabled, checked, value).
   - **Network**: `read_network_requests` filtered to the API. Check the method, path, status, and that the request happened or did not happen.
   - **Console**: `read_console_messages`, errors only. Ignore known third-party noise, but list it.
4. **Verdict**:
   - `PASS`: every Expect line holds.
   - `FAIL`: any Expect line does not hold. Rerun the TC once from a clean state. If it fails again it is `FAIL`; if it passes the second time it is `FLAKY`.
   - `BLOCKED`: a precondition, data, account or tool is missing. Say exactly what is missing.

Evidence is text, not files: the failing step, the network line and the console line go into the report.

Do not "fix" the app or the test case to make it pass. Report the failure, and leave changes to `implementer`.

## 3. Safety

- Run on **local, dev or staging** only. On any other host, stop and ask.
- `Mutates: yes` TCs run only on local/staging **and** after an explicit yes from the user in this session. Payments use the provider's test mode and its test cards only.
- Never type real passwords, card numbers or personal data. Use generated test data or project fixtures.
- Redact tokens, emails and personal data in the report.
- Do not accept cookie banners or terms beyond what the TC needs. Do not click anything that sends real email, SMS or messages unless the TC targets a sandbox.

## 4. Report: `docs/features/<slug>/ui-test-report.md`

```markdown
## e2e-runner (ui-test)

Target: http://localhost:3000 (local) · Tool: claude-in-chrome · Run: 2026-10-02 15:40
Source: test-cases.md (AC1–AC6, EC2) · 7 TCs

| TC | AC/EC | Verdict | Failing step / reason |
|----|-------|---------|-----------------------|
| TC-01 | AC1 | PASS | — |
| TC-03 | AC3 | FAIL | step 2: button enabled; POST /api/v1/cart → 422 sent |
| TC-05 | EC2 | BLOCKED | no seeded product with stock 0 |

Result: 5 PASS · 1 FAIL · 1 BLOCKED · 0 FLAKY
Console errors: none (ignored: 1× analytics 404)
Not covered: AC4 (email content, not visible in UI)
```

For each FAIL, add a short block with the expected vs the actual result and the network line, so that `implementer` can reproduce the failure without rerunning the browser.

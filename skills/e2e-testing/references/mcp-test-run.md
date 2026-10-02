# Run UI test cases through a browser MCP

Use this when a feature's user flows must be checked on a running app *now*, by driving a real browser step by step. No test code is needed up front. It is the UI half of verification: `spec-verifier` checks that tests exist and assert the right thing, while this run proves that the flow actually works on screen. Test cases that pass can later be codified into Playwright specs for CI (section 7).

## 1. Where test cases come from

Use the first source that applies:

1. **`docs/features/<slug>/spec.md`**: every AC or EC whose Then-clause is observable in the UI or on the network. Derive one TC per AC/EC and keep the ID link (`TC-03 (AC3)`).
2. **`docs/features/<slug>/test-cases.md`**: written by hand or by `planner` when there is no full spec.
3. **A bare URL with no docs**: ask for the flows to cover, draft TCs in the format below, show them, and wait for an OK before running. Save them to `test-cases.md` when a slug exists.

## 2. Test case format

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
- `Mutates: yes` when the flow creates, changes or deletes data (orders, payments, emails, deletes). See section 5.
- One flow per TC. Cover the happy path, then the AC's negative paths: invalid input, unauthorized access, an empty state, and a double submit.

## 3. Tools

| Tool | When |
|------|------|
| Playwright MCP (`mcp__plugin_playwright_playwright__*`) | Default. Isolated browser, repeatable, headless. |
| claude-in-chrome (`mcp__claude-in-chrome__*`) | The user wants to watch the run, or the app needs a session that only their browser has. Open a new tab; never reuse the user's tabs. |
| Neither available | Report `BLOCKED: no browser MCP` and offer to codify the TCs as Playwright specs instead (section 7). |

## 4. Step loop

For each TC:

1. **Set up the preconditions.** Use seed or fixture data and test accounts from the project (`.env.testing`, seeders, `tests/fixtures`). Never use real user credentials. If a precondition cannot be met, the TC is `BLOCKED`.
2. For each step:
   1. **Snapshot** the page (`browser_snapshot` / `read_page`) and find the target by role, label or visible text, then by `data-testid`. Do not use CSS paths.
   2. **Act**: click, type, select or navigate. One action per step.
   3. **Wait for a condition**: text visible, URL changed, or the request finished (`browser_wait_for`). Never wait a fixed time.
3. **Assert all three layers** in the Expect block:
   - **UI**: snapshot text and element state (disabled, checked, value).
   - **Network**: `browser_network_requests` / `read_network_requests`, filtered to the API. Check the method, path, status, and that the request happened or did not happen.
   - **Console**: errors only. Ignore known third-party noise, but list it.
4. **Evidence**: take a screenshot at the final Expect, and at the failing step on failure. Save it as `docs/features/<slug>/ui-test/<TC>-<step>.png`, or in the scratchpad when there is no slug.
5. **Verdict**:
   - `PASS`: every Expect line holds.
   - `FAIL`: any Expect line does not hold. Rerun the TC once from a clean state. If it fails again it is `FAIL`; if it passes the second time it is `FLAKY`.
   - `BLOCKED`: a precondition, data, account or tool is missing. Say exactly what is missing.

Do not "fix" the app or the test case to make it pass. Report the failure, and leave changes to `implementer`.

## 5. Safety

- Run on **local, dev or staging** only. On any other host, stop and ask.
- `Mutates: yes` TCs run only on local/staging **and** after an explicit yes from the user in this session. Payments use the provider's test mode and its test cards only.
- Never type real passwords, card numbers or personal data. Use generated test data or project fixtures.
- Redact tokens, emails and personal data in screenshots and in the report.
- Do not accept cookie banners or terms beyond what the TC needs. Do not click anything that sends real email, SMS or messages unless the TC targets a sandbox.

## 6. Report: `docs/features/<slug>/ui-test-report.md`

```markdown
## e2e-runner (ui-test)

Target: http://localhost:3000 (local) · Tool: Playwright MCP · Run: 2026-10-02 15:40
Source: spec.md (AC1–AC6, EC2) · 7 TCs

| TC | AC/EC | Verdict | Failing step / reason | Evidence |
|----|-------|---------|-----------------------|----------|
| TC-01 | AC1 | PASS | — | ui-test/TC-01-3.png |
| TC-03 | AC3 | FAIL | step 2: button enabled; POST /api/v1/cart → 422 sent | ui-test/TC-03-2.png |
| TC-05 | EC2 | BLOCKED | no seeded product with stock 0 | — |

Result: 5 PASS · 1 FAIL · 1 BLOCKED · 0 FLAKY
Console errors: none (ignored: 1× analytics 404)
Not covered: AC4 (email content, not visible in UI)
```

For each FAIL, add a short block with the expected vs the actual result and the network line, so that `implementer` can reproduce the failure without rerunning the browser.

## 7. Codify passing TCs (optional, after approval)

Turn each `PASS` TC into a Playwright spec following the main `SKILL.md` (POM, `getByRole`/`data-testid`, `waitForResponse`, no `waitForTimeout`):

- Put the IDs in the test title, for example `test('TC-03 AC3 add to cart blocked when out of stock', ...)`, so that `spec-verifier` can trace it.
- Assert the same three layers. For network, use `page.waitForResponse` or `expect(request).toBeFalsy()` patterns.
- Run the spec 3 times (`--repeat-each=3`) before calling it stable.

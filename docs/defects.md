# Defects found while building the automation

Every item below was reproduced against the live application on 2025-08-25 while
writing the suites. Each one is either encoded in a test or explains why a test is
written the way it is.

## Web UI

### BUG-001 — Three different buttons share `id="submit"` on /profile
**Severity:** Medium (accessibility + automatability)
**Steps:** Log in → open `/profile` → inspect the DOM.
**Actual:** *Logout*, *Delete Account* and *Delete All Books* all render `id="submit"`.
**Expected:** Ids are unique per document (HTML spec).
**Why it matters:** Duplicate ids break `document.getElementById`, break screen-reader
label association, and force every automated test to fall back to text matching. It is
a one-line fix that removes a whole class of future flakiness.

### BUG-002 — Two buttons share `id="addNewRecordButton"` on the book detail page
**Severity:** Medium
**Actual:** *Back To Book Store* and *Add To Your Collection* carry the same id, so
`#addNewRecordButton` resolves to whichever comes first in the DOM — a test written
against it would silently click the wrong control.

### BUG-003 — "Delete All Books" is rendered twice on /profile
**Severity:** Low
**Actual:** The profile page renders two identical *Delete All Books* buttons.
**Expected:** One. A duplicated destructive action is a genuine usability risk.

### BUG-004 — Empty collection paginates as "Page 1 of 0"
**Severity:** Low
**Steps:** Log in with an empty collection, or delete the last book.
**Actual:** The pager reads `Page 1 of 0`.
**Expected:** `Page 0 of 0`, or the pager is hidden when there is nothing to page.

### BUG-005 — /profile briefly renders its logged-out panel after a successful login
**Severity:** Low (perceived quality), High (as a source of test flakiness)
**Steps:** Submit valid credentials on `/login`.
**Actual:** The browser lands on `/profile` and, for a few hundred milliseconds, shows
the "Login in Book Store" panel before the authenticated view replaces it.
**Impact:** Any test — or user — that reacts to the first paint sees the wrong state.
The suite works around it by waiting on `#userName-value`, not on the URL.

### OBS-001 — Logout is labelled "Logout" on /profile and "Log out" on the book detail page
Cosmetic inconsistency; the suite matches `/log ?out/i` rather than either literal.

## API

### BUG-006 — Failed authentication returns `200 OK`
**Severity:** High (contract correctness)
**Request:** `POST /Account/v1/GenerateToken` with a valid username and a wrong password.
**Actual:** `200 OK` with `{"token":null,"expires":null,"status":"Failed","result":"User authorization failed."}`
**Expected:** `401 Unauthorized`.
**Why it matters:** Every generated client, gateway, retry policy and alerting rule keys
off the status code. A failed credential check that reports success is invisible to
monitoring, and a client that only checks `res.ok` will happily proceed with a null token.

### BUG-007 — Wrong password reported as "User not found"
**Severity:** Medium
**Request:** `POST /Account/v1/Authorized` with an existing username and a wrong password.
**Actual:** `404` with `{"code":"1207","message":"User not found!"}`
**Expected:** `401` with a credential-failure code. The user exists; the password does not
match. Reporting 404 misleads clients and support alike.

### BUG-008 — HTTP status and error code disagree
**Severity:** Medium
**Request:** `GET /Account/v1/User/{id}` for a deleted account, with that account's token.
**Actual:** HTTP `401` carrying `{"code":"1207","message":"User not found!"}` — the same
error code that `/Authorized` pairs with HTTP `404`.
**Expected:** One code, one status, consistently. As it stands a client cannot map error
codes to statuses reliably.

### BUG-009 — Generating a token silently invalidates the existing session
**Severity:** High (undocumented behaviour with real product impact)
**Steps:** Log in through the UI, then call `POST /Account/v1/GenerateToken` for the same
user. Every subsequent request from the browser session returns `401`.
**Actual:** The back end keeps one valid token per user; a new token kills the old one.
**Expected:** Either concurrent sessions are supported (a user on a phone and a laptop is
not an edge case), or the single-session rule is documented and the evicted session is
told why. This is not visible in the Swagger contract at all.
**Impact on the suite:** cross-layer assertions reuse the browser's own session cookie
instead of minting a second token — see `sessionTokenFromBrowser()`.

### OBS-002 — `/Account/v1/Authorized` returns a bare JSON primitive
Responds with `true` rather than an object such as `{"authorized": true}`. Legal JSON,
but awkward for typed clients and impossible to extend without a breaking change.

### PASS — Object-level authorisation is correctly enforced
Worth recording as a *positive* result, because it is the flaw this API's shape invites:
the `userId` travels in the request body, so a naive implementation would trust it. It
does not. With user A's token:

* `GET /Account/v1/User/{B's id}` → `401`
* `POST /BookStore/v1/Books` with `userId = B` → `401`
* `DELETE /Account/v1/User/{B's id}` → `401`

Covered by the `@security` scenarios in `account.feature`.

## Environment constraint (not a defect)

Registration is protected by Google reCAPTCHA. It cannot be automated through the
browser, and defeating it would only work against this demo site. Registration is
therefore performed through the public API for test-data purposes, and the UI suite
asserts the form's contract instead. In a real product the fix is a test-environment
captcha bypass key — reCAPTCHA ships one for exactly this reason.

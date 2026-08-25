# Test Plan — Book Store Application

**Application under test:** https://demoqa.com/books (web) · https://demoqa.com/swagger (API)
**Author:** Senior QA Engineer candidate · **Date:** 25 Aug 2025
**Status:** Executed — results in [defects.md](defects.md)

---

## 1. What we are testing and why

The Book Store lets a person register, sign in, browse a catalogue of books, keep a
personal collection, and sign out. The product's value sits in one place: **a user's
collection is correct and private**. Everything else — layout, sorting, pagination — is
secondary to that.

So the plan is organised around the question *"can the collection be wrong, lost, or seen
by the wrong person?"* rather than around a list of screens.

### In scope

| Area | Web | API |
|---|---|---|
| Registration and password policy | ✓ (form contract) | ✓ |
| Authentication and session handling | ✓ | ✓ |
| Catalogue browse, search, sort, paginate | ✓ | ✓ |
| Book detail | ✓ | ✓ |
| Collection: add, list, replace, delete, clear | ✓ | ✓ |
| Authorisation between users | — | ✓ |
| Cross-layer consistency (UI state = API state) | ✓ | ✓ |

### Out of scope, and why

- **Load and stress testing** — we do not own the shared demo environment; a load run
  would degrade it for everyone else using the site.
- **Penetration testing** — beyond the authorisation checks that need no special
  permission.
- **Visual regression** — worth adding once the DOM stabilises, but it is not the first
  thing that protects a collection from corruption.
- **Solving reCAPTCHA** — see *Known constraints*.

---

## 2. Risk analysis — what drives coverage

Coverage follows risk, not screen count. Probability and impact are scored from how the
system actually behaves, which is why several rows below already read "Confirmed" (see
[defects.md](defects.md)).

| # | Risk | Impact | Prob. | Priority | How it is covered |
|---|---|---|---|---|---|
| R1 | One user reads or modifies another user's collection | Critical | Low | **P0** | `@security` scenarios: cross-token read, write, delete |
| R2 | A book is added but not persisted (the UI lies) | High | Medium | **P0** | Cross-layer assertion: UI action, then API read-back |
| R3 | Delete removes the wrong book, or does not persist | High | Medium | **P0** | Delete by ISBN, then API read-back; plus a cancel-path test |
| R4 | Session does not end on logout | High | Low | **P0** | Post-logout access to `/profile` must be refused |
| R5 | Failed authentication reported as success | High | Confirmed | **P0** | Negative auth scenarios (found **BUG-006**) |
| R6 | Weak passwords accepted | Medium | Low | **P1** | Policy table plus an 8-character boundary scenario |
| R7 | Duplicate add corrupts the collection | Medium | Medium | **P1** | Duplicate add → 1210, then state re-verified |
| R8 | Concurrent sessions evict each other | Medium | Confirmed | **P1** | Documented as **BUG-009**; drove the suite's token design |
| R9 | Search returns wrong or no results | Medium | Medium | **P1** | Exact, partial, no-match and case searches |
| R10 | Catalogue payload changes shape | Medium | Medium | **P1** | Schema assertion on every catalogue entry |
| R11 | Pagination or sorting wrong | Low | Medium | **P2** | Exploratory plus one automated check (found **BUG-004**) |
| R12 | Cosmetic and responsive defects | Low | High | **P2** | Exploratory each release |

**The rule this produces:** P0 is automated and gates every deployment. P1 is automated
and runs on every pull request. P2 is exploratory, with selective automation once a
defect is found twice.

---

## 3. Test approach by layer

The same journey is covered at two layers, deliberately, because they answer different
questions.

```
        ┌───────────────────────────────────────────────┐
 few    │  E2E (Playwright)  register → … → logout      │  does the journey hold
        │  1 journey + critical negatives               │  together for a person?
        ├───────────────────────────────────────────────┤
 some   │  API (Karate)  contracts, auth, error codes   │  is the behaviour correct
        │  23 scenarios                                 │  and complete?
        ├───────────────────────────────────────────────┤
 many   │  Unit tests (owned by developers)             │  is the logic right?
        └───────────────────────────────────────────────┘
```

**Why so much sits at the API layer:** that is where the rules live (password policy,
authorisation, error codes), it runs roughly twenty times faster, and it does not break
when a class name changes. Every rule that *can* be tested there *is* tested there. The
UI layer then only has to prove the journey works end to end — one E2E test, not thirty.

### Test design techniques applied

| Technique | Where |
|---|---|
| Equivalence partitioning | Password classes; ISBN valid / unknown / malformed |
| Boundary value analysis | Password at exactly 8 characters, and at 7 |
| State transition | Collection: empty → one book → duplicate rejected → empty |
| Decision table | Auth outcomes: user exists × password correct × token present |
| Error guessing | Deleted account holding a live token; token replaced mid-session |
| Contract / schema testing | Every catalogue and collection payload |

---

## 4. Test coverage

### 4.1 API scenarios — automated in Karate (23 scenarios, all passing)

| Endpoint | Positive | Negative and edge |
|---|---|---|
| `POST /Account/v1/User` | 201, empty collection, well-formed body | 7 password-policy violations → 400/1300; duplicate user → 406/1204; 8-char boundary → 201 |
| `POST /Account/v1/GenerateToken` | 200, `Success`, token issued | Wrong password → **200 + `Failed`** (BUG-006) |
| `POST /Account/v1/Authorized` | `true` for valid credentials | Wrong password → 404/1207 (BUG-007) |
| `GET /Account/v1/User/{id}` | 200, collection matches | No token → 401/1200; malformed token → 401; another user's id → 401; deleted account → 401/1207 (BUG-008) |
| `DELETE /Account/v1/User/{id}` | 204, and the token dies with it | Another user's account → 401 |
| `GET /BookStore/v1/Books` | 200, schema, ISBNs unique | — |
| `GET /BookStore/v1/Book?ISBN=` | 200, full schema | Unknown ISBN → 400/1205 |
| `POST /BookStore/v1/Books` | 201 for one book and for several | Duplicate → 400/1210 with state unchanged; no token → 401; another user's id → 401 |
| `PUT /BookStore/v1/Books/{ISBN}` | 200, old ISBN gone, new one present | — |
| `DELETE /BookStore/v1/Book` | 204, removed | Book not owned → 400/1206 |
| `DELETE /BookStore/v1/Books?UserId=` | 204, collection emptied | — |

### 4.2 Web scenarios — automated in Playwright (7 tests, all passing)

| ID | Scenario | Tag |
|---|---|---|
| W-01 | Full journey: register → login → search → add → view → delete → logout | `@e2e` |
| W-02 | Cancelling the delete dialog keeps the book (state seeded via API) | `@regression` |
| W-03 | Unknown credentials → error shown, no session created | `@smoke` |
| W-04 | Valid user, wrong password → rejected | `@smoke` |
| W-05 | `/profile` refuses anonymous access | `@smoke` |
| W-06 | Registration form contract and reCAPTCHA present | `@smoke` |
| W-07 | Password policy enforced (via API — the rule the form fronts) | `@smoke` |

W-01 additionally asserts that after each UI action the **API agrees** with what the
screen shows. That is the check which catches "the UI said it saved, and it didn't".

### 4.3 Manual and exploratory — each release, time-boxed to 90 minutes

Charters, not scripts:

- Catalogue sorting and pagination applied on top of a filtered search.
- Search behaviour: partial words, case, punctuation, ISBN, and the no-match empty state.
- Session: browser back after logout; two tabs; token expiry at six hours.
- Responsive layout at 360 px, 768 px and 1440 px.
- Keyboard-only journey and screen-reader labels — duplicate ids are already a known
  problem here (BUG-001, BUG-002).

---

## 5. Test data strategy

| Need | Approach |
|---|---|
| User accounts | Generated per test (`qa_<uuid>`), created via API, deleted in teardown |
| Passwords | Meet the documented policy; violation cases live in a data table |
| Books | The seeded catalogue is read-only and stable; ISBNs referenced by constant |
| Collections | Seeded through the API whenever the test is not *about* adding a book |

**Nothing is shared between tests.** The demo environment's user namespace is global and
shared with strangers on the internet, so any fixed username eventually collides with
`406 User exists!`. Isolation is what makes the suite parallel-safe, and the same
principle applies to any shared staging environment.

---

## 6. Environments

| Environment | Purpose | Data | Suite |
|---|---|---|---|
| Local | Developer feedback | Ephemeral | `@smoke` on pre-push |
| CI (pull request) | The merge gate | Generated per run | `@smoke` + `@e2e`, chromium |
| Staging | Release candidate | Anonymised, refreshed nightly | Full regression, three browsers |
| Production | Post-deploy confidence | Read-only synthetic account | Smoke only, non-destructive |

`BASE_URL` (Playwright) and `karate.env` (Karate) are the only things that change between
them. There are no forks of the test code per environment.

---

## 7. Entry and exit criteria

**Entry:** the build deploys; the API answers a health check; test accounts can be
created; the feature has acceptance criteria written down.

**Exit:**

- All P0 and P1 automated tests pass.
- No open Critical or High defect in the flows under test.
- Exploratory charters completed and findings triaged.
- Every test disabled during the cycle has a ticket and a named owner. A quarantined
  test with no owner is deleted coverage that nobody has admitted to.

---

## 8. Reporting

- **Per run:** Playwright HTML report with traces, and the Karate HTML summary, both
  published as CI artefacts — a failure should be diagnosable from the build alone,
  without anyone re-running it locally.
- **Per release:** one page. What was covered, what was found, what is still risky.
- **Defects:** logged with steps, expected versus actual, evidence and environment.
  [defects.md](defects.md) shows the format used here.

---

## 9. Known constraints

**Registration is behind Google reCAPTCHA.** It cannot be driven from an automated
browser, and defeating it would only work against this demo site — a test that passes by
cheating gives false confidence. Two consequences:

1. Accounts for UI tests are provisioned through `POST /Account/v1/User`, which produces
   exactly the account a real registration would.
2. The UI suite asserts the *form's* contract — fields present, reachable from login,
   captcha enforced — and the registration rules themselves are covered at the API layer.

On a product I owned, the fix would be a reCAPTCHA test key in non-production
environments; Google publishes one for this exact purpose. That would be my first
request to the development team.

**Single active token per user.** Found while building the suite (BUG-009): calling
`GenerateToken` invalidates any existing session. Mixed UI and API tests therefore reuse
the browser's own session token rather than minting a competing one.

**Third-party ads intercept clicks.** The suite removes ad containers after navigation.
On a product I owned this would be environment configuration instead — tests should not
have to fight the page they are testing.

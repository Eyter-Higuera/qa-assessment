# API automation — Karate

```
src/test/java/karate-config.js          environment configuration
src/test/java/bookstore/common/         reusable setup / teardown (called, never run directly)
src/test/java/bookstore/e2e/            the end-to-end journey
src/test/java/bookstore/account/        registration, auth and authorisation contracts
src/test/java/bookstore/books/          catalogue and collection contracts
src/test/java/bookstore/*.java          JUnit 5 runners
```

## Requirements

**Java 17.** Karate 1.4.1 runs its JavaScript through GraalJS, which does not support
JDK 18+: on a newer JDK the suite does not fail, it *hangs* at `waiting for N features
to complete` with no error. This is the version CI pins (`.github/workflows/ci.yml`), so
match it locally:

```bash
java -version          # must report 17.x
```

Maven 3.8+ is also required.

## Running

```bash
mvn test -Dtest=BookStoreApiTest                 # everything (parallel, 5 threads)
mvn test -Dtest=SmokeTest                        # the deployment gate
mvn test -Dkarate.options="--tags @security"     # one tag
mvn test -Dkarate.env=staging                    # another environment
```

**On Windows PowerShell, quote any `-D` that contains a dot.** PowerShell ends a
parameter name at the first `.`, so `-Dkarate.env=staging` reaches Maven as two
arguments and it fails with *"Unknown lifecycle phase '.env=staging'"*. Wrap the
whole token in quotes:

```powershell
mvn test '-Dkarate.env=staging'
mvn test '-Dkarate.options=--tags @security'
```

`-Dtest=SmokeTest` has no dot and needs no quoting.

## Notable choices

**Every scenario owns its data.** `common/create-user.feature` provisions a throw-away
account and `common/delete-user.feature` removes it, so scenarios run in parallel
without colliding in the shared demo environment. Teardown tolerates a 401/404 — a
leftover account is a cleanup problem, not a product defect, and must not turn a green
run red.

**Schema assertions, not field spot-checks.** `match each response.books == bookSchema`
catches a field that changed type or disappeared — the failures that spot-checks miss.

**Current behaviour is asserted, wrong behaviour is flagged.** Where the API is
inconsistent (`GenerateToken` answering `200 / status:"Failed"` for bad credentials,
a `401` carrying a `1207 User not found!` body), the test locks the behaviour that ships
today and a comment points at the defect in Appendix B of `Senior_QA_Engineer_Assessment.md`. Tests that assert what
the API *ought* to do would be red every day and would stop being read.

**"Logout" is modelled as end-of-session.** The API exposes no logout endpoint, so the
journey ends by disposing of the session and proving the token is genuinely rejected
afterwards rather than merely unused.

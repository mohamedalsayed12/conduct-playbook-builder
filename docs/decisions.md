# Design decisions

## Phase 0 — Scaffold

### Separate `postgres_test` Compose service
**Decision:** Run a dedicated Postgres container for tests (`postgres_test` on host port 5435), distinct from the app database.
**Alternatives:** Second database on the same Postgres instance; ephemeral containers spun up only by pytest; host port 5433.
**Why:** Keeps test data and migrations isolated from local demo data, matches CI’s dedicated test DB, and avoids accidental `DROP`/`TRUNCATE` against the app database. Port 5435 avoids a common local Postgres bind on 5433.

### Health checks expose dependency booleans only on failure
**Decision:** `GET /health` returns `{"status":"ok"}` when healthy; on 503 it includes `checks.database` / `checks.redis` booleans and no exception text.
**Alternatives:** Always include checks; return 200 with a degraded flag; leak error messages for debugging.
**Why:** Operators can see which dependency failed without turning the health endpoint into an information leak or a false-healthy signal for load balancers.

### JSON logs only in production
**Decision:** Readable line-oriented logs in `development`/`test`; JSON lines when `APP_ENV=production`.
**Alternatives:** JSON everywhere; third-party logging libraries.
**Why:** Local debugging stays readable while production stays aggregator-friendly, without adding dependencies outside the approved stack.

### Keep TestClient on httpx (silence Starlette deprecation)
**Decision:** Stay on the approved `httpx` dependency and ignore Starlette’s `httpx2` TestClient deprecation warning in pytest.
**Alternatives:** Add `httpx2` (outside approved stack); pin older Starlette.
**Why:** Phase 0 must not add unapproved packages; the warning is tooling-only and does not affect runtime behaviour.

### `RedisClient` alias via `TYPE_CHECKING`
**Decision:** Export `RedisClient` as `Redis[str]` for mypy and plain `Redis` at runtime.
**Alternatives:** Annotate with bare `Redis` (mypy `type-arg` errors); use `Redis[str]` everywhere (runtime `TypeError` because redis-py’s `Redis` is not generic).
**Why:** FastAPI evaluates annotations at import time, so a runtime-safe alias is required while keeping `mypy --strict` happy.

## Phase 1 — Data model

### Email unique per tenant (`UNIQUE (tenant_id, email)`)
**Decision:** Enforce uniqueness with a composite unique constraint on `(tenant_id, email)`, not a global unique email.
**Alternatives:** Globally unique emails; partial unique indexes per role.
**Why:** The same person can be invited into two customer accounts; uniqueness must be scoped to the tenant. Strategists use `tenant_id IS NULL`, and PostgreSQL treats NULLs as distinct in unique constraints, which fits platform-level strategist rows.

### `stage_changed_at` on the user row plus append-only `StageEvent`
**Decision:** Keep the current stage timestamp on `users.stage_changed_at` and record every transition in `stage_events`.
**Alternatives:** Derive “current stage changed at” only from the latest `StageEvent`; store only the user row with no history.
**Why:** List/stuck queries need a cheap filter on the user row, while average time-in-stage and audit need the full history. Duplicating the latest timestamp avoids a per-row subquery on the hot path.

### Store invite token hash only
**Decision:** Persist `token_hash` (SHA-256 hex) on `invites`; never store the raw token.
**Alternatives:** Store the raw token; encrypt the token at rest.
**Why:** A database leak must not let an attacker accept invites. The raw token is shown once at creation (Phase 2) and only the hash is comparable later.

### Strategist ↔ tenant via join table
**Decision:** Model coverage with `strategist_assignments` (`strategist_id`, `tenant_id` composite PK).
**Alternatives:** Array/UUID list on the tenant; a `tenant_id` on strategists (one account only).
**Why:** One strategist covers many accounts and one account can have several strategists; a join table is the straightforward relational model and rejects duplicates via the composite primary key.

### OpenQodex security scan on pull requests (scanners-only)
**Decision:** A separate `OpenQodex` workflow runs SAST, secrets, dependency and lint scanners on the changed lines of every pull request. Findings go to GitHub code scanning, and anything `major` or above fails the check. AI review is off.
**Alternatives:** OpenQodex's paid AI review using an Anthropic API key; a local pre-push hook only; no security scanning beyond ruff.
**Why:** The project's pitch is tenant isolation and keeping personal data out of logs, so every change should be security-scanned before merge. Scanners-only costs nothing and needs no secrets. Code review already happens locally in Cursor. `fail-on-tool-error` makes sure a broken scan fails the check instead of passing silently.

### One branch and one pull request per phase
**Decision:** Each build phase lands on `main` through its own branch (`phase-N-<name>`) and pull request, gated by the CI and OpenQodex checks.
**Alternatives:** Committing straight to `main`; one long-lived feature branch.
**Why:** Every phase gets checked before it merges, and the git history tells the build story phase by phase for anyone reviewing the repo.

## Phase 2 — Core API

### Temporary auth dependency instead of open routers
**Decision:** Every management route depends on `Phase2TemporaryCaller` (`get_phase2_temporary_caller`), a clearly named stub that always allows access.
**Alternatives:** No auth dependency until Phase 3; fake JWT already in Phase 2.
**Why:** Phase 3 can replace one dependency provider (`get_current_user`) without rewriting every endpoint signature, and the stub’s name makes the temporary hole obvious in code review.

### Generic invite failure message
**Decision:** Unknown, expired, and already-used invite tokens all raise `InviteTokenInvalidError` with the same client message.
**Alternatives:** Distinct messages per failure mode; 404 for unknown tokens.
**Why:** Distinct errors would let attackers probe for valid tokens. One generic 400 keeps invite acceptance enumeration-safe.

### Limit/offset pagination with a hard max page size
**Decision:** `GET /tenants/{id}/users` uses limit/offset, defaults from settings, and rejects limits above `MAX_PAGE_SIZE`.
**Alternatives:** Cursor-only pagination; unbounded pages.
**Why:** Limit/offset is enough for strategist tooling at current scale, and a max page size prevents accidental full-table responses.

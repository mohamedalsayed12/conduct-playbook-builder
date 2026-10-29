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

## Phase 3 — Security

### 404 (not 403) for inaccessible tenants
**Decision:** `require_tenant_access` raises `NotFoundError` when the caller is outside `accessible_tenant_ids`, same as a missing tenant.
**Alternatives:** 403 Forbidden; distinct error bodies for missing vs forbidden.
**Why:** A 403 would confirm that a tenant id exists. Returning 404 for both cases prevents tenant-id enumeration.

### Creating a tenant auto-assigns the strategist
**Decision:** `create_tenant` inserts a `StrategistAssignment` for the creating strategist in the same transaction.
**Alternatives:** Require a separate assign call; leave the creator without access until assigned.
**Why:** Without an assignment the creator could not call any tenant-scoped endpoint after create. Auto-assign is the natural bootstrap for coverage.

### HS256 JWT with algorithm allow-list
**Decision:** Issue and verify tokens with HS256 only via PyJWT `algorithms=["HS256"]`.
**Alternatives:** Asymmetric RS256; accept multiple HMAC algorithms.
**Why:** HS256 matches the approved stack (shared secret in settings). An allow-list rejects `alg=none` and algorithm-confusion attacks.

## Phase 4 — Rollout summary

### Invalidate summary cache only after commit
**Decision:** Delete `summary:v1:{tenant_id}` from Redis only after `session.commit()` returns successfully on invite, accept, and stage advance.
**Alternatives:** Invalidate inside the transaction before commit; use a write-through cache updated in the same request; skip caching.
**Why:** If we invalidate before commit, a concurrent summary request can recompute from the old committed rows, repopulate the cache, and leave readers with a stale summary after our commit. Post-commit invalidation drops the key after the writer finishes. A summary computed just before that commit can still be served until the key is deleted or the TTL expires — so staleness is **bounded by the cache TTL** (and by delete latency), not impossible. TTL also bounds staleness if Redis delete fails.

### Redis is optional for summary reads
**Decision:** On Redis errors during get/set/delete, log a warning with tenant id only and compute the summary from Postgres.
**Alternatives:** Fail the request when Redis is down; require Redis for the endpoint.
**Why:** Strategists need rollout visibility even when the cache is unavailable; Redis must not be a single point of failure for onboarding metrics.

## Phase 5 — Seed data

### Idempotent seed by natural keys
**Decision:** `run_seed` looks up the default playbook, strategist email, tenant names, assignments, and `(tenant_id, email)` users before inserting; existing rows are left unchanged.
**Alternatives:** Wipe-and-recreate; upsert that rewrites stage history every run.
**Why:** Strategists re-run `make seed` safely on a shared demo DB without duplicating accounts or resetting progress they may have advanced by hand.

## Phase 7 — Hardening

### Assignments require actor tenant access
**Decision:** `assign_strategist` calls `require_tenant_access` for the acting strategist before inserting a row.
**Alternatives:** Allow any strategist to self-assign onto any tenant; require a separate “owner” role.
**Why:** Without this check an unassigned strategist could grant themselves coverage and read every account. Only strategists who already cover the tenant may add colleagues.

### No default JWT secret; reject placeholders outside tests
**Decision:** `jwt_secret` is required from the environment (≥32 chars). Placeholder fragments such as `change-me` are rejected unless `APP_ENV=test`. In `production`, fragments such as `local-dev` and `do-not-use` are also rejected so the `.env.example` value cannot be copied into a live deploy. Compose passes `JWT_SECRET` into the API service.
**Alternatives:** Hardcoded default in `config.py`; soft warning only; reject local-dev secrets in development too.
**Why:** A public default lets anyone forge strategist tokens against a stock Docker deploy. Development still works with `.env.example`; production must use a unique secret.

### Invite acceptance is the only path out of `invited`
**Decision:** `next_stage` rejects `INVITED`; only `accept_invite` may move a user to `activated`.
**Alternatives:** Allow strategists to force-activate via advance.
**Why:** Advance-without-password left invites unusable and skipped password setup.

### Stuck metrics ignore `active` and non–end-users
**Decision:** Summary stage counts include end users only; stuck count and `/stuck` also exclude `active`.
**Alternatives:** Count every tenant user including admins; treat completed onboarding as stuck.
**Why:** Fully onboarded users and customer admins are not “stuck in onboarding.”

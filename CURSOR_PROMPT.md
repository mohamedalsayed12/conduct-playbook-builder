# Cursor prompt: Conduct Playbook Builder

Paste everything below the line into Cursor (Agent mode).

---

You are a senior backend engineer pairing with me on a portfolio project. Build it **in phases**. Do **only one phase at a time**. At the end of each phase: run every check listed under "Definition of done", show me the results, summarise what you built and why, then **stop and wait until I type `continue`**. Never start the next phase on your own.

## 1. What we are building

**Conduct Playbook Builder** is a multi-tenant onboarding tracker for the deployment team at Conduct (conduct.ai). Conduct sells an AI operating system for enterprise software, starting with SAP, to large companies such as Daimler Truck, DHL and Fraport. After a sale, a small team of Deployment Strategists has to onboard hundreds of end users per customer (SAP developers, analysts, process owners and architects) and make sure the product "lands and sticks".

The service lets a strategist:
- create a customer account (tenant) and invite its users
- track each user through four stages: `invited → activated → first_use → active`
- apply a reusable **playbook** (ordered steps for each stage) to every account, so the team can take on more accounts without hiring at the same rate
- see who is stuck, a cached rollout summary for each account, and the average time spent in each stage

Customer admins can only ever see their own tenant. Security and tenant isolation are first-class features.

**Use only fictional data** (e.g. "Example Manufacturing GmbH", "Demo Logistics AG"). Never use real company or person names in code, seeds or tests.

**Facts discipline:** never state Conduct's headcount; never mention CBS as a customer (unverified); never model seed tenants on real customers (no "Daimler-style" tenant); any claim about Conduct in the README needs a source link; label the 80/50/30% figures as Conduct's own claims. Full rules in `.cursor/rules/product-alignment.mdc`.

## 2. Tech stack (do not add anything else without asking me first)

- Python 3.12, FastAPI, Pydantic v2, pydantic-settings
- PostgreSQL 16, SQLAlchemy 2.0 (typed `Mapped[]` style, **sync** sessions), psycopg 3, Alembic
- Redis 7 with the `redis` package
- PyJWT for access tokens, `argon2-cffi` for password hashing, `secrets` + `hashlib` (SHA-256) for invite tokens
- pytest, FastAPI `TestClient` (httpx), a real Postgres test database (no SQLite)
- uv for dependency management, ruff (lint + format), mypy `--strict`
- Docker + Docker Compose (api, postgres, redis)
- GitHub Actions CI

## 3. Non-negotiable code quality rules

These apply to every phase. If a rule conflicts with speed, the rule wins.

1. **Fully typed.** `mypy --strict` passes with zero errors. No `Any` unless it is unavoidable and has a comment explaining why. No `# type: ignore` without a specific error code and a reason.
2. **Lint clean.** `ruff check` and `ruff format --check` pass. Enable rule sets `E, F, I, B, UP, SIM, S, N, RUF`.
3. **Layered architecture.** Routers handle only HTTP. Services hold the business logic. Models and repositories handle only data access. No SQL or business rules inside routers.
4. **No sloppiness.** No commented-out code, no `print`, no TODO/FIXME, no bare `except`, no unused imports or variables, no magic numbers (use named constants or settings), no duplicated logic.
5. **Errors.** Define domain exceptions (e.g. `NotFoundError`, `InvalidStageTransitionError`, `InviteExpiredError`) and map them to HTTP responses in one exception handler. Never leak stack traces or internal details to clients.
6. **Time.** Every datetime is timezone-aware UTC. Never use naive datetimes.
7. **Secrets.** All config comes from environment variables via pydantic-settings. Commit `.env.example`, never `.env`. No secrets in code.
8. **Transactions.** Each state change (e.g. a stage move plus its `StageEvent`) is one atomic transaction.
9. **Small, named units.** Functions do one thing. Public service functions get a one-line docstring. Names are explicit (`advance_user_stage`, not `update`).
10. **Tests ship with the code.** Every phase adds tests for what it built. Tests are deterministic and independent: each test runs in a transaction that is rolled back, and time is controlled with an injectable clock, never `sleep`.
11. **Logging.** Structured logging (JSON in production, readable in dev). **Never log emails, names, passwords, tokens or JWTs.** Log IDs only.
12. **Decisions log.** Keep `docs/decisions.md`. For every non-obvious design choice, add 2–4 lines: the decision, the alternatives considered, and why. I will be defending these in an interview.
13. **Git workflow.** Each phase is built on its own branch, named `phase-N-<short-name>` (e.g. `phase-1-data-model`), created from an up-to-date `main`. Make one conventional commit per logical change (`feat:`, `fix:`, `test:`, `chore:`, `docs:`). **Never push, merge or open pull requests yourself.** At the end of a phase, tell me the branch name and the commit messages. I push, open the pull request, and merge once **CI** and **OpenQodex** (the security scan in `.github/workflows/openqodex.yml`) both pass. If OpenQodex reports findings, I'll paste them to you: fix the cause, don't suppress the warning.
14. If something is ambiguous, **ask me** instead of guessing. Do not invent features I haven't listed.

## 4. Target project structure

```
app/
  main.py              # app factory, exception handlers, router registration
  config.py            # Settings (pydantic-settings)
  db.py                # engine, session factory, get_session dependency
  cache.py             # Redis client + cache helpers
  logging.py           # structured logging setup
  clock.py             # injectable UTC clock
  models/              # SQLAlchemy models, one file per aggregate
  schemas/             # Pydantic request/response models
  services/            # business logic
  api/                 # routers + dependencies (auth, scoping)
  security/            # jwt, password hashing, invite tokens
  errors.py            # domain exceptions
migrations/            # Alembic
scripts/seed.py        # fictional demo data
tests/
  conftest.py
  unit/
  integration/
docs/decisions.md
docker-compose.yml
Dockerfile
Makefile               # make up / down / test / lint / typecheck / migrate / seed
pyproject.toml
.env.example
.github/workflows/ci.yml
README.md
```

---

## Phase 0: Scaffold (about 45 minutes)

- Set up the uv project, pyproject with ruff/mypy/pytest config, Dockerfile (multi-stage, non-root user), docker-compose with `api`, `postgres`, `redis` and a separate `postgres_test` database, plus healthchecks.
- Settings, DB session dependency, Redis client, logging, injectable clock.
- `GET /health` returns `{"status": "ok"}` and checks DB and Redis connectivity (returns 503 if either is down).
- Makefile targets and a GitHub Actions workflow that runs lint, typecheck and tests against Postgres and Redis service containers.

**Definition of done:** `make up` starts everything; `make lint`, `make typecheck` and `make test` pass; the health test passes; CI config is valid.

**Status: done.** Git, the per-phase branch workflow and the OpenQodex pull-request security scan were added after Phase 0. Start Phase 1 on a new branch, `phase-1-data-model`.

## Phase 1: Data model + migration (about 1 hour)

Create these models and one Alembic migration:

- **Tenant**: id (UUID), name, created_at.
- **User**: id, tenant_id (nullable; only strategists may have none, enforced with a CHECK constraint), email (unique **per tenant**), password_hash (nullable until the invite is accepted), role enum (`strategist`, `customer_admin`, `end_user`), sap_role enum (`developer`, `analyst`, `process_owner`, `architect`; nullable for strategists), stage enum (`invited`, `activated`, `first_use`, `active`), stage_changed_at, created_at.
- **Invite**: id, user_id, token_hash (SHA-256 hex, unique), expires_at, used_at (nullable).
- **StageEvent**: append-only history. id, tenant_id, user_id, from_stage (nullable), to_stage, occurred_at. Indexed on (tenant_id, user_id).
- **StrategistAssignment**: strategist_id + tenant_id as a composite primary key, assigned_at. Many-to-many, so one strategist can cover many accounts and one account can have several strategists.
- **Playbook**: id, tenant_id (nullable; null means the global default template), name, created_at.
- **PlaybookStep**: id, playbook_id, stage, position, title, description, due_within_days. Unique on (playbook_id, stage, position).

Add indexes for the queries we will run (users by tenant + stage, users by tenant + stage_changed_at).

**Definition of done:** the migration applies and rolls back cleanly; integration tests prove that per-tenant email uniqueness works, that the strategist CHECK constraint works, and that a duplicate assignment is rejected; `docs/decisions.md` explains: email unique per tenant, `stage_changed_at` on the user row alongside the `StageEvent` history, token hash only, and the join table for assignments.

## Phase 2: Core API (about 2 hours)

Services and endpoints (no auth yet; put a clearly isolated temporary dependency in place that Phase 3 replaces):

- `POST /tenants`: creates the tenant and **copies the default playbook** into a tenant-specific playbook in the same transaction.
- `POST /tenants/{tenant_id}/invites`: creates an `invited` user with sap_role, generates a token with `secrets.token_urlsafe(32)`, stores only its SHA-256 hash, sets expiry from settings (default 72h), and returns the raw token **once** in the response.
- `POST /invites/accept`: takes a token and a password. Rejects tokens that are expired, already used or unknown, all with the same generic error. Hashes the password with argon2, marks the invite as used, moves the user to `activated` and writes a `StageEvent`, all in one transaction.
- `POST /tenants/{tenant_id}/users/{user_id}/advance`: moves the user forward **exactly one stage**. Skipping, going backwards or advancing past `active` raises `InvalidStageTransitionError` (409). Updates `stage_changed_at` and writes a `StageEvent` atomically.
- `GET /tenants/{tenant_id}/users`: filter by stage and sap_role, cursor or limit/offset pagination with a max page size, stable ordering.
- `GET /tenants/{tenant_id}/playbook`: the tenant's playbook steps grouped by stage.
- `GET /tenants/{tenant_id}/users/{user_id}/next-steps`: the playbook steps for the user's current stage.

**Definition of done:** unit tests for the stage-transition rules (every valid and invalid transition); integration tests for every endpoint, including invite expiry (using the injectable clock), reuse of a used invite, and playbook copying; OpenAPI at `/docs` shows typed request and response schemas with examples.

## Phase 3: Security and tenant isolation (about 2 hours)

- `POST /auth/token` (email + password + optional tenant) returns a short-lived JWT with `sub`, `role`, `tenant_id` and `exp`. The signing key and expiry come from settings. Use HS256, validate `exp`, and reject a token signed with the wrong algorithm.
- `get_current_user` dependency. Replace the Phase 2 temporary dependency everywhere.
- **One** scoping function, `accessible_tenant_ids(user)`: a customer admin gets their own tenant; a strategist gets the tenants in `StrategistAssignment`; an end user gets no management access. Every tenant-scoped query goes through it.
- A request for a tenant the caller can't access returns **404, not 403**, so callers can't discover which tenants exist. Record this in `docs/decisions.md`.
- Permissions: only strategists create tenants and assignments; strategists and customer admins can invite users and advance stages within their scope.
- `POST /tenants/{tenant_id}/strategists/{strategist_id}`: assign a strategist (strategist-only).
- Make sure no log line contains an email, password, token or JWT. Add a test that captures the logs during the invite and login flow and asserts this.

**Definition of done:** an integration test matrix proves that a customer admin of tenant A gets 404 on every tenant B endpoint, that an unassigned strategist can't see a tenant, and that an assigned one can; tests cover expired and tampered JWTs; all checks are green.

## Phase 4: Rollout summary, stuck users, time per stage, Redis cache (about 2 hours)

- `GET /tenants/{tenant_id}/summary`: count of users per stage, count per sap_role per stage, number stuck (no stage change for `STUCK_AFTER_DAYS`, default 7, from settings), and **average days spent in each stage**, calculated from `StageEvent`. Computed in SQL with aggregates, not Python loops.
- `GET /tenants/{tenant_id}/stuck`: paginated list of stuck users with their current stage, days stuck and next playbook step.
- Cache the summary in Redis under a versioned key (e.g. `summary:v1:{tenant_id}`) with a TTL from settings. **Invalidate it after the transaction commits** whenever a user is invited, accepts an invite or changes stage. Never invalidate before the commit: explain the race condition in `docs/decisions.md`.
- If Redis is unavailable, log a warning (with no personal data) and serve the summary straight from the database. Redis must never become a single point of failure.

**Definition of done:** tests prove (1) a cache hit doesn't query the DB, (2) the summary is never stale after a stage change, invite or acceptance, (3) the endpoint still works with Redis down, and (4) stuck detection and average-days maths are correct, using the injectable clock.

## Phase 5: Seed data and polish (about 45 minutes)

- `scripts/seed.py` (`make seed`): two fictional tenants ("Example Manufacturing GmbH" and "Demo Logistics AG"), one strategist assigned to both, a customer admin for each, about 40 end users spread across stages and SAP roles with realistic `StageEvent` histories (some stuck), and a default playbook with sensible steps (e.g. *Activated: 30-minute guided walkthrough within 3 days*; *First use: run first system question on own custom code within 7 days*). Running it twice must not create duplicates.
- Review the whole codebase for consistency, dead code, naming and missing tests. Fix anything you find and list the changes.

**Definition of done:** `make seed` runs twice without errors or duplicates; all checks green; test coverage report generated (aim for 90%+ on `services/` and `security/`).

## Phase 6: README (about 45 minutes)

Write `README.md` with:
1. A one-line pitch: *"Conduct makes SAP knowledge available at scale. This tool tries to do the same for deployment knowledge."*
2. **Why this exists:** a small GTM team onboarding hundreds of users per enterprise account; reusable playbooks so capacity grows without matching headcount growth. Present this as my assumption about how the team works today, not as fact.
3. Features list.
4. An architecture diagram in Mermaid (API → services → Postgres, Redis cache, invalidation on commit).
5. Security model: tenant isolation, roles, invite token hashing, 404 vs 403, no personal data in logs.
6. Quick start: `cp .env.example .env`, `make up`, `make migrate`, `make seed`, open `/docs`, with an example walkthrough using curl.
7. Testing: how to run the tests and what the critical tests prove.
8. Design decisions: link to `docs/decisions.md`.
9. Next steps (not built): reminder emails via a background worker, Kubernetes deployment, SSO/SAML for enterprise customers, usage-based health signals.

**Definition of done:** a new reader can clone the repo and get it running with only the README; every command in it has been run and works.

---

Start with **Phase 0** now. Before writing code, list the files you will create and any assumptions you're making, then build it.

# Phase log

What each build phase shipped. Updated at the end of every phase before waiting for `continue`.

## Phase 0 — Scaffold

**Branch / release:** `phase-0-scaffold` · [release](https://github.com/mohamedalsayed12/conduct-playbook-builder/releases/tag/phase-0-scaffold)

- uv project with ruff, mypy `--strict`, pytest; multi-stage Dockerfile (non-root); Compose for `api`, `postgres`, `redis`, `postgres_test`.
- Settings via pydantic-settings, DB session dependency, Redis client, structured logging, injectable UTC clock.
- `GET /health` with DB/Redis checks (503 + dependency booleans on failure).
- Makefile + GitHub Actions CI (lint, typecheck, tests against Postgres/Redis).
- Later follow-ups on this foundation: git/per-phase branch workflow, OpenQodex PR scanners.

## Phase 1 — Data model

**Branch / release:** `phase-1-data-model` · [release](https://github.com/mohamedalsayed12/conduct-playbook-builder/releases/tag/phase-1-data-model) · commit folded into `da74eb2` catch-up

- SQLAlchemy models + Alembic migration: Tenant, User, Invite, StageEvent, StrategistAssignment, Playbook, PlaybookStep.
- Constraints: email unique per tenant, token hash only, strategist CHECK, assignment composite PK, playbook step uniqueness.
- Indexes for tenant+stage and tenant+stage_changed_at queries.
- Integration tests for uniqueness, strategist CHECK, duplicate assignment rejection.
- Design decisions recorded in `docs/decisions.md`.

## Phase 2 — Core API

**Branch / PR / release:** `phase-2-core-api` · [#8](https://github.com/mohamedalsayed12/conduct-playbook-builder/pull/8) · [release](https://github.com/mohamedalsayed12/conduct-playbook-builder/releases/tag/phase-2-core-api)

- Tenant create (copies default playbook), invites/accept, stage advance, user list, playbook + next-steps.
- Temporary `Phase2TemporaryCaller` auth stub for Phase 3 to replace.
- Domain exceptions → HTTP; OpenAPI schemas with examples.
- Unit tests for stage transitions; integration tests for invites/expiry/playbook copy.

## Phase 3 — Security and tenant isolation

**Branch / PR / release:** `phase-3-security` · [#9](https://github.com/mohamedalsayed12/conduct-playbook-builder/pull/9) · [release](https://github.com/mohamedalsayed12/conduct-playbook-builder/releases/tag/phase-3-security) · closes #2

- `POST /auth/token` → short-lived HS256 JWT; `get_current_user` replaces the Phase 2 stub.
- `accessible_tenant_ids` on every tenant-scoped route; inaccessible tenants → **404 not 403**.
- Permissions: strategists create tenants/assignments; strategists + customer admins invite/advance in scope.
- Auto-assign creating strategist on tenant create; assign-strategist endpoint.
- Log scrubbing (no emails/passwords/tokens/JWTs); security matrix + scrubbing tests (48 tests green).

## Phase 4 — Rollout summary, stuck users, Redis cache

**Branch / PR / release:** `phase-4-rollout-summary` · [#10](https://github.com/mohamedalsayed12/conduct-playbook-builder/pull/10) · [release](https://github.com/mohamedalsayed12/conduct-playbook-builder/releases/tag/phase-4-rollout-summary) · closes #3

- `GET /tenants/{id}/summary`: users per stage, sap_role×stage counts, stuck count, average days per stage from `StageEvent` (SQL aggregates).
- `GET /tenants/{id}/stuck`: paginated stuck users with days stuck and next playbook step.
- Redis cache `summary:v1:{tenant_id}` with TTL; invalidate only after commit on invite / accept / advance.
- Redis-down falls back to Postgres; decisions recorded for post-commit invalidation.
- Tests: cache hit skips DB, invalidation freshness, Redis down, stuck + average-days maths.

## Phase 5 — Seed data and polish

**Branch / PR / release:** `phase-5-seed-polish` · [#11](https://github.com/mohamedalsayed12/conduct-playbook-builder/pull/11) · [release](https://github.com/mohamedalsayed12/conduct-playbook-builder/releases/tag/phase-5-seed-polish) · closes #4

- Idempotent `scripts/seed.py` / `make seed`: Example Manufacturing GmbH + Demo Logistics AG, one strategist on both, admins, 40 end users with StageEvent histories (some stuck), default playbook steps.
- Shared `app/seed_data.py` constants; factories reuse default playbook steps.
- Public `get_default_playbook` / `copy_playbook_to_tenant`; `make cov` (≥90% on `services/` + `security/`, measured 95%).
- Seed idempotency + shape tests; decisions for natural-key seeding.

## Phase 6 — README

**Branch:** `phase-6-readme` (PR/release links filled at merge) · closes #5

- Full README: pitch, why-it-exists (as assumption), features, Mermaid architecture, security model, quick start + curl walkthrough, testing, decisions link, next steps.
- Verified host commands: `make up`, `make migrate`, `make seed`, health/auth/tenant/summary curls against local API.

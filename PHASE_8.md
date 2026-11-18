# Phase 8 — Production Engineering Blueprint

## Purpose

Turn the completed PAAI autonomy runtime into a deployable, observable, maintainable service with a secure HTTP boundary, durable operations, background workers, operational controls, and deployment automation.

Phase 8 builds on the stable service interfaces delivered in Phase 7. It must not replace the agent, memory, orchestration, or autonomy layers with a second application architecture.

## Target architecture

Client → HTTPS reverse proxy → FastAPI application → authentication middleware → authenticated request context → application services → durable repositories.

Background worker → persistent scheduler/goal queue → autonomy engine → existing agent/workflow runtime.

Shared infrastructure:
- SQLite for local development and single-instance deployment; repository interfaces must allow a future PostgreSQL adapter.
- Encrypted credential storage using a dedicated encryption key from the environment/secret manager.
- Structured logs, health/readiness endpoints, metrics, request IDs, and audit records.
- Docker deployment for repeatable local/host deployment, with non-root runtime and health checks.

## Module plan

### HTTP application
- `app/api/main.py`: FastAPI application factory and lifespan.
- `app/api/dependencies.py`: bearer-token authentication, identity_scope dependency, runtime dependency.
- `app/api/schemas.py`: request/response schemas; never expose credential material.
- `app/api/routes/auth.py`: registration and login.
- `app/api/routes/goals.py`: create/list/get/pause/resume/cancel/run-now.
- `app/api/routes/runs.py`: authenticated run history and status.
- `app/api/routes/approvals.py`: list and respond to pending approvals.
- `app/api/routes/health.py`: liveness/readiness.

### Production controls
- `app/production/settings.py`: typed environment configuration and fail-fast validation.
- `app/production/logging.py`: structured JSON logging and secret redaction.
- `app/production/middleware.py`: request ID, security headers, bounded request size, safe CORS.
- `app/production/crypto.py`: authenticated encryption for integration credentials.
- `app/production/rate_limit.py`: per-client and per-account login/API rate limiting with a pluggable store.
- `app/production/worker.py`: supervised worker entry point calling the Phase 7 scheduler.
- `app/production/metrics.py`: basic process and queue metrics without exposing user data.

### Persistence and deployment
- Durable repository interfaces and migrations for auth, goals, runs, approvals/audit, credentials, and permission grants.
- PostgreSQL adapter is the target for multi-instance deployment; SQLite remains a supported local mode.
- Dockerfile, docker-compose configuration, environment template, startup scripts, and deployment/runbook docs.
- CI workflow for lint, compile, unit/integration tests, dependency checks, and container build.

## API contract

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me`
- `POST /api/v1/goals`
- `GET /api/v1/goals`
- `GET /api/v1/goals/{goal_id}`
- `POST /api/v1/goals/{goal_id}/pause`
- `POST /api/v1/goals/{goal_id}/resume`
- `POST /api/v1/goals/{goal_id}/cancel`
- `POST /api/v1/goals/{goal_id}/run`
- `GET /api/v1/goals/{goal_id}/runs`
- `GET /api/v1/approvals`
- `POST /api/v1/approvals/{approval_id}/approve`
- `POST /api/v1/approvals/{approval_id}/reject`
- `GET /health/live`
- `GET /health/ready`

Every authenticated endpoint derives tenant identity from a verified bearer token. User IDs in request bodies are rejected/ignored; never use them as authorization evidence.

## Security requirements

- Production secrets are required and validated at startup; no development fallback secret.
- Password hashing remains PBKDF2 for compatibility unless a reviewed migration to Argon2id is included.
- Access tokens remain short-lived. Add revocation/version checking and a documented logout strategy.
- Credential encryption uses authenticated encryption (Fernet/AES-GCM) with key rotation guidance. Encryption keys never share the database or repository.
- Rate-limit login and sensitive operations; avoid account enumeration in authentication errors.
- CORS is explicit, not wildcard with credentials.
- HTTPS is required at deployment ingress.
- Request size/timeouts and allowed hosts are bounded.
- Logs redact passwords, tokens, authorization headers, OAuth codes, and credential payloads.
- API errors never expose stack traces or provider secrets.
- Background worker re-establishes tenant identity from persisted goal ownership before running each job.
- High-risk actions continue to require Phase 5 approval.

## Reliability and operations

- Worker claims persisted jobs atomically and handles graceful shutdown.
- Retries use bounded exponential backoff with jitter and idempotency keys.
- Dead-letter/failed jobs are inspectable and can be retried by an authorized operator.
- Readiness checks verify required dependencies; liveness does not depend on external LLM availability.
- Database migrations are versioned and repeatable.
- Backups, restore steps, retention, and incident response are documented.
- Metrics cover request latency/errors, queue depth/age, run outcomes, approvals waiting, and worker health.

## Implementation sequence

1. Stabilize Phase 7 interfaces and add production settings.
2. Add durable repository/migration interfaces and encrypted credential persistence.
3. Add FastAPI application, schemas, auth dependency, and route groups.
4. Add approval and run APIs with ownership checks.
5. Add worker entry point and graceful shutdown.
6. Add logging, redaction, middleware, rate limiting, health, and metrics.
7. Add Docker and CI workflows plus deployment/runbook docs.
8. Add API/security/worker integration tests and full regression suite.

## Test plan

- Authentication and tenant isolation at every route.
- Expired, malformed, tampered, and revoked tokens rejected.
- Password/credential/token values absent from logs and API responses.
- CORS, host, request-size, and rate-limit behavior.
- Goal CRUD and run/approval ownership enforcement.
- Worker restart, duplicate delivery, graceful shutdown, and idempotency.
- Credential encryption/decryption, wrong-key failure, and rotation behavior.
- Database migration from the existing SQLite schema.
- Health/readiness behavior when dependencies are unavailable.
- Container starts as non-root and passes health check.
- Full Phase 1–7 regression suite remains intact.

## Acceptance criteria

- [ ] HTTP API exposes the documented authenticated operations.
- [ ] Authentication middleware creates trusted identity scope for every protected request.
- [ ] Persistent goal/run/approval/credential stores survive restart.
- [ ] Credential encryption and secret redaction are verified.
- [ ] Worker executes persisted due work and shuts down gracefully.
- [ ] Rate limits, CORS, request bounds, health, logs, and metrics work.
- [ ] Docker and CI pipelines are committed and reproducible.
- [ ] API/security/worker integration and regression tests pass.
- [ ] Deployment and operational runbooks are complete.
- [ ] Phase 8 engineering review and final MCQ assessment complete.

## Explicit production caveat

A repository containing deployment files is not itself proof of a secure production deployment. Real production readiness still requires secret provisioning, HTTPS ingress, database backups, dependency scanning, load/security testing, alerting, and a live deployment exercise in the target environment.

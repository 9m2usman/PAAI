# Phase 8 — Production Engineering

## Goal

Provide a real application boundary around PAAI: authenticated HTTP endpoints, request controls, background worker entry point, deployment packaging, CI, and an operational runbook. This is a production-oriented foundation, not a claim that a live deployment is already secure or available.

## Architecture

Client → HTTPS reverse proxy supplied by deployment host → FastAPI → bearer-token verification → request-local identity scope → existing authenticated services.

A separate worker process loads the same runtime and iterates trusted principals from the authentication repository. It establishes an identity scope for each tenant before running that tenant's due-goal scheduler tick.

## Implemented components

### HTTP API
- `app/api/main.py`: application factory and lifespan.
- `app/api/dependencies.py`: bearer-token authentication and request-local identity scope.
- `app/api/schemas.py`: bounded request/response models.
- `app/api/routes/auth.py`: registration, login, current-user endpoint.\n- `app/api/routes/google_oauth.py`: authenticated connect/status/disconnect and state-bound OAuth callback.
- `app/api/routes/goals.py`: create/list/get/pause/resume/cancel/run-now and run history.\n- `app/api/routes/events.py`: authenticated durable event ingestion for registered event-goal triggers.\n- `app/api/routes/workflows.py`: authenticated Phase 5 workflow execution, inspection, approval, rejection, and resume endpoints.\n- `app/api/routes/permissions.py`: owner-scoped grants and revocation for explicitly allowlisted integration actions; automatic permission grants are not exposed.
- `app/api/routes/health.py`: liveness and readiness.
- Every goal route calls tenant-scoped services. No route accepts a user ID as proof of identity.

### Operational controls
- `app/production/settings.py`: environment-backed configuration and required authentication secret validation.
- `app/production/middleware.py`: request IDs, response security headers, Content-Length request-size bound, and process-local per-IP rate limit.
- `app/production/logging.py`: best-effort redaction filter for common token/password/secret patterns.
- `app/production/crypto.py`: Fernet authenticated-encryption helper for credential values.\n- `app/security/credential_manager.py`: SQLite-backed, per-user credential storage; token payloads are encrypted with Fernet and connections close deterministically.
- `app/production/worker.py` and `worker_main.py`: supervised polling worker that establishes the authenticated identity for each account before scheduler execution.

### Deployment and automation
- `Dockerfile`: Python container running as a non-root user with a health check.
- `docker-compose.yml`: single-host persistent data volume.
- `.github/workflows/ci.yml`: dependency install, compile check, and full unittest suite.
- `PRODUCTION_RUNBOOK.md`: configuration, container start, worker start, backup, and operations notes.

## API routes

- `GET /api/v1/integrations/google/connect` (authenticated; returns Google authorization URL)\n- `GET /auth/google/callback` (Google redirect; validates one-time OAuth state)\n- `GET /api/v1/integrations/google/status` (authenticated)\n- `DELETE /api/v1/integrations/google/disconnect` (authenticated)\n- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me`
- `POST /api/v1/events` (authenticated; idempotent event ingestion and matching event-goal queue)\n- `GET /api/v1/permissions` (list the current user's integration permissions)\n- `POST /api/v1/permissions` (grant one supported integration action)\n- `DELETE /api/v1/permissions/{integration}/{action}` (revoke an action permission)\n- `POST /api/v1/workflows` (authenticated; plan and start an integration workflow)\n- `GET /api/v1/workflows/{workflow_id}` (owner-scoped workflow status)\n- `POST /api/v1/workflows/{workflow_id}/approve` (approve the exact pending action and resume)\n- `POST /api/v1/workflows/{workflow_id}/reject` (reject the pending action)\n- `POST /api/v1/goals`
- `GET /api/v1/goals`
- `GET /api/v1/goals/{goal_id}`
- `POST /api/v1/goals/{goal_id}/pause`
- `POST /api/v1/goals/{goal_id}/resume`
- `POST /api/v1/goals/{goal_id}/cancel`
- `POST /api/v1/goals/{goal_id}/run`
- `GET /api/v1/goals/{goal_id}/runs`
- `GET /health/live`
- `GET /health/ready`

Interactive API docs are disabled by default. Set `PAAI_ENABLE_DOCS=true` only in a trusted development environment.

## Configuration

Required:
- `GROQ_API_KEY` for the default reasoning-only goal executor.
- `PAAI_AUTH_SECRET`, a random secret of at least 32 characters.

Optional settings are listed in `.env.example`. Configure explicit trusted origins in `PAAI_CORS_ORIGINS`; leave empty when no browser frontend is used.

## Run locally on Windows

```powershell
.\\venv\\Scripts\\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
# Edit .env and configure GROQ_API_KEY and PAAI_AUTH_SECRET
.\\venv\\Scripts\\python.exe -m uvicorn app.api.main:app --host 127.0.0.1 --port 8000
```

Run the worker in a second PowerShell window:

```powershell
.\\venv\\Scripts\\python.exe -m app.production.worker_main
```

## Security boundaries and known gaps

- TLS termination, trusted proxy configuration, firewall, managed secrets, backups, and host monitoring must be supplied by the deployment environment.
- Rate limiting is in-memory and per process/IP; it is not distributed and is not a substitute for an edge/API gateway.
- Request-size middleware checks Content-Length; an upstream reverse proxy must also enforce body-size and connection limits.
- Logging redaction is best-effort. Application code must never log raw credentials, prompts containing secrets, or authorization headers.
- Google OAuth credentials are stored per user in `PAAI_CREDENTIAL_DATABASE`, encrypted at rest with `PAAI_CREDENTIAL_ENCRYPTION_KEY`. Back up the key separately; losing it makes stored credentials unrecoverable. OAuth authorization state is single-use and expires after ten minutes; pending state is currently process-local, so keep the API as one process during OAuth callback.
- Phase 5 workflow execution and exact-action approval/resume are now exposed through authenticated API routes. Users can grant only actions advertised by registered connectors; high-risk and non-automatic medium-risk actions still require approval. The workflow manager and approval manager are still process-local, so pending workflows do not survive an API process restart. They are not yet linked back to a paused Phase 7 autonomy run; that cross-lifecycle persistence/resume integration remains outstanding.
- The default autonomy executor performs reasoning only. A trusted custom executor is required for external actions, and must use Phase 5 permissions and risk/approval controls.
- Worker and API use SQLite and are intended for a single-host deployment. Multiple replicas need PostgreSQL and shared job leases/queue.
- Token revocation, refresh-token rotation, email verification, password reset, and account lockout are not implemented.
- No live deployment, load test, penetration test, backup restore exercise, or external-provider verification has been performed.

## Verification

```powershell
.\\venv\\Scripts\\python.exe -m compileall -q app tests
.\\venv\\Scripts\\python.exe -m unittest discover -s tests -v
```

The Phase 8 test module includes credential encryption round-trip/wrong-key tests and authenticated API tenant-isolation tests. The CI workflow runs the complete suite on pushes and pull requests.

## Acceptance checklist

- [x] Authenticated FastAPI application and route modules authored.
- [x] Request identity scope derived from verified bearer tokens.
- [x] Authenticated goal operations and tenant checks.\n- [x] Authenticated durable event ingestion and event-goal dispatch.\n- [x] Authenticated Phase 5 workflow, permission grant/revocation, and exact-action approval/resume API integration.\n- [ ] Durable workflow/approval state and automatic resumption of the originating autonomy run.
- [x] Health endpoints and basic request controls.
- [x] Worker process entry point with per-account identity scope.
- [x] Fernet encryption utility wired into persistent per-user Google credential storage.\n- [x] Google OAuth connect/callback/status/disconnect API routes.
- [x] Docker and Compose configuration.
- [x] GitHub Actions CI workflow.
- [x] Production runbook and configuration template.
- [x] Focused Phase 8 tests authored.
- [ ] Local installation, compile, full regression, and API tests run by the user.
- [ ] CI workflow result verified.
- [ ] Security review and deployment exercise completed.
- [ ] Phase 8 MCQ assessment completed.

# PAAI — Personal Autonomous Agent Infrastructure

PAAI is a reusable autonomous-agent platform built as one continuous codebase. Its roadmap progresses from a first agent to memory, orchestration, real-world workflows, multi-user identity, advanced autonomy, and production engineering.

## Roadmap

1. Understanding AI agents
2. Building the first autonomous agent
3. Memory and personalization
4. Multi-agent orchestration
5. Real-world workflow execution
6. Multi-user agent infrastructure
7. Advanced autonomy
8. Production engineering

## Technology

- Python and Groq LLM API
- SQLite for the current persistence layer
- FastAPI and Uvicorn for the HTTP application and local dashboard
- Gmail and Google Calendar REST integrations
- Playwright for optional allowlisted browser automation
- Docker and GitHub Actions

## Project structure

- `app/agents/` — agent implementations
- `app/core/` — configuration, LLM client, and state
- `app/memory/` — memory, personalization, authenticated memory facade
- `app/orchestration/` — multi-agent orchestration
- `app/integrations/` — external service connectors and OAuth
- `app/security/` and `app/access/` — credentials, permissions, authorization
- `app/approvals/` — deterministic risk and approval management
- `app/execution/` and `app/workflows/` — controlled integration execution
- `app/auth/`, `app/identity/`, `app/tenancy/` — authentication and tenant identity
- `app/autonomy/` — persistent goals, scheduler, policy, and autonomous execution
- `app/api/` — FastAPI routes and request authentication
- `app/web/` — local browser-based control center
- `app/production/` — settings, middleware, worker, logging, and encryption utility
- `tests/` — automated tests

## Windows setup

```powershell
python -m venv venv
.\\venv\\Scripts\\python.exe -m pip install --upgrade pip
.\\venv\\Scripts\\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Configure `GROQ_API_KEY` and set `PAAI_AUTH_SECRET` to a random value of at least 32 characters. Configure Google OAuth values and the Fernet credential-encryption key if you intend to connect Google. Never commit `.env`.

## Run PAAI

Install dependencies (including Uvicorn) and start the application:

```powershell
.\\venv\\Scripts\\python.exe -m pip install -r requirements.txt
.\\venv\\Scripts\\python.exe -m uvicorn app.api.main:app --host 127.0.0.1 --port 8000
```

Open **http://127.0.0.1:8000** for the PAAI Control Center. The API is also available at `http://127.0.0.1:8000`. Interactive API docs are disabled unless `PAAI_ENABLE_DOCS=true`.

The dashboard supports account registration/sign-in, goal creation and execution, goal run history, manual integration workflows, Google OAuth connection status, per-action permission grants/revocation, and approval/rejection of pending workflows. It is served by the same FastAPI process, so no separate frontend server or CORS setup is needed.

## Run the background worker

```powershell
.\\venv\\Scripts\\python.exe -m app.production.worker_main
```

The worker uses the same databases and authentication secret as the API.

## Run tests

```powershell
.\\venv\\Scripts\\python.exe -m compileall -q app tests
.\\venv\\Scripts\\python.exe -m unittest discover -s tests -v
```

## Safety model

- User identity comes from a verified bearer token, not an LLM response or request-body user ID.
- Goal and memory operations derive tenant identity from the authenticated request context.
- Phase 5 tool permissions and deterministic risk/approval rules remain the boundary for external side effects.
- Phase 7's default goal executor is reasoning-only; integration-backed autonomous goal execution is opt-in with `PAAI_ENABLE_INTEGRATION_GOAL_EXECUTOR=true`.
- High-risk actions such as sending email require human approval even if an integration permission exists.
- Interrupted external actions are not automatically replayed; their outcome must be inspected.
- Never place credentials or tokens in prompts or logs.

## Production limitations

This repository contains a production-oriented application foundation, not proof of production readiness. The current deployment uses single-host SQLite. TLS ingress, managed secret storage, backups, monitoring/alerting, and a live deployment exercise remain host/operator responsibilities. The Fernet helper is not yet integrated into a durable encrypted OAuth credential vault. Distributed worker coordination and PostgreSQL remain future hardening.

See [PHASE_7.md](PHASE_7.md), [PHASE_8.md](PHASE_8.md), and [PRODUCTION_RUNBOOK.md](PRODUCTION_RUNBOOK.md).

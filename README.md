# PAAI — Personal Autonomous Agent Infrastructure

PAAI is a reusable autonomous-agent codebase. Its roadmap builds from a single agent to personalized memory, multi-agent orchestration, real-world integrations, multi-user isolation, background autonomy, and production deployment.

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

- Python
- Groq LLM API
- SQLite for account and memory storage
- Gmail and Google Calendar REST APIs
- Playwright for optional allowlisted browser automation

## Project structure

- `app/agents/` — agent implementations
- `app/core/` — core runtime and configuration
- `app/memory/` — memory and personalization
- `app/orchestration/` — multi-agent orchestration
- `app/integrations/` — external service connectors and OAuth
- `app/security/` — credentials and permissions
- `app/approvals/` — deterministic risk and approval management
- `app/execution/` — controlled action execution and audit records
- `app/workflows/` — ordered workflow execution
- `app/documents/` — document processing
- `tests/` — automated tests

## Windows setup

Run these commands from the repository root in PowerShell:

```powershell
python -m venv venv
.\\venv\\Scripts\\python.exe -m pip install --upgrade pip
.\\venv\\Scripts\\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Open `.env` and set `GROQ_API_KEY`. Keep `.env` private and never commit it.

Set `PAAI_AUTH_SECRET` in the same local `.env` file to a random value of at least 32 characters. Never commit this secret.

For optional browser automation, install the Chromium browser:

```powershell
.\\venv\\Scripts\\python.exe -m playwright install chromium
```

## Run tests

```powershell
.\\venv\\Scripts\\python.exe -m unittest discover -s tests -v
```

## Phase 5 safety model

- A user must have explicit permission for an integration action.
- Low-risk actions may run automatically after tool permission is granted.
- Medium-risk actions require approval unless that user separately grants automatic permission for the exact action.
- High-risk actions always require human approval.
- Unknown actions default to high risk.
- Approval is bound to exact parameters, expires after 15 minutes by default, and is single-use.
- OAuth credentials are user/integration scoped in the current in-memory prototype.
- Browser automation requires an explicit HTTPS domain allowlist.

See [PHASE_5.md](PHASE_5.md) for workflow usage, OAuth boundaries, tests, and limitations.

## Phase 6 — Multi-user foundation

Phase 6 adds email/password registration, PBKDF2 password hashing, signed expiring HS256 access tokens, a SQLite authentication repository, verified request identity contexts, tenant guards, identity-bound authorization, authenticated profile and memory services, and thread-safe user-scoped credential and permission managers.

The framework-independent runtime authenticates a token and installs the verified identity with `identity_scope` for each request. Use `runtime.memory` for memory operations; its public methods derive the user ID from the current authenticated identity rather than accepting a user ID from the caller.

See [PHASE_6.md](PHASE_6.md) for usage, architecture, security boundaries, and known limitations.

## Security warning

This is a learning/prototype codebase, not a production deployment. Credential, permission, workflow, approval, audit, OAuth-state, and browser-session storage are not yet a complete durable production design. Credentials are not encrypted at rest. The HTTP authentication middleware, token revocation, durable encrypted secrets, persistent workflow/approval/audit stores, and production deployment remain future engineering work.

Never commit `.env`, API keys, OAuth client secrets, access tokens, refresh tokens, or `venv`.

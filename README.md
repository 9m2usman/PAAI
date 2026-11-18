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
- SQLite for the existing memory layer
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
- `app/agents/integration_workflow_agent.py` — validated LLM planning for real-world integration workflows
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
- Low-risk actions may run automatically after permission is granted.
- Medium-risk actions require approval unless that user separately grants automatic permission for the exact action.
- High-risk actions always require human approval.
- Unknown actions default to high risk.
- Approval is bound to exact parameters, expires after 15 minutes by default, and is single-use.
- OAuth credentials are user/integration scoped in the current in-memory prototype.
- Browser automation requires an explicit HTTPS domain allowlist.

See [PHASE_5.md](PHASE_5.md) for workflow usage, OAuth boundaries, tests, and current limitations.

## Security warning

This is a learning/prototype codebase, not a production deployment. Phase 5 stores OAuth credentials, workflow state, approvals, and audit events in memory. Credentials are not encrypted at rest. Authentication, durable tenant isolation, persistent encrypted secrets, a callback web server, and production deployment are future engineering work. Never commit `.env`, API keys, OAuth client secrets, access tokens, or refresh tokens.

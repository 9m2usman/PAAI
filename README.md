# PAAI — Personal Autonomous Agent Infrastructure

PAAI is a reusable autonomous-agent codebase built as one continuous project. Its roadmap progresses from a first agent to memory, multi-agent orchestration, real-world workflows, multi-user identity, advanced autonomy, and production engineering.

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
- SQLite for memory, authentication, profiles, and autonomy records
- Gmail and Google Calendar REST integrations
- Playwright for optional allowlisted browser automation

## Project structure

- `app/agents/` — agent implementations
- `app/core/` — configuration, LLM client, and state
- `app/memory/` — memory and personalization
- `app/orchestration/` — multi-agent orchestration
- `app/integrations/` — external service connectors and OAuth
- `app/security/`, `app/access/`, `app/approvals/` — permissions and controlled execution
- `app/auth/`, `app/identity/`, `app/tenancy/` — multi-user identity
- `app/autonomy/` — persistent goals, scheduling, policy, and execution
- `tests/` — automated tests

## Windows setup

```powershell
python -m venv venv
.\\venv\\Scripts\\python.exe -m pip install --upgrade pip
.\\venv\\Scripts\\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Configure `GROQ_API_KEY` and set `PAAI_AUTH_SECRET` to a random value of at least 32 characters. Never commit `.env`.

## Run tests

```powershell
.\\venv\\Scripts\\python.exe -m compileall -q app tests
.\\venv\\Scripts\\python.exe -m unittest discover -s tests -v
```

## Current phase

**Phase 7 — Advanced Autonomy**

The current implementation supports authenticated goal storage, manual and fixed-interval scheduled execution, pause/resume/cancel controls, run history, a bounded scheduler, and a safe reasoning-only default executor. External actions must use a trusted executor integrated with Phase 5 permission and approval controls.

The Phase 8 production blueprint is documented, but its API/deployment implementation is on the separate `phase8-production-engineering` branch.

## Important limitations

This is a learning-stage system, not a production deployment. The current goal scheduler uses single-host SQLite. Cron/weekday scheduling, durable external event dispatch, approval-resume integration, distributed workers, encrypted persistent OAuth credentials, and production API hosting remain future work.

See [ARCHITECTURE.md](ARCHITECTURE.md), [PHASE_7.md](PHASE_7.md), and [PHASE_8.md](PHASE_8.md).

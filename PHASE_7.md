# Phase 7 — Advanced Autonomy

## Goal

Move PAAI from request/response interaction toward persistent, goal-driven execution. A user can save goals, schedule one-time or recurring runs, manually trigger a run, pause/resume/cancel goals, and inspect run history. Execution is bounded by deterministic policy and records outcomes.

## Architecture

- `app/autonomy/models.py`: goal/run domain models and status vocabulary.
- `app/autonomy/goal_repository.py`: SQLite goal/run persistence; every user-facing operation obtains the owner from `current_identity()`. Due work is claimed in an atomic SQLite transaction.
- `app/autonomy/goal_service.py`: validation and goal lifecycle operations.
- `app/autonomy/policy.py`: hard limits for description size, step budget, runtime budget, retry count, event payload size, and due-goal batch size.
- `app/autonomy/triggers.py`: allowlisted event type validation and payload size checks.\n- `POST /api/v1/events`: authenticated event ingestion with per-user event IDs, durable SQLite storage, duplicate suppression, and queued delivery to matching event goals.
- `app/autonomy/agent_executor.py`: safe default reasoning-only executor. It has no external tools and must not claim side effects.
- `app/autonomy/engine.py`: claims due goals, invokes the injected executor, and persists completed, failed, approval-waiting, or budget-exhausted outcomes.
- `app/autonomy/scheduler.py`: explicit one-tick scheduler; it does not start an unmanaged background thread.
- `app/runtime/multi_user_runtime.py`: composes autonomy services with the existing authenticated PAAI runtime.

## Supported behavior

- Manual goals can be created and run on demand.
- Scheduled goals support one-time ISO-8601 timestamps and fixed recurring intervals (minimum 60 seconds).
- Users can list, inspect, pause, resume, cancel, and request a run for their own goals.
- Run history is persisted separately from goal state.
- The Phase 8 worker can iterate trusted principals from the authentication repository and execute one scheduler tick in each user's identity scope.
- Default execution is reasoning-only through the configured Groq model. A trusted application may inject a different executor, but it must enforce tool permissions, Phase 5 risk/approval rules, tenant ownership, idempotency, and the supplied budgets.

## Data flow

1. An authenticated request installs `identity_scope`.
2. GoalService validates and persists a goal under the current user.
3. The scheduler queries and atomically claims due goals for that identity.
4. The engine creates/updates a run and invokes the configured executor with bounded limits.
5. The outcome is stored; recurring completed goals receive their next interval time.
6. User-facing reads always filter by the current authenticated identity.

## Safety and failure handling

- LLM output cannot set user IDs, change policy limits, grant permissions, or select arbitrary Python callables.
- The default executor has no external tools; external side effects require an explicitly injected trusted executor.
- The existing Phase 5 deterministic risk evaluator and approval manager remain the required safety boundary for integrations.
- Run history stores bounded error text, not credential values.
- Due-goal claims use a database transaction to reduce duplicate runs.
- SQLite is single-host storage; distributed worker leases and cross-host scheduling are not provided.
- The runtime budget is checked after the executor returns; a custom executor must enforce a hard timeout itself.

## Current implementation boundaries

- Fixed-interval recurrence is implemented; cron expressions, weekdays, calendars, and timezone-aware recurrence rules are not yet implemented.
- Event goals can be created with an allowlisted `event_type`. Authenticated event ingestion persists each event and its matching goal deliveries in SQLite. Repeated event IDs are idempotent per user, and multiple queued events for one goal are delivered sequentially without overwriting earlier events.
- The engine can record `awaiting_approval`, but resuming an autonomous goal through a verified Phase 5 approval is still an integration task.
- Default execution is reasoning-only. It does not browse, send email, edit calendars, or run arbitrary tools.
- Retry/idempotency policies are represented in the policy and design, but automatic retry of failed goal runs is not enabled.
- Scheduler cadence is provided by the Phase 8 worker process, not by a built-in timer service.

## Test suite

`tests/phase7/test_autonomy.py` covers tenant isolation, manual execution, recurring rescheduling, pause/cancel, policy validation, and allowlisted event validation.

Run all tests from the project root:

```powershell
.\\venv\\Scripts\\python.exe -m unittest discover -s tests -v
```

## Acceptance checklist

- [x] Tenant-scoped goal and run persistence.
- [x] Manual and fixed-interval scheduled goals.
- [x] Pause, resume, cancel, and run-now operations.
- [x] Atomic due-goal claim.
- [x] Deterministic execution limits and safe reasoning-only default executor.
- [x] Run outcome and history persistence.
- [x] Event type and payload validation.
- [x] Phase 7 focused tests authored.
- [ ] Local focused and full regression tests run by the user.
- [x] Authenticated durable event ingestion, deduplication, and sequential event-goal dispatch.\n- [ ] Verified approval-resume integration between autonomous runs and the Phase 5 workflow approval manager.
- [ ] Engineering review and MCQ assessment.

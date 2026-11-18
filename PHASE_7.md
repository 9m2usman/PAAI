# Phase 7 — Advanced Autonomy

## Purpose

Move PAAI from a request/response agent system to a controlled, goal-driven system that can retain goals, schedule future work, react to trusted events, execute through the existing agent/workflow infrastructure, pause for human approval, recover safely, and report what happened.

This phase builds autonomy controls and orchestration. It does not expose a public HTTP service or claim production deployment; those belong to Phase 8.

## Product behavior

A user can create a goal such as:
- "Every weekday morning, review my latest work inbox and prepare a summary."
- "When a trusted event says a report is ready, analyze it and prepare a draft."
- "Research this topic and continue until the defined completion condition or execution budget is reached."

The system stores the goal under the authenticated user, its schedule/trigger, status, execution history, and next run time. A goal can be paused, resumed, cancelled, inspected, and manually run. A run is bounded by policy and recorded. High-risk external actions remain subject to the existing Phase 5 approval system.

## Architecture and module responsibilities

### 1. Goal domain and persistence
- `app/autonomy/models.py`: validated goal/run data structures and lifecycle states.
- `app/autonomy/goal_repository.py`: SQLite persistence for goals and run history. Every public query derives the tenant from `current_identity()`; no caller-supplied user ID.
- Persist schedule, recurrence, trigger metadata, budget, timestamps, status, last result, and next run.

### 2. Goal application service
- `app/autonomy/goal_service.py`: create, list, get, pause, resume, cancel, and request immediate execution.
- Enforce ownership through authenticated repository methods.
- Validate schedules and limits before saving.

### 3. Trigger system
- `app/autonomy/triggers.py`: typed manual, scheduled, and trusted-event triggers.
- `app/autonomy/trigger_registry.py`: allowlisted event types and deterministic matching.
- External systems do not execute arbitrary code by publishing event payloads. Event payloads are data, validated against registered event schemas.

### 4. Autonomy policy
- `app/autonomy/policy.py`: deterministic maximum runs, maximum steps, execution time budget, retry limits, and allowed autonomy mode.
- Never allow an LLM to raise its own budget or grant itself permissions.
- Never retry an action with external side effects unless its executor declares it idempotent and supplies a stable idempotency key.

### 5. Execution engine
- `app/autonomy/engine.py`: claims due goals, creates run records, calls an injected executor, records outcomes, schedules the next occurrence, and pauses on approval.
- The executor is an application dependency. The model is not allowed to select a tenant, bypass authorization, or call arbitrary Python.
- A run may finish as completed, failed, awaiting approval, cancelled, or budget exhausted.

### 6. Scheduler
- `app/autonomy/scheduler.py`: deterministic `run_due_once()` polling primitive. Phase 8 will host it in a supervised background worker. No unmanaged daemon thread is started by importing application modules.

### 7. Runtime integration
- Extend `MultiUserRuntime` to compose the goal repository, service, trigger registry, policy, engine, and scheduler.
- Keep the Phase 1–6 agent, memory, integration, approval, and identity modules reusable. Avoid a second parallel agent stack.

## Data flow

1. An authenticated application request installs `identity_scope`.
2. GoalService validates the request and stores a tenant-owned goal.
3. Scheduler finds due goals and the engine claims one atomically.
4. Engine checks policy and creates a durable run record.
5. The injected task executor calls the existing PAAI planner/agent or Phase 5 workflow layer.
6. Any approval requirement pauses the goal/run; the user must approve through the trusted application boundary.
7. Engine stores result/error, next run time, and audit metadata.
8. User reads only their own goal and run history.

## Execution lifecycle

`active → running → completed`

Other terminal or paused states:
- `paused`: user or policy paused the goal.
- `awaiting_approval`: a side-effecting step needs explicit approval.
- `failed`: execution failed after safe retry policy.
- `cancelled`: user cancelled the goal.
- `budget_exhausted`: run reached its deterministic limit.

A recurring goal returns to `active` with a new `next_run_at` only after its run has been safely finalized. A one-time goal becomes completed.

## Security and reliability rules

- Tenant ID comes only from verified `current_identity()`.
- SQLite operations use transactions and atomic due-goal claims to reduce duplicate execution.
- A run has a unique ID and idempotency key.
- At-least-once scheduling is expected; external side effects must be protected by idempotency or approval.
- The LLM cannot create arbitrary triggers, change budgets, or authorize actions.
- Trusted events are allowlisted and size-limited.
- User pause/cancel is checked before each execution boundary.
- No credentials are included in prompts, goal text is treated as untrusted input, and tool authorization remains in Phase 5.
- Scheduler polling is single-host in this phase. Cross-process distributed leases and production worker supervision are Phase 8.

## Implementation sequence

1. Define models, status transitions, validation, and deterministic policy.
2. Implement tenant-scoped SQLite repository and run history.
3. Implement GoalService and trigger registry.
4. Implement engine with claim/complete/fail/approval/pause/cancel paths.
5. Implement one-shot scheduler and runtime composition.
6. Add tests for lifecycle, tenant isolation, recurrence, concurrent claims, budgets, retries/idempotency, event validation, and approval pause.
7. Update README and PROJECT_PROGRESS.

## Test plan

- Invalid goal/schedule/recurrence/budget rejected.
- User A cannot list/get/pause/cancel User B goals or runs.
- A due goal is claimed once under concurrent scheduler calls.
- One-time and recurring schedule transitions are correct.
- Paused/cancelled goals never execute.
- Budget exhaustion stops execution.
- Retry only occurs for explicitly idempotent operations.
- Approval result pauses and does not silently resume.
- Unknown event types and oversized payloads are rejected.
- Run outcomes and errors are persisted without secrets.
- Existing Phase 1–6 regression suite remains intact.

## Acceptance criteria

- [ ] Goals and run history persist across process restarts.
- [ ] All goal/run operations are tenant-scoped from authenticated identity.
- [ ] Manual, scheduled, and allowlisted event triggers work.
- [ ] Scheduler safely claims due goals.
- [ ] Engine has bounded execution and safe retry rules.
- [ ] Human approval pauses autonomy.
- [ ] User pause/resume/cancel controls work.
- [ ] Tests and full regression suite pass.
- [ ] Documentation and engineering review complete.
- [ ] Phase 7 MCQ assessment complete.

## Explicit Phase 7 non-goals

- Public HTTP API and web dashboard.
- Production worker deployment, multi-host distributed scheduling, and autoscaling.
- Production secret vault and encryption-at-rest for all stores.
- Kubernetes/cloud deployment automation.
- Autonomous execution without explicit user permissions or risk approval.

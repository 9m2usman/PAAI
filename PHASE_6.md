# Phase 6 — Multi-User Agent Infrastructure

## Objective
Provide a shared PAAI runtime with independently authenticated users and backend-enforced isolation for identity, profiles, memory access boundaries, credentials, and permissions.

## Architecture
Authentication verifies email/password credentials and issues short-lived HS256 bearer tokens. The token verifier checks signature, algorithm, expiry, subject, and email, then resolves the account from SQLite. The resulting IdentityContext is installed for a request with identity_scope. ContextVar keeps concurrent request identities separate.

TenantGuard and AuthorizationService read the current identity rather than accepting an identity selected by an LLM. ProfileService obtains its user ID from the verified context. CredentialManager and PermissionManager retain per-user keys and are protected by re-entrant locks.

## Modules
- app/auth: PBKDF2 password hashing, SQLite account repository, token signing/verification, registration and login.
- app/identity: Principal, IdentityContext, request-local identity scope.
- app/tenancy: ownership guard.
- app/access: permission facade bound to current identity.
- app/profiles: authenticated profile persistence.
- app/runtime: shared service composition.
- app/security: thread-safe credential and permission managers.
- tests/phase6: authentication, identity, tenant, authorization, profile, tool, concurrency, and end-to-end tests.

## Usage
Create a MultiUserRuntime with a persistent SQLite path and a random secret of at least 32 characters. Store the secret in PAAI_AUTH_SECRET; never commit it.

Register:
```python
result = runtime.auth.register("person@example.com", "a-long-password")
```

Authenticate each incoming bearer token:
```python
identity = runtime.authenticate(access_token)
with identity_scope(identity):
    profile = runtime.profiles.get_profile()
```

Only call authenticated services inside the identity scope. Do not accept a user ID from model output or an untrusted request body as proof of identity.

## Security boundaries and limitations
- HS256 tokens are signed and expire, but there is no refresh-token or revocation system yet.
- HTTP middleware/API server that extracts bearer tokens and installs identity_scope is Phase 8 work. Until then, callers must use runtime.authenticate(token) and identity_scope correctly.
- Python objects are not a security boundary: code running inside the process can instantiate Principal. Only verified tokens at the application boundary establish trusted identity.
- CredentialManager and PermissionManager are thread-safe but remain in-memory; credentials are not encrypted or durable.
- Existing Phase 3 memory functions accept user IDs. Application entry points must derive the ID from current_identity and never forward a caller-selected ID. A dedicated authenticated memory facade and durable tenant controls remain future hardening.
- Workflows, approvals, audit logs, and browser contexts are not yet durable or comprehensively isolated across processes.
- SQLite is suitable for this learning-stage single-host implementation; production multi-process deployment requires a deliberate shared persistence strategy.

## Tests
Run all tests from the project root:
```powershell
.\venv\Scripts\python.exe -m unittest discover -s tests -v
```

Phase 6 is not closed until the complete suite passes, the runtime is exercised with two users, docs are reviewed, and the engineering MCQ assessment is completed.

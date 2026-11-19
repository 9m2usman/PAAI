# Phase 6 — Multi-User Agent Infrastructure

## Objective

Provide one shared PAAI runtime for independently authenticated users. Identity, profiles, long-term memory, credentials, and permissions must remain scoped to the authenticated user.

## Architecture

1. Email/password registration and login use PBKDF2 password hashing and a SQLite account repository.
2. The token service issues signed HS256 bearer tokens with an expiry. Authentication verifies the token and confirms that its subject and email still match an account in the database.
3. The application authenticates a bearer token with `runtime.authenticate(token)`, then installs the returned identity for the request using `identity_scope(identity)`.
4. `ContextVar` keeps the current identity separate between concurrent execution contexts.
5. `ProfileService` and `AuthenticatedMemoryService` derive the user ID from the current identity. Their public methods do not accept a caller-selected user ID.
6. `AuthorizationService` binds permission and credential operations to the current identity. The underlying credential and permission managers use per-user keys and thread locks.
7. The shared runtime composes these services. It does not create a separate agent instance for each user.

## Modules

- `app/auth/`: password hashing, SQLite account repository, token signing/verification, registration and login.
- `app/identity/`: Principal, IdentityContext, and request-local identity scope.
- `app/tenancy/`: ownership guard.
- `app/access/`: identity-bound permission and credential facade.
- `app/profiles/`: authenticated profile persistence.
- `app/memory/authenticated_memory.py`: authenticated facade over the Phase 3 memory store.
- `app/runtime/`: shared multi-user service composition.
- `app/security/`: thread-safe user-scoped credential and permission managers.
- `tests/phase6/`: authentication, identity, tenant, authorization, profile/memory isolation, tool isolation, concurrency, and end-to-end tests.

## Usage

Create one shared runtime with a persistent SQLite account path and a random secret of at least 32 characters. Set the secret in `PAAI_AUTH_SECRET`; never commit it.

Register and authenticate:

```python
result = runtime.auth.register("person@example.com", "a-long-password")
identity = runtime.authenticate(result["access_token"])

with identity_scope(identity):
    profile = runtime.profiles.get_profile()
    memories = runtime.memory.get_memories()
    runtime.memory.save_memory("language", "English")
    access = runtime.authorization()
```

The identity scope belongs at the trusted application boundary for each request. Never accept a user ID from model output or an untrusted request body as proof of identity. The authenticated memory service deliberately exposes no user-ID parameter.

## Security boundaries and limitations

- HS256 tokens are signed and expire, but refresh-token rotation, revocation, and account logout invalidation are not implemented.
- HTTP middleware/API server that extracts bearer tokens and installs `identity_scope` is Phase 8 work. Until then, callers must authenticate the token and establish the scope correctly.
- Python objects are not a security boundary: code running inside the process can instantiate a Principal. Only a token verified by the authentication service at the application boundary establishes trusted identity.
- CredentialManager and PermissionManager are thread-safe but remain in-memory; credentials are not encrypted or durable.
- The original low-level Phase 3 memory functions still accept a user ID for internal use. Application entry points should use `runtime.memory`, whose methods derive the ID from the authenticated identity.
- Workflows, approvals, audit logs, OAuth state, and browser contexts are not yet durable or comprehensively isolated across processes.
- SQLite is suitable for this learning-stage single-host implementation. Production multi-process deployment needs a deliberate shared persistence strategy and stronger operational controls.
- Password reset, email verification, rate limiting, and account lockout are not implemented.

## Verification

Run the complete test suite from the project root in PowerShell:

```powershell
.\\venv\\Scripts\\python.exe -m unittest discover -s tests -v
```

The Phase 6 tests verify registration/login, invalid credentials, token tampering/expiry, identity scoping, tenant checks, profile and actual Phase 3 memory isolation, credential/permission isolation, concurrent identity separation, and a two-user runtime flow.

## Engineering review

The review confirmed the shared runtime and request-local identity design, signed expiring tokens, backend-derived profile and memory ownership, and per-user permission/credential scoping. It also identified that the original memory-isolation test only covered profiles. The authenticated memory facade and expanded tests close that specific acceptance gap.

The implementation remains a learning-stage multi-user foundation, not a production security boundary. In particular, the HTTP authentication boundary, durable encrypted credentials, durable workflow/approval/audit stores, cross-process coordination, token revocation, and live external-provider verification remain later work.

## Phase 6 completion checklist

- [x] Email/password registration and login with PBKDF2 password hashing.
- [x] Signed HS256 access tokens with expiry and account lookup.
- [x] Request-local authenticated identity context.
- [x] Backend tenant ownership checks.
- [x] Authenticated profile service.
- [x] Authenticated facade for the Phase 3 memory store.
- [x] User-scoped credentials and permissions.
- [x] Concurrent request identity separation.
- [x] Two-user integration coverage.
- [ ] User reruns the complete test suite after the memory-isolation remediation.
- [ ] Engineering MCQ assessment completed.
- [ ] User confirms Phase 6 closure.


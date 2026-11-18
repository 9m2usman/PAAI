# Phase 5 — Real-World Workflow Execution

## Status

Implementation hardening is in progress on branch `phase5-hardening`. The code and regression tests have been added, but the test suite has not yet been executed in the project's Windows virtual environment. Do not mark Phase 5 complete until local tests, an end-to-end workflow, documentation review, and the phase assessment are complete.

## Goal

Allow the trusted application layer to run real integration actions through a common execution boundary, with per-user permissions, deterministic risk classification, human approval, OAuth credentials, and audit records.

## Architecture

1. `IntegrationRegistry` holds the available Gmail, Calendar, and optional Browser connectors.
2. `CredentialManager` stores credentials under a user and integration key.
3. `PermissionManager` checks whether that user may call an action and whether medium-risk actions may run automatically.
4. `RiskEvaluator` classifies actions in application code. Unknown actions are high risk.
5. `ApprovalManager` binds an approval to the exact integration, action, and parameters. Approvals expire after 15 minutes by default and can be consumed once.
6. `ExecutionManager` checks permission and risk, obtains credentials, invokes the connector, and writes an audit record.
7. `WorkflowManager` runs ordered integration steps, pauses when approval is needed, and resumes or rejects the workflow.
8. `IntegrationToolAdapter` is an application-facing adapter. The authenticated application must bind the user identity before calling it; never accept a user ID supplied by the LLM.

## Risk and approval rules

| Risk | Default behavior |
|---|---|
| Low | Runs automatically after tool permission is granted |
| Medium | Requires approval unless the user has separately granted automatic permission for that exact integration/action |
| High | Always requires human approval; automatic permission cannot override this |
| Unknown | Treated as high risk |

High-risk examples include sending email, deleting or cancelling events, publishing, payments, and transfers. Medium-risk examples include creating drafts/events and updating records. The classification is deterministic and does not depend on the model's opinion.

An approval is tied to a SHA-256 fingerprint of the exact action data. Changing any parameter invalidates the approval. An approved action expires and may be consumed only once.

## Integrations

### Gmail

- List and read messages
- Create drafts
- Send email (high risk and always approval-gated)

### Google Calendar

- List events
- Create and update events (medium risk)
- Delete events (high risk)

Google OAuth state is bound to the initiating user and expires after 10 minutes. Access and refresh tokens are stored by user/integration in the in-memory credential manager. The application must create an OAuth authorization URL and handle the callback by passing the authenticated user, returned code, and state to `exchange_code`.

**Important:** This phase provides the OAuth manager but does not provide an HTTP callback route or a complete web server. The configured redirect URI must point to a callback endpoint that the application implements.

### Browser

Browser automation is optional. It requires an explicit HTTPS domain allowlist. The Playwright request route blocks navigation and resource requests outside that allowlist, including redirects. Do not enable the browser with an empty allowlist.

### Documents

The existing document processor supports TXT, Markdown, JSON, and CSV reading, plus TXT/Markdown creation. Paths are restricted to its configured root and file sizes are limited.

## Example: create a runtime and run a workflow

The following is an application-layer example. In a real web application, obtain `authenticated_user_id` from the verified login session, never from a prompt or model-generated argument.

```python
from app.integrations.register_integrations import create_phase5_runtime, close_phase5_runtime

runtime = create_phase5_runtime()

user_id = "authenticated-user-123"

runtime["permission_manager"].grant_permission(
    user_id,
    "gmail",
    ["list_emails", "read_email", "create_draft", "send_email"]
)

result = runtime["workflow_manager"].run(
    user_id,
    [
        {
            "integration": "gmail",
            "action": "list_emails",
            "parameters": {"max_results": 5}
        }
    ]
)

print(result)

close_phase5_runtime(runtime)
```

For a high-risk step, the workflow returns with `status == "awaiting_approval"`. Approve it through `runtime["approval_manager"].approve(user_id, approval_id)`, then call `runtime["workflow_manager"].resume(user_id, workflow_id, approval_id)`. To reject, call `runtime["workflow_manager"].reject(user_id, workflow_id, approval_id)`.

The example requires the user's Google account to have been connected through OAuth first. The in-memory runtime and credentials must remain alive for the duration of the workflow.

## Local verification

From `E:\\PAAI` in PowerShell:

```powershell
.\\venv\\Scripts\\python.exe -m pip install -r requirements.txt
.\\venv\\Scripts\\python.exe -m unittest discover -s tests -p "test_phase5_hardening.py" -v
.\\venv\\Scripts\\python.exe -m unittest discover -s tests -v
```

The tests mock external services. They must not send real emails, change a real calendar, or browse arbitrary external sites.

## Prototype limitations and later-phase work

- Credentials, approvals, workflow state, and audit records are in memory and are lost when the process stops.
- Credentials are not encrypted at rest. Do not use this prototype as a production credential vault.
- OAuth state is in memory; multiple server processes need shared state storage.
- The application must implement authentication and the OAuth callback. Phase 6 will establish trusted identity and tenant isolation at the platform boundary.
- The current workflow manager is called by trusted application code. The Phase 2 planner's generic tool schema does not yet carry integration parameters or a verified user context, so do not expose the adapter as a global LLM tool. A future planner/orchestrator bridge must inject authenticated identity outside model-controlled arguments and route approvals back to the user.
- Browser automation uses one browser context per runtime, not a durable per-user browser profile. Do not share a runtime's browser session between users.
- API requests reject redirects. If a provider legitimately requires a redirect, handle it with an explicit provider-specific allowlist rather than enabling unrestricted redirects.
- Gmail and Calendar live API calls, Google OAuth, and real browser navigation require manual integration testing with test accounts and allowlisted domains.

## Acceptance criteria

- [x] Runtime factory matches connector and workflow constructor signatures.
- [x] Browser is opt-in and requires explicit allowed domains.
- [x] User identity is bound by the trusted application adapter, not model arguments.
- [x] Low/medium/high/unknown risk behavior is deterministic.
- [x] Approval is action-bound, expires, and is single-use.
- [x] OAuth state is user-bound and expires.
- [x] Browser and API destination restrictions are implemented.
- [x] Workflow rejection records the actual risk level.
- [x] Focused Phase 5 regression tests are added.
- [ ] Run focused and full test suites on Windows.
- [ ] Complete a mocked end-to-end email draft/approval workflow test.
- [ ] Complete a manual Google OAuth and Gmail/Calendar test using a dedicated test account.
- [ ] Complete documentation and engineering review.
- [ ] Complete the Phase 5 MCQ assessment and formally close the phase.

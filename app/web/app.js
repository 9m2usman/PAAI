const API = "";
const tokenKey = "paai_access_token";
let authMode = "login";
let currentUser = null;
let toastTimer = null;

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => Array.from(document.querySelectorAll(selector));

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  })[char]);
}

function showToast(message, isError = false) {
  const toast = $("#toast");
  toast.textContent = message;
  toast.classList.toggle("error", isError);
  toast.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove("show"), 3800);
}

async function api(path, options = {}) {
  const token = sessionStorage.getItem(tokenKey);
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (token) headers.Authorization = `Bearer ${token}`;
  const response = await fetch(API + path, { ...options, headers });
  const raw = await response.text();
  let data = null;
  try { data = raw ? JSON.parse(raw) : null; } catch { data = raw; }
  if (!response.ok) {
    if (response.status === 401 && token) signOut(false);
    const detail = data && typeof data === "object" ? (data.detail || data.message) : data;
    throw new Error(detail || `Request failed (${response.status})`);
  }
  return data;
}

function setAuthMode(mode) {
  authMode = mode;
  $$(".auth-tab").forEach((tab) => tab.classList.toggle("selected", tab.dataset.authMode === mode));
  $("#auth-submit").textContent = mode === "login" ? "Sign in" : "Create account";
  $("#auth-password").autocomplete = mode === "login" ? "current-password" : "new-password";
}

function signOut(showMessage = true) {
  sessionStorage.removeItem(tokenKey);
  currentUser = null;
  $("#workspace").hidden = true;
  $("#auth-view").hidden = false;
  $("#logout-button").hidden = true;
  $("#user-email").textContent = "Not signed in";
  if (showMessage) showToast("Signed out.");
}

function showWorkspace(user) {
  currentUser = user;
  $("#auth-view").hidden = true;
  $("#workspace").hidden = false;
  $("#logout-button").hidden = false;
  $("#user-email").textContent = user.email || "Signed in";
  refreshAll().catch((error) => showToast(error.message, true));
}

function showView(name) {
  const allowed = ["overview", "goals", "workflows", "approvals", "integrations"];
  if (!allowed.includes(name)) name = "overview";
  $$(".view").forEach((view) => view.classList.toggle("active", view.id === `view-${name}`));
  $$(".nav-link").forEach((link) => link.classList.toggle("active", link.dataset.view === name));
  const titles = { overview: "Overview", goals: "Autonomous goals", workflows: "Manual workflows", approvals: "Approval center", integrations: "Integrations" };
  $("#page-title").textContent = titles[name];
  if (name === "goals") loadGoals();
  if (name === "approvals") loadApprovals();
  if (name === "integrations") { loadGoogleStatus(); loadPermissions(); }
}

async function loadHealth() {
  try {
    const result = await api("/health/ready");
    $("#api-dot").classList.toggle("good", result.status === "ready");
    $("#api-dot").classList.toggle("bad", result.status !== "ready");
    $("#api-label").textContent = result.status === "ready" ? "API ready" : "API not ready";
  } catch {
    $("#api-dot").classList.add("bad");
    $("#api-label").textContent = "API unavailable";
  }
}

function asArray(value) {
  if (Array.isArray(value)) return value;
  if (value && Array.isArray(value.items)) return value.items;
  if (value && Array.isArray(value.results)) return value.results;
  return [];
}

function statusBadge(status) {
  const safe = String(status || "unknown").toLowerCase();
  return `<span class="status-badge ${escapeHtml(safe)}">${escapeHtml(safe.replaceAll("_", " "))}</span>`;
}

function goalTitle(goal) {
  return goal.description || goal.goal_id || "Untitled goal";
}

function renderGoalCard(goal) {
  const id = escapeHtml(goal.goal_id || "");
  const status = String(goal.status || "unknown");
  return `<article class="item-card">
    <div class="item-top"><div><h4>${escapeHtml(goalTitle(goal))}</h4><div class="item-meta">ID: ${id} · Trigger: ${escapeHtml(goal.trigger_type || "manual")}</div></div>${statusBadge(status)}</div>
    <div class="item-meta">Next run: ${escapeHtml(goal.next_run_at || "Manual")}</div>
    <div class="item-actions">
      <button class="button button-primary" data-goal-action="run" data-id="${id}">Run now</button>
      <button class="button button-secondary" data-goal-action="runs" data-id="${id}">History</button>
      ${status === "paused" ? `<button class="button button-secondary" data-goal-action="resume" data-id="${id}">Resume</button>` : `<button class="button button-secondary" data-goal-action="pause" data-id="${id}">Pause</button>`}
      <button class="button button-quiet" data-goal-action="cancel" data-id="${id}">Cancel</button>
    </div>
  </article>`;
}

async function loadGoals() {
  const target = $("#goals-list");
  target.textContent = "Loading goals…";
  try {
    const goals = asArray(await api("/api/v1/goals"));
    $("#stat-goals").textContent = String(goals.length);
    target.innerHTML = goals.length ? goals.map(renderGoalCard).join("") : "No goals yet. Create your first goal above.";
    $("#overview-goals").innerHTML = goals.length ? goals.slice(0, 3).map(renderGoalCard).join("") : "No goals yet.";
  } catch (error) {
    target.textContent = error.message;
    throw error;
  }
}

async function loadApprovals() {
  const target = $("#approvals-list");
  target.textContent = "Loading pending approvals…";
  try {
    const workflows = asArray(await api("/api/v1/workflows/pending"));
    $("#approval-count").textContent = String(workflows.length);
    $("#stat-approvals").textContent = String(workflows.length);
    if (!workflows.length) {
      target.textContent = "No pending approvals. When a workflow needs your decision, it will appear here.";
      return;
    }
    target.innerHTML = workflows.map((workflow) => {
      const pending = workflow.pending_approval || {};
      const action = pending.action_data || {};
      const workflowId = escapeHtml(workflow.workflow_id);
      const approvalId = escapeHtml(pending.approval_id);
      return `<article class="item-card">
        <div class="item-top"><div><h4>${escapeHtml(action.integration || "Integration")} · ${escapeHtml(action.action || "Action")}</h4><div class="item-meta">Workflow: ${workflowId}</div></div>${statusBadge("awaiting_approval")}</div>
        <p class="muted">Review the exact parameters below. Approval can perform a real external action.</p>
        <pre class="json-output">${escapeHtml(JSON.stringify(action.parameters || {}, null, 2))}</pre>
        <div class="item-actions"><button class="button button-primary" data-approval-action="approve" data-workflow="${workflowId}" data-approval="${approvalId}">Approve and continue</button><button class="button button-quiet" data-approval-action="reject" data-workflow="${workflowId}" data-approval="${approvalId}">Reject</button></div>
      </article>`;
    }).join("");
  } catch (error) {
    target.textContent = error.message;
    throw error;
  }
}

async function loadGoogleStatus() {
  try {
    const status = await api("/api/v1/integrations/google/status");
    const connected = Boolean(status.gmail || status.calendar);
    $("#google-status").textContent = connected ? `Connected · Gmail ${status.gmail ? "✓" : "—"} / Calendar ${status.calendar ? "✓" : "—"}` : "Not connected";
    $("#google-status").className = `status-badge ${connected ? "connected" : ""}`;
    $("#stat-google").textContent = connected ? "Connected" : "Not connected";
  } catch (error) {
    $("#google-status").textContent = "Unavailable";
    $("#stat-google").textContent = "Unavailable";
    throw error;
  }
}

async function loadPermissions() {
  const target = $("#permissions-list");
  target.textContent = "Loading permissions…";
  try {
    const permissions = await api("/api/v1/permissions");
    const entries = Array.isArray(permissions)
      ? permissions
      : Object.entries(permissions || {}).flatMap(([integration, actions]) =>
          (Array.isArray(actions) ? actions : []).map((action) => ({ integration, action }))
        );
    if (!entries.length) {
      target.textContent = "No integration permissions granted yet.";
      return;
    }
    target.innerHTML = entries.map((entry) => {
      const integration = entry.integration || entry.name || "";
      const actions = Array.isArray(entry.actions) ? entry.actions : [entry.action].filter(Boolean);
      return actions.map((action) => `<article class="item-card"><div class="item-top"><div><h4>${escapeHtml(integration)} · ${escapeHtml(action)}</h4><div class="item-meta">Granted to your PAAI account</div></div><button class="button button-quiet button-small" data-revoke-integration="${escapeHtml(integration)}" data-revoke-action="${escapeHtml(action)}">Revoke</button></div></article>`).join("");
    }).join("");
  } catch (error) {
    target.textContent = error.message;
    throw error;
  }
}

async function refreshAll() {
  await loadHealth();
  await Promise.allSettled([loadGoals(), loadApprovals(), loadGoogleStatus(), loadPermissions()]);
}

$("#auth-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = $("#auth-submit");
  button.disabled = true;
  try {
    const result = await api(`/api/v1/auth/${authMode === "login" ? "login" : "register"}`, {
      method: "POST",
      body: JSON.stringify({ email: $("#auth-email").value.trim(), password: $("#auth-password").value })
    });
    sessionStorage.setItem(tokenKey, result.access_token);
    $("#auth-password").value = "";
    showWorkspace(result.user);
    showToast(authMode === "login" ? "Signed in." : "Account created.");
  } catch (error) {
    showToast(error.message, true);
  } finally {
    button.disabled = false;
  }
});

$$(".auth-tab").forEach((tab) => tab.addEventListener("click", () => setAuthMode(tab.dataset.authMode)));
$$(".nav-link").forEach((link) => link.addEventListener("click", () => showView(link.dataset.view)));
$$(".text-link[data-view]").forEach((link) => link.addEventListener("click", () => showView(link.dataset.view)));
$("#logout-button").addEventListener("click", () => signOut());
$("#refresh-button").addEventListener("click", () => refreshAll().then(() => showToast("Workspace refreshed.")).catch((error) => showToast(error.message, true)));
$("#goals-refresh").addEventListener("click", () => loadGoals().then(() => showToast("Goals reloaded.")).catch((error) => showToast(error.message, true)));
$("#approvals-refresh").addEventListener("click", () => loadApprovals().then(() => showToast("Approvals reloaded.")).catch((error) => showToast(error.message, true)));
$("#permissions-refresh").addEventListener("click", () => loadPermissions().then(() => showToast("Permissions reloaded.")).catch((error) => showToast(error.message, true)));
$("#google-refresh").addEventListener("click", () => loadGoogleStatus().then(() => showToast("Google status checked.")).catch((error) => showToast(error.message, true)));

$("#goal-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = event.submitter;
  button.disabled = true;
  try {
    const goal = await api("/api/v1/goals", { method: "POST", body: JSON.stringify({
      description: $("#goal-description").value.trim(),
      max_steps: Number($("#goal-steps").value),
      max_runtime_seconds: Number($("#goal-runtime").value)
    }) });
    $("#goal-description").value = "";
    showToast(`Goal created: ${goal.goal_id || "saved"}`);
    await loadGoals();
  } catch (error) {
    showToast(error.message, true);
  } finally { button.disabled = false; }
});

$("#goals-list").addEventListener("click", handleGoalAction);
$("#overview-goals").addEventListener("click", handleGoalAction);
async function handleGoalAction(event) {
  const button = event.target.closest("[data-goal-action]");
  if (!button) return;
  const action = button.dataset.goalAction;
  const id = button.dataset.id;
  button.disabled = true;
  try {
    if (action === "runs") {
      const runs = await api(`/api/v1/goals/${encodeURIComponent(id)}/runs`);
      $("#runs-panel").hidden = false;
      $("#runs-subtitle").textContent = `Goal ${id}`;
      $("#runs-output").textContent = JSON.stringify(runs, null, 2);
      $("#runs-panel").scrollIntoView({ behavior: "smooth", block: "start" });
      return;
    }
    if (action === "cancel" && !confirm("Cancel this goal?")) return;
    const result = await api(`/api/v1/goals/${encodeURIComponent(id)}/${action}`, { method: "POST" });
    if (action === "run") {
      $("#runs-panel").hidden = false;
      $("#runs-subtitle").textContent = `Latest scheduler result for ${id}`;
      $("#runs-output").textContent = JSON.stringify(result, null, 2);
    }
    showToast(`Goal action completed: ${action}`);
    await loadGoals();
    await loadApprovals();
  } catch (error) {
    showToast(error.message, true);
  } finally { button.disabled = false; }
}

$("#workflow-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = event.submitter;
  button.disabled = true;
  $("#workflow-output").textContent = "Planning and executing workflow…";
  try {
    const result = await api("/api/v1/workflows", { method: "POST", body: JSON.stringify({ request: $("#workflow-request").value.trim() }) });
    $("#workflow-output").textContent = JSON.stringify(result, null, 2);
    await loadApprovals();
    showToast(result.workflow?.status === "awaiting_approval" ? "Workflow is waiting for your approval." : "Workflow finished.");
  } catch (error) {
    $("#workflow-output").textContent = error.message;
    showToast(error.message, true);
  } finally { button.disabled = false; }
});

$("#approvals-list").addEventListener("click", async (event) => {
  const button = event.target.closest("[data-approval-action]");
  if (!button) return;
  const action = button.dataset.approvalAction;
  const workflowId = button.dataset.workflow;
  const approvalId = button.dataset.approval;
  const message = action === "approve"
    ? "Approve this exact action and allow the workflow to continue? It may perform a real external side effect."
    : "Reject this action?";
  if (!confirm(message)) return;
  button.disabled = true;
  try {
    const result = await api(`/api/v1/workflows/${encodeURIComponent(workflowId)}/${action}`, {
      method: "POST", body: JSON.stringify({ approval_id: approvalId })
    });
    showToast(action === "approve" ? "Approval processed." : "Action rejected.");
    $("#workflow-output").textContent = JSON.stringify(result, null, 2);
    await Promise.all([loadApprovals(), loadGoals()]);
  } catch (error) {
    showToast(error.message, true);
  } finally { button.disabled = false; }
});

$("#google-connect").addEventListener("click", async () => {
  try {
    const result = await api("/api/v1/integrations/google/connect");
    if (!result.authorization_url) throw new Error("Google did not return an authorization URL.");
    window.location.assign(result.authorization_url);
  } catch (error) { showToast(error.message, true); }
});

$("#google-disconnect").addEventListener("click", async () => {
  if (!confirm("Disconnect Gmail and Google Calendar credentials for this PAAI account?")) return;
  try {
    await api("/api/v1/integrations/google/disconnect", { method: "DELETE" });
    await loadGoogleStatus();
    showToast("Google account disconnected.");
  } catch (error) { showToast(error.message, true); }
});

function updatePermissionActions() {
  const integration = $("#permission-integration").value;
  const actions = integration === "gmail"
    ? [["list_emails", "List emails (read-only)"], ["read_email", "Read email (read-only)"], ["create_draft", "Create draft"], ["send_email", "Send email (high risk)"]]
    : [["list_events", "List events (read-only)"], ["create_event", "Create event"], ["update_event", "Update event"], ["delete_event", "Delete event (high risk)"]];
  $("#permission-action").innerHTML = actions.map(([value, label]) => `<option value="${value}">${label}</option>`).join("");
}
$("#permission-integration").addEventListener("change", updatePermissionActions);
$("#permission-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const integration = $("#permission-integration").value;
  const action = $("#permission-action").value;
  try {
    await api("/api/v1/permissions", { method: "POST", body: JSON.stringify({ integration, action }) });
    showToast(`Granted ${integration} → ${action}.`);
    await loadPermissions();
  } catch (error) { showToast(error.message, true); }
});

$("#permissions-list").addEventListener("click", async (event) => {
  const button = event.target.closest("[data-revoke-integration]");
  if (!button) return;
  const integration = button.dataset.revokeIntegration;
  const action = button.dataset.revokeAction;
  if (!confirm(`Revoke ${integration} → ${action}?`)) return;
  try {
    await api(`/api/v1/permissions/${encodeURIComponent(integration)}/${encodeURIComponent(action)}`, { method: "DELETE" });
    showToast("Permission revoked.");
    await loadPermissions();
  } catch (error) { showToast(error.message, true); }
});

async function bootstrap() {
  await loadHealth();
  const token = sessionStorage.getItem(tokenKey);
  if (!token) return;
  try {
    const user = await api("/api/v1/auth/me");
    showWorkspace(user);
  } catch {
    sessionStorage.removeItem(tokenKey);
  }
}

window.addEventListener("hashchange", () => {
  const name = window.location.hash.replace("#", "") || "overview";
  if (!$("#workspace").hidden) showView(name);
});
updatePermissionActions();
bootstrap();

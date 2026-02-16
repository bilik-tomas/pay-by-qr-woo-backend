ADMIN_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Pay By QR Admin</title>
  <style>
    :root {
      --bg: #f3f6fb;
      --card: #ffffff;
      --line: #dbe3f2;
      --text: #17223a;
      --muted: #5f6f92;
      --primary: #0b5ad7;
      --primary-soft: #eff5ff;
      --danger: #b42318;
      --ok: #067647;
      --shadow: 0 8px 24px rgba(17, 34, 68, 0.08);
    }
    * { box-sizing: border-box; }
    body { margin: 0; font-family: "Segoe UI", Arial, sans-serif; color: var(--text); background: radial-gradient(circle at 10% 0%, #e7eefc 0, var(--bg) 48%); }
    .hidden { display: none !important; }

    .auth-screen { min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 20px; }
    .auth-card { width: 100%; max-width: 460px; background: var(--card); border: 1px solid var(--line); border-radius: 14px; box-shadow: var(--shadow); padding: 24px; }
    .auth-card h1 { margin: 0 0 8px; font-size: 26px; }
    .auth-card p { margin: 0 0 16px; color: var(--muted); font-size: 13px; }

    .shell { max-width: 1280px; margin: 0 auto; padding: 18px; }
    h1 { margin: 0 0 14px; font-size: 26px; }
    h2 { margin: 0 0 10px; font-size: 18px; }
    .sub { margin: 0 0 10px; color: var(--muted); font-size: 13px; }

    .grid { display: grid; gap: 14px; grid-template-columns: repeat(12, 1fr); }
    .card { background: var(--card); border: 1px solid var(--line); border-radius: 12px; padding: 14px; box-shadow: var(--shadow); }
    .span-12 { grid-column: span 12; }
    .span-8 { grid-column: span 8; }
    .span-6 { grid-column: span 6; }
    .span-4 { grid-column: span 4; }
    @media (max-width: 980px) { .span-8, .span-6, .span-4 { grid-column: span 12; } }

    .toolbar { display: flex; gap: 10px; flex-wrap: wrap; align-items: center; justify-content: space-between; margin-bottom: 10px; }
    .row { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin-bottom: 8px; }
    .field { display: grid; gap: 6px; min-width: 180px; margin-bottom: 10px; }
    .field label { font-size: 12px; color: var(--muted); }

    input, select, button {
      border-radius: 8px;
      border: 1px solid #b7c4de;
      padding: 10px 11px;
      font-size: 14px;
      background: #fff;
    }
    input, select { min-width: 180px; }
    input.wide { min-width: 280px; }
    input.slim { min-width: 120px; }
    input[type="checkbox"] { min-width: auto; }
    button { border: none; cursor: pointer; color: #fff; background: var(--primary); }
    button.secondary { background: #47587b; }
    button.ghost { background: #edf2ff; color: #1f3d72; border: 1px solid #c9d7f6; }
    button.danger { background: var(--danger); }
    .btn-xs { padding: 6px 8px; font-size: 12px; }

    .status { margin-top: 6px; min-height: 20px; font-size: 13px; }
    .status.ok { color: var(--ok); }
    .status.err { color: var(--danger); }
    .hint { color: var(--muted); font-size: 12px; }
    .pill { display: inline-flex; align-items: center; border: 1px solid #c6d1e8; border-radius: 999px; background: var(--primary-soft); color: #234274; padding: 4px 10px; font-size: 12px; }

    table { width: 100%; border-collapse: collapse; font-size: 13px; }
    th, td { border-bottom: 1px solid #e9eef7; text-align: left; vertical-align: top; padding: 8px 6px; }
    th { background: #f7faff; font-weight: 600; }
    .mono { font-family: Consolas, monospace; font-size: 12px; }
    .tags { display: inline-flex; gap: 6px; align-items: center; }
    .tag { font-size: 11px; padding: 2px 7px; border-radius: 999px; border: 1px solid #c9d4eb; background: #f6f9ff; color: #26406f; }

    .qr-wrap { border: 1px dashed #bcc9e4; border-radius: 10px; padding: 10px; width: 240px; background: #fbfdff; }
    .qr-wrap img { width: 220px; height: 220px; object-fit: contain; display: block; margin: 0 auto; }
  </style>
  <script src="https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit" async defer></script>
</head>
<body>
  <div id="login_screen" class="auth-screen">
    <div class="auth-card">
      <h1>Pay By QR Admin</h1>
      <p>Sign in to manage licenses and security settings.</p>

      <div class="field">
        <label for="username">Username</label>
        <input id="username" type="text" autocomplete="username">
      </div>
      <div class="field">
        <label for="password">Password</label>
        <input id="password" type="password" autocomplete="current-password">
      </div>
      <div id="otp_field" class="field hidden">
        <label for="otp_code">TOTP code</label>
        <input id="otp_code" class="slim" type="text" maxlength="12" placeholder="123456">
      </div>
      <div id="turnstile_box" class="hidden"></div>

      <div class="row" style="margin-top: 14px;">
        <button id="btn_login" type="button">Login</button>
      </div>
      <div id="status" class="status"></div>
    </div>
  </div>

  <div id="app" class="hidden shell">
    <h1>Pay By QR Admin</h1>
    <div class="grid">
      <div class="card span-12">
        <div class="toolbar">
          <div class="row">
            <div id="session_user" class="pill">Logged in</div>
            <div id="superadmin_banner" class="pill hidden">Superadmin</div>
          </div>
          <div class="row">
            <button id="btn_refresh_all" type="button" class="secondary btn-xs">Refresh Data</button>
            <button id="btn_logout" type="button" class="secondary btn-xs">Logout</button>
          </div>
        </div>
        <div id="app_status" class="status"></div>
      </div>

      <div class="card span-8">
        <h2>Licenses</h2>
        <p class="sub">Edit or delete existing licenses.</p>
        <div class="toolbar">
          <input id="search" type="text" class="wide" placeholder="Search key, domain, note">
          <button id="btn_licenses_refresh" type="button" class="secondary btn-xs">Refresh</button>
        </div>
        <table>
          <thead>
            <tr><th>License</th><th>Status</th><th>Domain</th><th>Instance</th><th>Expires</th><th>Actions</th></tr>
          </thead>
          <tbody id="license_rows"></tbody>
        </table>
      </div>

      <div class="card span-4">
        <h2>License Form</h2>
        <div class="field">
          <label for="license_key">License key</label>
          <div class="row">
            <input id="license_key" type="text" placeholder="XXXX-XXXX-XXXX" class="wide">
            <button id="btn_license_generate" type="button" class="ghost">Generate</button>
          </div>
        </div>
        <div class="field">
          <label for="license_status">Status</label>
          <select id="license_status">
            <option value="active">active</option>
            <option value="blocked">blocked</option>
            <option value="expired">expired</option>
          </select>
        </div>
        <div class="field">
          <label for="domain">Domain(s)</label>
          <input id="domain" type="text" placeholder="example.com, www.example.com">
        </div>
        <div class="field">
          <label for="plugin_instance_id">Plugin instance ID</label>
          <input id="plugin_instance_id" type="text" placeholder="optional">
        </div>
        <div class="field">
          <label for="expires_at">Expires at</label>
          <input id="expires_at" type="datetime-local">
        </div>
        <div class="field">
          <label for="note">Note</label>
          <input id="note" type="text" placeholder="internal note">
        </div>
        <div class="row">
          <button id="btn_license_save" type="button">Save</button>
          <button id="btn_license_delete" type="button" class="danger">Delete</button>
          <button id="btn_license_clear" type="button" class="ghost">Clear</button>
        </div>
      </div>

      <div class="card span-6">
        <h2>Admin Accounts</h2>
        <p class="sub">2FA can be enabled only by the account owner.</p>
        <div class="row">
          <div class="field">
            <label for="u_username">Username</label>
            <input id="u_username" type="text">
          </div>
          <div class="field">
            <label for="u_password">Password</label>
            <input id="u_password" type="password" placeholder="leave empty to keep">
          </div>
        </div>
        <div class="row">
          <label><input id="u_active" type="checkbox" checked> Active login</label>
          <label><input id="u_superadmin" type="checkbox"> Superadmin</label>
          <button id="btn_user_save" type="button">Save User</button>
          <button id="btn_user_clear" type="button" class="ghost">Clear</button>
        </div>
        <table>
          <thead><tr><th>User</th><th>Flags</th><th>2FA</th><th>Actions</th></tr></thead>
          <tbody id="user_rows"></tbody>
        </table>
      </div>

      <div class="card span-6">
        <h2>My Security</h2>
        <p class="sub">Scan QR in authenticator app and confirm code.</p>
        <div id="my_security_state" class="hint">Loading...</div>

        <div id="twofa_start_area" class="row" style="margin-top: 10px;">
          <button id="btn_2fa_start" type="button">Start 2FA Setup</button>
        </div>

        <div id="twofa_setup" class="hidden">
          <div class="qr-wrap"><img id="twofa_qr_img" alt="2FA QR"></div>
          <div class="field">
            <label for="twofa_secret">Secret</label>
            <input id="twofa_secret" type="text" readonly>
          </div>
          <div class="field">
            <label for="twofa_code">Confirm code</label>
            <input id="twofa_code" type="text" class="slim" maxlength="12" placeholder="123456">
          </div>
          <div class="row">
            <button id="btn_2fa_confirm" type="button">Confirm & Enable</button>
          </div>
        </div>

        <div id="twofa_disable_area" class="hidden">
          <hr>
          <div class="field">
            <label for="disable_password">Disable 2FA: account password</label>
            <input id="disable_password" type="password">
          </div>
          <div class="field">
            <label for="disable_otp">Disable 2FA: current OTP code</label>
            <input id="disable_otp" type="text" class="slim" maxlength="12">
          </div>
          <div class="row">
            <button id="btn_2fa_disable" type="button" class="danger">Disable 2FA</button>
          </div>
        </div>
      </div>

      <div id="superadmin_security" class="card span-12 hidden">
        <h2>Security Dashboard</h2>
        <p class="sub" id="turnstile_status_text"></p>
        <div class="grid">
          <div class="span-6">
            <h3>Blocked Actors</h3>
            <table>
              <thead><tr><th>Actor</th><th>Mode</th><th>Reason</th><th>Expires</th><th>Action</th></tr></thead>
              <tbody id="blocked_rows"></tbody>
            </table>
          </div>
          <div class="span-6">
            <h3>License Rate Stats</h3>
            <table>
              <thead><tr><th>License</th><th>Total calls</th><th>Current minute</th></tr></thead>
              <tbody id="license_stats_rows"></tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  </div>

<script>
let loginOptions = { twofa_required: false, turnstile_required: false, turnstile_site_key: "" };
let turnstileWidgetId = null;
let searchTimer = null;
let sessionUser = "";
let isSuperadmin = false;
let myTwoFaEnabled = false;

function setStatus(elId, msg, ok=true) {
  const el = document.getElementById(elId);
  el.textContent = msg || "";
  el.className = "status " + (ok ? "ok" : "err");
}

async function api(path, options = {}) {
  const resp = await fetch(path, Object.assign({ credentials: "same-origin" }, options));
  const body = await resp.json().catch(() => ({}));
  if (!resp.ok) throw new Error(body.detail || JSON.stringify(body) || "Request failed");
  return body;
}

function toIsoFromLocal(dateValue) { if (!dateValue) return null; const dt = new Date(dateValue); return Number.isNaN(dt.getTime()) ? null : dt.toISOString(); }
function toLocalInput(isoValue) { return isoValue ? String(isoValue).slice(0, 16) : ""; }
function resetTurnstile() { if (window.turnstile && turnstileWidgetId !== null) { try { window.turnstile.reset(turnstileWidgetId); } catch (err) {} } }

function renderTurnstile() {
  const box = document.getElementById("turnstile_box");
  if (!loginOptions.turnstile_required || !loginOptions.turnstile_site_key || !window.turnstile) {
    box.classList.add("hidden");
    box.innerHTML = "";
    turnstileWidgetId = null;
    return;
  }
  box.classList.remove("hidden");
  box.innerHTML = '<div id="turnstile_widget"></div>';
  turnstileWidgetId = window.turnstile.render("#turnstile_widget", { sitekey: loginOptions.turnstile_site_key, theme: "light" });
}

function getTurnstileToken() { return (!window.turnstile || turnstileWidgetId === null) ? "" : (window.turnstile.getResponse(turnstileWidgetId) || ""); }
function updateOtpVisibility() { document.getElementById("otp_field").classList.toggle("hidden", !loginOptions.twofa_required); }

function updateTwoFaUiState() {
  document.getElementById("my_security_state").textContent = myTwoFaEnabled ? "2FA is currently enabled." : "2FA is currently disabled.";
  document.getElementById("twofa_start_area").classList.toggle("hidden", myTwoFaEnabled);
  document.getElementById("twofa_disable_area").classList.toggle("hidden", !myTwoFaEnabled);
  if (myTwoFaEnabled) document.getElementById("twofa_setup").classList.add("hidden");
}

async function refreshLoginOptions() {
  try {
    const username = document.getElementById("username").value.trim();
    loginOptions = await api("/admin/api/login/options?username=" + encodeURIComponent(username));
    updateOtpVisibility();
    renderTurnstile();
  } catch (err) {
    setStatus("status", err.message, false);
  }
}

function applySessionInfo(data) {
  sessionUser = data.username;
  isSuperadmin = !!data.is_superadmin;
  myTwoFaEnabled = !!data.twofa_enabled;
  document.getElementById("session_user").textContent = "Logged in as: " + sessionUser;
  document.getElementById("superadmin_banner").classList.toggle("hidden", !isSuperadmin);
  document.getElementById("superadmin_security").classList.toggle("hidden", !isSuperadmin);
  document.getElementById("turnstile_status_text").textContent = isSuperadmin
    ? (loginOptions.turnstile_required
      ? "Cloudflare Turnstile is enabled in env configuration."
      : "Cloudflare Turnstile is disabled. Set ADMIN_TURNSTILE_SITE_KEY and ADMIN_TURNSTILE_SECRET_KEY in .env.")
    : "";
  updateTwoFaUiState();
}

async function login() {
  try {
    const payload = {
      username: document.getElementById("username").value.trim(),
      password: document.getElementById("password").value,
      otp_code: document.getElementById("otp_code").value.trim(),
      turnstile_token: getTurnstileToken()
    };
    await api("/admin/api/login", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
    const session = await api("/admin/api/session");
    document.getElementById("login_screen").classList.add("hidden");
    document.getElementById("app").classList.remove("hidden");
    applySessionInfo(session);
    setStatus("status", "Logged in.");
    await loadAll();
  } catch (err) {
    setStatus("status", err.message, false);
    resetTurnstile();
  }
}

async function logout() { try { await api("/admin/api/logout", { method: "POST" }); } catch (err) {} location.reload(); }

async function checkSession() {
  try {
    const session = await api("/admin/api/session");
    document.getElementById("login_screen").classList.add("hidden");
    document.getElementById("app").classList.remove("hidden");
    await refreshLoginOptions();
    applySessionInfo(session);
    await loadAll();
  } catch (err) {
    await refreshLoginOptions();
  }
}

function clearLicenseForm() {
  document.getElementById("license_key").value = "";
  document.getElementById("license_status").value = "active";
  document.getElementById("domain").value = "";
  document.getElementById("plugin_instance_id").value = "";
  document.getElementById("expires_at").value = "";
  document.getElementById("note").value = "";
}
function fillLicenseForm(item) {
  document.getElementById("license_key").value = item.license_key || "";
  document.getElementById("license_status").value = item.status || "active";
  document.getElementById("domain").value = item.domain || "";
  document.getElementById("plugin_instance_id").value = item.plugin_instance_id || "";
  document.getElementById("expires_at").value = toLocalInput(item.expires_at);
  document.getElementById("note").value = item.note || "";
}

async function generateLicenseKey() {
  try {
    const data = await api("/admin/api/license/generate", { method: "POST" });
    document.getElementById("license_key").value = data.license_key || "";
    setStatus("app_status", "License key generated.");
  } catch (err) { setStatus("app_status", err.message, false); }
}

async function upsertLicense() {
  try {
    const payload = {
      license_key: document.getElementById("license_key").value.trim(),
      status: document.getElementById("license_status").value,
      domain: document.getElementById("domain").value.trim(),
      plugin_instance_id: document.getElementById("plugin_instance_id").value.trim(),
      expires_at: toIsoFromLocal(document.getElementById("expires_at").value),
      note: document.getElementById("note").value.trim()
    };
    if (!payload.license_key) throw new Error("License key is required.");
    await api("/admin/api/license/upsert", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
    setStatus("app_status", "License saved.");
    await loadLicenses();
  } catch (err) { setStatus("app_status", err.message, false); }
}

async function deleteLicense(licenseKey) {
  if (!licenseKey || !confirm("Delete license '" + licenseKey + "'?")) return;
  try {
    await api("/admin/api/license/delete", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ license_key: licenseKey }) });
    setStatus("app_status", "License deleted.");
    if (document.getElementById("license_key").value.trim() === licenseKey) clearLicenseForm();
    await loadLicenses();
  } catch (err) { setStatus("app_status", err.message, false); }
}
function deleteLicenseFromForm() {
  const key = document.getElementById("license_key").value.trim();
  if (!key) { setStatus("app_status", "Select or enter a license key first.", false); return; }
  deleteLicense(key);
}

async function loadLicenses() {
  const q = document.getElementById("search").value.trim();
  const query = q ? "?q=" + encodeURIComponent(q) + "&limit=200" : "?limit=200";
  const data = await api("/admin/api/license/list" + query);
  const rows = document.getElementById("license_rows");
  rows.innerHTML = "";
  for (const item of data.items || []) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td class="mono"></td>
      <td><span class="tag"></span></td>
      <td></td>
      <td class="mono"></td>
      <td></td>
      <td class="tags"><button type="button" class="btn-xs ghost">Edit</button><button type="button" class="btn-xs danger">X</button></td>
    `;
    tr.children[0].textContent = item.license_key || "";
    tr.children[1].querySelector("span").textContent = item.status || "";
    tr.children[2].textContent = item.domain || "";
    tr.children[3].textContent = item.plugin_instance_id || "";
    tr.children[4].textContent = item.expires_at || "";
    tr.children[5].children[0].addEventListener("click", () => fillLicenseForm(item));
    tr.children[5].children[1].addEventListener("click", () => deleteLicense(item.license_key || ""));
    rows.appendChild(tr);
  }
}

function clearUserForm() {
  document.getElementById("u_username").value = "";
  document.getElementById("u_password").value = "";
  document.getElementById("u_active").checked = true;
  document.getElementById("u_superadmin").checked = false;
}
function fillUserForm(item) {
  document.getElementById("u_username").value = item.username || "";
  document.getElementById("u_password").value = "";
  document.getElementById("u_active").checked = !!item.is_active;
  document.getElementById("u_superadmin").checked = !!item.is_superadmin;
}

async function upsertUser() {
  try {
    const payload = {
      username: document.getElementById("u_username").value.trim(),
      password: document.getElementById("u_password").value,
      is_active: document.getElementById("u_active").checked,
      is_superadmin: document.getElementById("u_superadmin").checked,
      twofa_enabled: false,
      twofa_secret: ""
    };
    if (!payload.username) throw new Error("Username is required.");
    await api("/admin/api/user/upsert", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
    setStatus("app_status", "User saved.");
    document.getElementById("u_password").value = "";
    await loadUsers();
  } catch (err) { setStatus("app_status", err.message, false); }
}

async function setUserActive(username, isActive) {
  try {
    await api("/admin/api/user/set-active", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ username: username, is_active: isActive }) });
    setStatus("app_status", isActive ? "User enabled." : "User disabled.");
    await loadUsers();
  } catch (err) { setStatus("app_status", err.message, false); }
}

async function deleteUser(username) {
  if (!confirm("Delete user '" + username + "'?")) return;
  try {
    await api("/admin/api/user/delete", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ username: username }) });
    setStatus("app_status", "User deleted.");
    if (document.getElementById("u_username").value.trim() === username) clearUserForm();
    await loadUsers();
  } catch (err) { setStatus("app_status", err.message, false); }
}

async function loadUsers() {
  const data = await api("/admin/api/user/list");
  const rows = document.getElementById("user_rows");
  rows.innerHTML = "";
  let mine = null;
  for (const item of data.items || []) {
    if (item.username === sessionUser) mine = item;
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td class="mono"></td>
      <td></td>
      <td></td>
      <td class="tags"><button type="button" class="btn-xs ghost">Edit</button><button type="button" class="btn-xs secondary"></button><button type="button" class="btn-xs danger">Delete</button></td>
    `;
    tr.children[0].textContent = item.username || "";
    tr.children[1].textContent = (item.is_active ? "active" : "inactive") + " / " + (item.is_superadmin ? "superadmin" : "standard");
    tr.children[2].textContent = item.twofa_enabled ? "enabled" : "disabled";

    const editBtn = tr.children[3].children[0];
    const toggleBtn = tr.children[3].children[1];
    const delBtn = tr.children[3].children[2];
    toggleBtn.textContent = item.is_active ? "Disable" : "Enable";
    editBtn.addEventListener("click", () => fillUserForm(item));
    toggleBtn.addEventListener("click", () => setUserActive(item.username, !item.is_active));
    delBtn.addEventListener("click", () => deleteUser(item.username));
    if (item.username === sessionUser) { toggleBtn.disabled = true; toggleBtn.textContent = "Current"; }
    rows.appendChild(tr);
  }
  if (mine) {
    myTwoFaEnabled = !!mine.twofa_enabled;
    updateTwoFaUiState();
  }
}

async function startTwoFaSetup() {
  try {
    const data = await api("/admin/api/user/2fa/start", { method: "POST" });
    document.getElementById("twofa_setup").classList.remove("hidden");
    document.getElementById("twofa_qr_img").src = data.qr_data_url || "";
    document.getElementById("twofa_secret").value = data.secret || "";
    setStatus("app_status", "2FA setup started. Scan QR and confirm code.");
  } catch (err) { setStatus("app_status", err.message, false); }
}

async function confirmTwoFaSetup() {
  try {
    const otp = document.getElementById("twofa_code").value.trim();
    await api("/admin/api/user/2fa/confirm", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ otp_code: otp }) });
    document.getElementById("twofa_setup").classList.add("hidden");
    document.getElementById("twofa_code").value = "";
    setStatus("app_status", "2FA enabled successfully.");
    myTwoFaEnabled = true;
    updateTwoFaUiState();
    await loadUsers();
  } catch (err) { setStatus("app_status", err.message, false); }
}

async function disableTwoFa() {
  try {
    const payload = { password: document.getElementById("disable_password").value, otp_code: document.getElementById("disable_otp").value.trim() };
    await api("/admin/api/user/2fa/disable", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
    document.getElementById("disable_password").value = "";
    document.getElementById("disable_otp").value = "";
    document.getElementById("twofa_setup").classList.add("hidden");
    setStatus("app_status", "2FA disabled.");
    myTwoFaEnabled = false;
    updateTwoFaUiState();
    await loadUsers();
  } catch (err) { setStatus("app_status", err.message, false); }
}

async function loadBlockedActors() {
  if (!isSuperadmin) return;
  const data = await api("/admin/api/security/blocks");
  const rows = document.getElementById("blocked_rows");
  rows.innerHTML = "";
  for (const item of data.items || []) {
    const tr = document.createElement("tr");
    tr.innerHTML = `<td class="mono"></td><td></td><td></td><td></td><td><button type="button" class="btn-xs danger">Unblock</button></td>`;
    tr.children[0].textContent = item.actor;
    tr.children[1].textContent = item.mode;
    tr.children[2].textContent = item.reason;
    tr.children[3].textContent = item.mode === "hard" ? "never" : String(item.expires_in_seconds) + "s";
    tr.children[4].children[0].addEventListener("click", () => unblockActor(item.actor));
    rows.appendChild(tr);
  }
}

async function unblockActor(actor) {
  try {
    await api("/admin/api/security/unblock", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ actor: actor }) });
    setStatus("app_status", "Actor unblocked.");
    await loadBlockedActors();
  } catch (err) { setStatus("app_status", err.message, false); }
}

async function loadLicenseStats() {
  if (!isSuperadmin) return;
  const data = await api("/admin/api/security/license-stats");
  const rows = document.getElementById("license_stats_rows");
  rows.innerHTML = "";
  for (const item of data.items || []) {
    const tr = document.createElement("tr");
    tr.innerHTML = `<td class="mono"></td><td></td><td></td>`;
    tr.children[0].textContent = item.license_key;
    tr.children[1].textContent = String(item.total_calls);
    tr.children[2].textContent = String(item.current_minute_calls);
    rows.appendChild(tr);
  }
}

function debounceLoadLicenses() {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => { loadLicenses().catch((err) => setStatus("app_status", err.message, false)); }, 250);
}

async function loadAll() {
  try {
    await loadLicenses();
    await loadUsers();
    if (isSuperadmin) {
      await loadBlockedActors();
      await loadLicenseStats();
    }
  } catch (err) { setStatus("app_status", err.message, false); }
}

function bindEvents() {
  document.getElementById("btn_login").addEventListener("click", login);
  document.getElementById("btn_logout").addEventListener("click", logout);
  document.getElementById("btn_refresh_all").addEventListener("click", loadAll);
  document.getElementById("btn_licenses_refresh").addEventListener("click", () => loadLicenses().catch((err) => setStatus("app_status", err.message, false)));
  document.getElementById("btn_license_save").addEventListener("click", upsertLicense);
  document.getElementById("btn_license_delete").addEventListener("click", deleteLicenseFromForm);
  document.getElementById("btn_license_clear").addEventListener("click", clearLicenseForm);
  document.getElementById("btn_license_generate").addEventListener("click", generateLicenseKey);
  document.getElementById("btn_user_save").addEventListener("click", upsertUser);
  document.getElementById("btn_user_clear").addEventListener("click", clearUserForm);
  document.getElementById("btn_2fa_start").addEventListener("click", startTwoFaSetup);
  document.getElementById("btn_2fa_confirm").addEventListener("click", confirmTwoFaSetup);
  document.getElementById("btn_2fa_disable").addEventListener("click", disableTwoFa);

  document.getElementById("username").addEventListener("input", refreshLoginOptions);
  document.getElementById("search").addEventListener("input", debounceLoadLicenses);
  document.getElementById("password").addEventListener("keydown", (event) => { if (event.key === "Enter") login(); });
  document.getElementById("otp_code").addEventListener("keydown", (event) => { if (event.key === "Enter") login(); });
}

bindEvents();
checkSession();
</script>
</body>
</html>
"""
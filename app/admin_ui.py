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
      --shadow: 0 8px 24px rgba(17, 34, 68, 0.06);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "Segoe UI", Arial, sans-serif;
      color: var(--text);
      background: radial-gradient(circle at 10% 0%, #e7eefc 0, var(--bg) 48%);
    }
    .shell { max-width: 1240px; margin: 0 auto; padding: 18px; }
    h1 { margin: 0 0 14px; font-size: 26px; }
    h2 { margin: 0 0 10px; font-size: 18px; }
    .sub { margin: 0 0 10px; color: var(--muted); font-size: 13px; }
    .grid { display: grid; gap: 14px; grid-template-columns: repeat(12, 1fr); }
    .card {
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 14px;
      box-shadow: var(--shadow);
    }
    .span-12 { grid-column: span 12; }
    .span-8 { grid-column: span 8; }
    .span-6 { grid-column: span 6; }
    .span-4 { grid-column: span 4; }
    @media (max-width: 980px) { .span-8, .span-6, .span-4 { grid-column: span 12; } }

    .toolbar { display: flex; gap: 10px; flex-wrap: wrap; align-items: center; justify-content: space-between; margin-bottom: 10px; }
    .row { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin-bottom: 8px; }
    .field { display: grid; gap: 4px; min-width: 180px; }
    .field label { font-size: 12px; color: var(--muted); }
    input, select, button {
      border-radius: 8px;
      border: 1px solid #b7c4de;
      padding: 9px 10px;
      font-size: 14px;
      background: #fff;
    }
    input, select { min-width: 180px; }
    input.wide { min-width: 260px; }
    input.slim { min-width: 120px; }
    input[type="checkbox"] { min-width: auto; }
    button {
      border: none;
      cursor: pointer;
      color: #fff;
      background: var(--primary);
    }
    button.secondary { background: #47587b; }
    button.ghost { background: #edf2ff; color: #1f3d72; border: 1px solid #c9d7f6; }
    button.danger { background: var(--danger); }
    .btn-xs { padding: 6px 8px; font-size: 12px; }

    .hidden { display: none !important; }
    .status { margin-top: 4px; min-height: 20px; font-size: 13px; }
    .status.ok { color: var(--ok); }
    .status.err { color: var(--danger); }
    .hint { color: var(--muted); font-size: 12px; }
    .pill {
      display: inline-flex;
      align-items: center;
      border: 1px solid #c6d1e8;
      border-radius: 999px;
      background: var(--primary-soft);
      color: #234274;
      padding: 4px 10px;
      font-size: 12px;
    }
    table { width: 100%; border-collapse: collapse; font-size: 13px; }
    th, td { border-bottom: 1px solid #e9eef7; text-align: left; vertical-align: top; padding: 8px 6px; }
    th { background: #f7faff; font-weight: 600; }
    .mono { font-family: Consolas, monospace; font-size: 12px; }
    .tags { display: inline-flex; gap: 6px; align-items: center; }
    .tag {
      font-size: 11px;
      padding: 2px 7px;
      border-radius: 999px;
      border: 1px solid #c9d4eb;
      background: #f6f9ff;
      color: #26406f;
    }
  </style>
  <script src="https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit" async defer></script>
</head>
<body>
  <div class="shell">
    <h1>Pay By QR Admin</h1>

    <div id="login_card" class="grid">
      <div class="card span-6">
        <h2>Admin Login</h2>
        <p class="sub">Session-based authentication for UI management.</p>
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
        <div class="row">
          <button id="btn_login" type="button">Login</button>
        </div>
        <div id="status" class="status"></div>
      </div>
    </div>

    <div id="app" class="hidden">
      <div class="grid">
        <div class="card span-12">
          <div class="toolbar">
            <div class="row">
              <div id="session_user" class="pill">Logged in</div>
              <span class="hint">Actions are applied immediately.</span>
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
          <p class="sub">Select row with Edit, remove with X.</p>
          <div class="toolbar">
            <input id="search" type="text" class="wide" placeholder="Search key, domain, note">
            <button id="btn_licenses_refresh" type="button" class="secondary btn-xs">Refresh</button>
          </div>
          <table>
            <thead>
              <tr>
                <th>License</th>
                <th>Status</th>
                <th>Domain</th>
                <th>Instance</th>
                <th>Expires</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody id="license_rows"></tbody>
          </table>
        </div>

        <div class="card span-4">
          <h2>License Form</h2>
          <p class="sub">Create or update one license.</p>
          <div class="field">
            <label for="license_key">License key</label>
            <input id="license_key" type="text" placeholder="xxxx-xxxx-xxxx">
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
            <label for="domain">Domain</label>
            <input id="domain" type="text" placeholder="example.com or *">
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

        <div class="card span-12">
          <h2>Admin Accounts</h2>
          <p class="sub">Only superadmin can manage accounts.</p>
          <div class="row">
            <div class="field">
              <label for="u_username">Username</label>
              <input id="u_username" type="text">
            </div>
            <div class="field">
              <label for="u_password">Password</label>
              <input id="u_password" type="password" placeholder="leave empty to keep">
            </div>
            <div class="field">
              <label for="u_twofa_secret">TOTP secret</label>
              <input id="u_twofa_secret" type="text" placeholder="optional; auto-generated if empty">
            </div>
          </div>
          <div class="row">
            <label><input id="u_active" type="checkbox" checked> Active</label>
            <label><input id="u_superadmin" type="checkbox"> Superadmin</label>
            <label><input id="u_twofa" type="checkbox"> 2FA enabled</label>
            <button id="btn_user_save" type="button">Save User</button>
            <button id="btn_user_clear" type="button" class="ghost">Clear</button>
          </div>
          <table>
            <thead>
              <tr>
                <th>User</th>
                <th>Flags</th>
                <th>2FA</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody id="user_rows"></tbody>
          </table>
        </div>
      </div>
    </div>
  </div>

<script>
let loginOptions = { twofa_required: false, turnstile_required: false, turnstile_site_key: "" };
let turnstileWidgetId = null;
let searchTimer = null;

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

function toIsoFromLocal(dateValue) {
  if (!dateValue) return null;
  const dt = new Date(dateValue);
  if (Number.isNaN(dt.getTime())) return null;
  return dt.toISOString();
}

function toLocalInput(isoValue) {
  if (!isoValue) return "";
  return String(isoValue).slice(0, 16);
}

function resetTurnstile() {
  if (window.turnstile && turnstileWidgetId !== null) {
    try {
      window.turnstile.reset(turnstileWidgetId);
    } catch (err) {}
  }
}

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
  turnstileWidgetId = window.turnstile.render("#turnstile_widget", {
    sitekey: loginOptions.turnstile_site_key,
    theme: "light"
  });
}

function getTurnstileToken() {
  if (!window.turnstile || turnstileWidgetId === null) return "";
  return window.turnstile.getResponse(turnstileWidgetId) || "";
}

function updateOtpVisibility() {
  const otpField = document.getElementById("otp_field");
  if (loginOptions.twofa_required) otpField.classList.remove("hidden");
  else otpField.classList.add("hidden");
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

async function login() {
  try {
    const payload = {
      username: document.getElementById("username").value.trim(),
      password: document.getElementById("password").value,
      otp_code: document.getElementById("otp_code").value.trim(),
      turnstile_token: getTurnstileToken()
    };
    const data = await api("/admin/api/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    document.getElementById("login_card").classList.add("hidden");
    document.getElementById("app").classList.remove("hidden");
    document.getElementById("session_user").textContent = "Logged in as: " + data.username;
    setStatus("status", "Logged in.");
    await loadAll();
  } catch (err) {
    setStatus("status", err.message, false);
    resetTurnstile();
  }
}

async function logout() {
  try { await api("/admin/api/logout", { method: "POST" }); } catch (err) {}
  location.reload();
}

async function checkSession() {
  try {
    const data = await api("/admin/api/session");
    document.getElementById("login_card").classList.add("hidden");
    document.getElementById("app").classList.remove("hidden");
    document.getElementById("session_user").textContent = "Logged in as: " + data.username;
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
    await api("/admin/api/license/upsert", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    setStatus("app_status", "License saved.");
    await loadLicenses();
  } catch (err) {
    setStatus("app_status", err.message, false);
  }
}

async function deleteLicense(licenseKey) {
  if (!licenseKey) return;
  if (!confirm("Delete license '" + licenseKey + "'?")) return;
  try {
    await api("/admin/api/license/delete", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ license_key: licenseKey })
    });
    setStatus("app_status", "License deleted.");
    if (document.getElementById("license_key").value.trim() === licenseKey) clearLicenseForm();
    await loadLicenses();
  } catch (err) {
    setStatus("app_status", err.message, false);
  }
}

function deleteLicenseFromForm() {
  const key = document.getElementById("license_key").value.trim();
  if (!key) {
    setStatus("app_status", "Select or enter a license key first.", false);
    return;
  }
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
      <td class="mono">${item.license_key || ""}</td>
      <td><span class="tag">${item.status || ""}</span></td>
      <td>${item.domain || ""}</td>
      <td class="mono">${item.plugin_instance_id || ""}</td>
      <td>${item.expires_at || ""}</td>
      <td class="tags">
        <button type="button" class="btn-xs ghost js-license-edit" data-key="${item.license_key || ""}">Edit</button>
        <button type="button" class="btn-xs danger js-license-delete" data-key="${item.license_key || ""}">X</button>
      </td>
    `;
    tr.dataset.item = JSON.stringify(item);
    rows.appendChild(tr);
  }
}

function clearUserForm() {
  document.getElementById("u_username").value = "";
  document.getElementById("u_password").value = "";
  document.getElementById("u_twofa_secret").value = "";
  document.getElementById("u_active").checked = true;
  document.getElementById("u_superadmin").checked = false;
  document.getElementById("u_twofa").checked = false;
}

function fillUserForm(item) {
  document.getElementById("u_username").value = item.username || "";
  document.getElementById("u_password").value = "";
  document.getElementById("u_twofa_secret").value = "";
  document.getElementById("u_active").checked = !!item.is_active;
  document.getElementById("u_superadmin").checked = !!item.is_superadmin;
  document.getElementById("u_twofa").checked = !!item.twofa_enabled;
}

async function upsertUser() {
  try {
    const payload = {
      username: document.getElementById("u_username").value.trim(),
      password: document.getElementById("u_password").value,
      is_active: document.getElementById("u_active").checked,
      is_superadmin: document.getElementById("u_superadmin").checked,
      twofa_enabled: document.getElementById("u_twofa").checked,
      twofa_secret: document.getElementById("u_twofa_secret").value.trim()
    };
    if (!payload.username) throw new Error("Username is required.");
    await api("/admin/api/user/upsert", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    setStatus("app_status", "User saved.");
    document.getElementById("u_password").value = "";
    await loadUsers();
  } catch (err) {
    setStatus("app_status", err.message, false);
  }
}

async function deleteUser(username) {
  if (!confirm("Delete user '" + username + "'?")) return;
  try {
    await api("/admin/api/user/delete", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username: username })
    });
    setStatus("app_status", "User deleted.");
    if (document.getElementById("u_username").value.trim() === username) clearUserForm();
    await loadUsers();
  } catch (err) {
    setStatus("app_status", err.message, false);
  }
}

async function loadUsers() {
  const data = await api("/admin/api/user/list");
  const rows = document.getElementById("user_rows");
  rows.innerHTML = "";
  for (const item of data.items || []) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td class="mono">${item.username || ""}</td>
      <td>${item.is_active ? "active" : "inactive"} / ${item.is_superadmin ? "superadmin" : "standard"}</td>
      <td>${item.twofa_enabled ? "enabled" : "disabled"}</td>
      <td class="tags">
        <button type="button" class="btn-xs ghost js-user-edit" data-user="${item.username || ""}">Edit</button>
        <button type="button" class="btn-xs danger js-user-delete" data-user="${item.username || ""}">X</button>
      </td>
    `;
    tr.dataset.item = JSON.stringify(item);
    rows.appendChild(tr);
  }
}

function debounceLoadLicenses() {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => {
    loadLicenses().catch((err) => setStatus("app_status", err.message, false));
  }, 250);
}

async function loadAll() {
  try {
    await loadLicenses();
    await loadUsers();
  } catch (err) {
    setStatus("app_status", err.message, false);
  }
}

function bindEvents() {
  document.getElementById("btn_login").addEventListener("click", login);
  document.getElementById("btn_logout").addEventListener("click", logout);
  document.getElementById("btn_refresh_all").addEventListener("click", loadAll);
  document.getElementById("btn_licenses_refresh").addEventListener("click", () => loadLicenses().catch((err) => setStatus("app_status", err.message, false)));
  document.getElementById("btn_license_save").addEventListener("click", upsertLicense);
  document.getElementById("btn_license_delete").addEventListener("click", deleteLicenseFromForm);
  document.getElementById("btn_license_clear").addEventListener("click", clearLicenseForm);
  document.getElementById("btn_user_save").addEventListener("click", upsertUser);
  document.getElementById("btn_user_clear").addEventListener("click", clearUserForm);
  document.getElementById("username").addEventListener("input", refreshLoginOptions);
  document.getElementById("search").addEventListener("input", debounceLoadLicenses);
  document.getElementById("password").addEventListener("keydown", (event) => { if (event.key === "Enter") login(); });
  document.getElementById("otp_code").addEventListener("keydown", (event) => { if (event.key === "Enter") login(); });

  document.getElementById("license_rows").addEventListener("click", (event) => {
    const editBtn = event.target.closest(".js-license-edit");
    if (editBtn) {
      const tr = editBtn.closest("tr");
      if (!tr || !tr.dataset.item) return;
      fillLicenseForm(JSON.parse(tr.dataset.item));
      return;
    }
    const delBtn = event.target.closest(".js-license-delete");
    if (delBtn) {
      deleteLicense(delBtn.dataset.key || "");
    }
  });

  document.getElementById("user_rows").addEventListener("click", (event) => {
    const editBtn = event.target.closest(".js-user-edit");
    if (editBtn) {
      const tr = editBtn.closest("tr");
      if (!tr || !tr.dataset.item) return;
      fillUserForm(JSON.parse(tr.dataset.item));
      return;
    }
    const delBtn = event.target.closest(".js-user-delete");
    if (delBtn) {
      deleteUser(delBtn.dataset.user || "");
    }
  });
}

bindEvents();
checkSession();
</script>
</body>
</html>
"""
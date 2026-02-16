ADMIN_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Pay By QR Admin</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 24px; background: #f5f6f8; color: #1f2937; }
    .card { background: #fff; border: 1px solid #d4d7dd; border-radius: 8px; padding: 16px; margin-bottom: 16px; }
    .row { display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 8px; }
    input, select, button { padding: 8px; border: 1px solid #bac1cc; border-radius: 6px; }
    input[type="text"], input[type="password"], input[type="datetime-local"] { min-width: 230px; }
    button { cursor: pointer; background: #0b66c3; color: #fff; border: none; }
    button.secondary { background: #52525b; }
    table { width: 100%; border-collapse: collapse; font-size: 13px; }
    th, td { border-bottom: 1px solid #eceff4; text-align: left; padding: 8px; }
    th { background: #f9fafb; }
    .hidden { display: none; }
    .mono { font-family: Consolas, monospace; font-size: 12px; }
    .status { margin: 8px 0 0; font-size: 13px; }
  </style>
</head>
<body>
  <h1>Pay By QR Admin</h1>

  <div class="card" id="login_card">
    <h3>Login</h3>
    <div class="row">
      <input id="username" type="text" placeholder="username">
      <input id="password" type="password" placeholder="password">
      <input id="otp_code" type="text" placeholder="TOTP code (optional)">
      <button onclick="login()">Login</button>
    </div>
    <div class="status" id="status"></div>
  </div>

  <div id="app" class="hidden">
    <div class="card">
      <h3>Session</h3>
      <div class="row">
        <span id="session_user"></span>
        <button class="secondary" onclick="logout()">Logout</button>
      </div>
    </div>

    <div class="card">
      <h3>Create / Update License</h3>
      <div class="row">
        <input id="license_key" type="text" placeholder="license key">
        <select id="license_status">
          <option value="active">active</option>
          <option value="blocked">blocked</option>
          <option value="expired">expired</option>
        </select>
        <input id="domain" type="text" placeholder="domain or *">
      </div>
      <div class="row">
        <input id="plugin_instance_id" type="text" placeholder="plugin instance id">
        <input id="expires_at" type="datetime-local">
        <input id="note" type="text" placeholder="note">
        <button onclick="upsertLicense()">Save license</button>
      </div>
    </div>

    <div class="card">
      <h3>Licenses</h3>
      <div class="row">
        <input id="search" type="text" placeholder="search key/domain/note">
        <button class="secondary" onclick="loadLicenses()">Refresh</button>
      </div>
      <table>
        <thead><tr><th>License</th><th>Status</th><th>Domain</th><th>Instance</th><th>Expires</th><th>Note</th><th>Action</th></tr></thead>
        <tbody id="license_rows"></tbody>
      </table>
    </div>

    <div class="card">
      <h3>Admin Users</h3>
      <div class="row">
        <input id="u_username" type="text" placeholder="username">
        <input id="u_password" type="password" placeholder="new password (optional)">
        <input id="u_twofa_secret" type="text" placeholder="TOTP secret (optional)">
      </div>
      <div class="row">
        <label><input id="u_active" type="checkbox" checked> active</label>
        <label><input id="u_superadmin" type="checkbox"> superadmin</label>
        <label><input id="u_twofa" type="checkbox"> 2FA enabled</label>
        <button onclick="upsertUser()">Save user</button>
      </div>
      <table>
        <thead><tr><th>User</th><th>Active</th><th>Superadmin</th><th>2FA</th><th>Action</th></tr></thead>
        <tbody id="user_rows"></tbody>
      </table>
    </div>
  </div>

<script>
function status(msg, ok=true) {
  const el = document.getElementById("status");
  el.textContent = msg;
  el.style.color = ok ? "#0c7a43" : "#b42318";
}

async function api(path, options={}) {
  const resp = await fetch(path, Object.assign({credentials: "same-origin"}, options));
  const body = await resp.json().catch(() => ({}));
  if (!resp.ok) throw new Error(body.detail || JSON.stringify(body));
  return body;
}

function showApp(user) {
  document.getElementById("login_card").classList.add("hidden");
  document.getElementById("app").classList.remove("hidden");
  document.getElementById("session_user").textContent = "Logged in as: " + user;
  status("Logged in.");
}

async function login() {
  try {
    const payload = {
      username: document.getElementById("username").value.trim(),
      password: document.getElementById("password").value,
      otp_code: document.getElementById("otp_code").value.trim(),
    };
    const data = await api("/admin/api/login", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(payload),
    });
    showApp(data.username);
    await Promise.all([loadLicenses(), loadUsers()]);
  } catch (e) {
    status(e.message, false);
  }
}

async function logout() {
  try {
    await api("/admin/api/logout", {method: "POST"});
  } finally {
    location.reload();
  }
}

async function checkSession() {
  try {
    const data = await api("/admin/api/session");
    showApp(data.username);
    await Promise.all([loadLicenses(), loadUsers()]);
  } catch (e) {
    // ignore
  }
}

async function upsertLicense() {
  try {
    const expires = document.getElementById("expires_at").value;
    const payload = {
      license_key: document.getElementById("license_key").value.trim(),
      status: document.getElementById("license_status").value,
      domain: document.getElementById("domain").value.trim(),
      plugin_instance_id: document.getElementById("plugin_instance_id").value.trim(),
      expires_at: expires ? new Date(expires).toISOString() : null,
      note: document.getElementById("note").value.trim(),
    };
    if (!payload.license_key) throw new Error("License key is required.");
    await api("/admin/api/license/upsert", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(payload),
    });
    status("License saved.");
    await loadLicenses();
  } catch (e) {
    status(e.message, false);
  }
}

async function loadLicenses() {
  const q = document.getElementById("search").value.trim();
  const qs = q ? "?q=" + encodeURIComponent(q) + "&limit=200" : "?limit=200";
  const data = await api("/admin/api/license/list" + qs);
  const rows = document.getElementById("license_rows");
  rows.innerHTML = "";
  for (const item of data.items || []) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td class="mono">${item.license_key || ""}</td>
      <td>${item.status || ""}</td>
      <td>${item.domain || ""}</td>
      <td class="mono">${item.plugin_instance_id || ""}</td>
      <td>${item.expires_at || ""}</td>
      <td>${item.note || ""}</td>
      <td><button class="secondary">Edit</button></td>
    `;
    tr.querySelector("button").addEventListener("click", () => {
      document.getElementById("license_key").value = item.license_key || "";
      document.getElementById("license_status").value = item.status || "active";
      document.getElementById("domain").value = item.domain || "";
      document.getElementById("plugin_instance_id").value = item.plugin_instance_id || "";
      document.getElementById("note").value = item.note || "";
      document.getElementById("expires_at").value = item.expires_at ? item.expires_at.slice(0,16) : "";
    });
    rows.appendChild(tr);
  }
}

async function upsertUser() {
  try {
    const payload = {
      username: document.getElementById("u_username").value.trim(),
      password: document.getElementById("u_password").value,
      is_active: document.getElementById("u_active").checked,
      is_superadmin: document.getElementById("u_superadmin").checked,
      twofa_enabled: document.getElementById("u_twofa").checked,
      twofa_secret: document.getElementById("u_twofa_secret").value.trim(),
    };
    if (!payload.username) throw new Error("Username is required.");
    await api("/admin/api/user/upsert", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(payload),
    });
    status("User saved.");
    document.getElementById("u_password").value = "";
    await loadUsers();
  } catch (e) {
    status(e.message, false);
  }
}

async function deleteUser(username) {
  if (!confirm("Delete user '" + username + "'?")) return;
  try {
    await api("/admin/api/user/delete", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({username}),
    });
    status("User deleted.");
    await loadUsers();
  } catch (e) {
    status(e.message, false);
  }
}

async function loadUsers() {
  const data = await api("/admin/api/user/list");
  const rows = document.getElementById("user_rows");
  rows.innerHTML = "";
  for (const item of data.items || []) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td class="mono">${item.username}</td>
      <td>${item.is_active ? "yes" : "no"}</td>
      <td>${item.is_superadmin ? "yes" : "no"}</td>
      <td>${item.twofa_enabled ? "yes" : "no"}</td>
      <td>
        <button class="secondary edit">Edit</button>
        <button class="secondary del">Delete</button>
      </td>
    `;
    tr.querySelector(".edit").addEventListener("click", () => {
      document.getElementById("u_username").value = item.username;
      document.getElementById("u_password").value = "";
      document.getElementById("u_active").checked = !!item.is_active;
      document.getElementById("u_superadmin").checked = !!item.is_superadmin;
      document.getElementById("u_twofa").checked = !!item.twofa_enabled;
      document.getElementById("u_twofa_secret").value = "";
    });
    tr.querySelector(".del").addEventListener("click", () => deleteUser(item.username));
    rows.appendChild(tr);
  }
}

checkSession();
</script>
</body>
</html>
"""

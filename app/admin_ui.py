ADMIN_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Pay By QR Admin</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 24px; background: #f7f7f9; color: #1d1d1f; }
    .card { background: #fff; border: 1px solid #ddd; border-radius: 8px; padding: 16px; margin-bottom: 16px; }
    .row { display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 8px; }
    input, select, button { padding: 8px; border: 1px solid #bbb; border-radius: 6px; }
    input[type="text"], input[type="datetime-local"] { min-width: 260px; }
    button { cursor: pointer; background: #0a66c2; color: #fff; border: none; }
    button.secondary { background: #555; }
    table { width: 100%; border-collapse: collapse; font-size: 13px; }
    th, td { border-bottom: 1px solid #ececec; text-align: left; padding: 8px; vertical-align: top; }
    th { background: #fafafa; }
    .mono { font-family: Consolas, monospace; font-size: 12px; }
    .status { margin-top: 8px; font-size: 13px; }
  </style>
</head>
<body>
  <h1>Pay By QR Admin</h1>

  <div class="card">
    <h3>Admin Token</h3>
    <div class="row">
      <input id="token" type="text" placeholder="Paste X-Admin-Token">
      <button class="secondary" onclick="loadLicenses()">Load licenses</button>
    </div>
    <div class="status" id="status"></div>
  </div>

  <div class="card">
    <h3>Create / Update License</h3>
    <div class="row">
      <input id="license_key" type="text" placeholder="license key">
      <select id="status_field">
        <option value="active">active</option>
        <option value="blocked">blocked</option>
        <option value="expired">expired</option>
      </select>
      <input id="domain" type="text" placeholder="domain (example.com or *)">
    </div>
    <div class="row">
      <input id="plugin_instance_id" type="text" placeholder="plugin instance id (optional)">
      <input id="expires_at" type="datetime-local" placeholder="expires at">
      <input id="note" type="text" placeholder="note">
      <button onclick="upsertLicense()">Save</button>
    </div>
  </div>

  <div class="card">
    <h3>Licenses</h3>
    <div class="row">
      <input id="search" type="text" placeholder="search key/domain/note">
      <button class="secondary" onclick="loadLicenses()">Refresh</button>
    </div>
    <table>
      <thead>
        <tr>
          <th>License</th><th>Status</th><th>Domain</th><th>Instance</th><th>Expires</th><th>Note</th><th>Actions</th>
        </tr>
      </thead>
      <tbody id="rows"></tbody>
    </table>
  </div>

<script>
function status(msg, ok=true) {
  const el = document.getElementById("status");
  el.textContent = msg;
  el.style.color = ok ? "#0a7a3d" : "#b00020";
}

function token() {
  return document.getElementById("token").value.trim();
}

async function api(path, options={}) {
  const t = token();
  if (!t) throw new Error("Admin token is required.");
  const headers = Object.assign({}, options.headers || {}, {"X-Admin-Token": t});
  const resp = await fetch(path, Object.assign({}, options, {headers}));
  const body = await resp.json();
  if (!resp.ok) {
    throw new Error(body.detail || JSON.stringify(body));
  }
  return body;
}

function fillForm(item) {
  document.getElementById("license_key").value = item.license_key || "";
  document.getElementById("status_field").value = item.status || "active";
  document.getElementById("domain").value = item.domain || "";
  document.getElementById("plugin_instance_id").value = item.plugin_instance_id || "";
  document.getElementById("note").value = item.note || "";
  document.getElementById("expires_at").value = item.expires_at ? item.expires_at.slice(0,16) : "";
}

async function upsertLicense() {
  try {
    const expires = document.getElementById("expires_at").value;
    const payload = {
      license_key: document.getElementById("license_key").value.trim(),
      status: document.getElementById("status_field").value,
      domain: document.getElementById("domain").value.trim(),
      plugin_instance_id: document.getElementById("plugin_instance_id").value.trim(),
      expires_at: expires ? new Date(expires).toISOString() : null,
      note: document.getElementById("note").value.trim()
    };
    if (!payload.license_key) throw new Error("License key is required.");
    await api("/v1/admin/license/upsert", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(payload)
    });
    status("License saved.");
    await loadLicenses();
  } catch (e) {
    status(e.message, false);
  }
}

async function loadLicenses() {
  try {
    const q = document.getElementById("search").value.trim();
    const query = q ? "?q=" + encodeURIComponent(q) + "&limit=200" : "?limit=200";
    const data = await api("/v1/admin/license/list" + query);
    const rows = document.getElementById("rows");
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
      tr.querySelector("button").addEventListener("click", () => fillForm(item));
      rows.appendChild(tr);
    }
    status("Loaded " + (data.items || []).length + " license(s).");
  } catch (e) {
    status(e.message, false);
  }
}
</script>
</body>
</html>
"""

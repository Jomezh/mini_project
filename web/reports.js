// reports.js — compat SDK, no imports needed
let allData    = [];
let userData   = [];
let adminData  = [];
let filteredAll   = [];
let filteredUser  = [];
let filteredAdmin = [];

db.ref("inspection_records").on("value", (snapshot) => {
  allData = []; userData = []; adminData = [];

  const raw = snapshot.val() || {};
  for (let id in raw) {
    const record = { id, ...raw[id] };
    allData.push(record);
    if (record.role === "user")  userData.push(record);
    if (record.role === "admin") adminData.push(record);
  }

  filteredAll   = [...allData];
  filteredUser  = [...userData];
  filteredAdmin = [...adminData];

  renderAll(filteredAll);
  renderUser(filteredUser);
  renderAdmin(filteredAdmin);
  updateSummaries();
});

// ── Badges ────────────────────────────────────────────────────────────────────
function spoilageBadge(level) {
  if (!level) return "—";
  const cls = level === "High" ? "badge-high" : level === "Medium" ? "badge-medium" : "badge-low";
  return `<span class="badge ${cls}">${level}</span>`;
}
function roleBadge(role) {
  if (!role) return "—";
  return `<span class="badge ${role === "admin" ? "badge-admin" : "badge-user"}">${role}</span>`;
}

// ── Renderers ─────────────────────────────────────────────────────────────────
function renderAll(list) {
  const tbody = document.getElementById("allTable");
  tbody.innerHTML = list.length
    ? list.map(r => `<tr>
        <td>${r.id}</td>
        <td>${r.user_id || "—"}</td>
        <td>${roleBadge(r.role)}</td>
        <td>${r.food_type || "—"}</td>
        <td>${spoilageBadge(r.spoilage_level)}</td>
        <td>${r.timestamp || "—"}</td>
      </tr>`).join("")
    : `<tr><td colspan="6" style="text-align:center;padding:32px;color:#aaa;">No records found.</td></tr>`;
}

function renderUser(list) {
  const tbody = document.getElementById("userTable");
  tbody.innerHTML = list.length
    ? list.map(r => `<tr>
        <td>${r.id}</td>
        <td>${r.user_id || "—"}</td>
        <td>${r.food_type || "—"}</td>
        <td>${spoilageBadge(r.spoilage_level)}</td>
        <td>${r.timestamp || "—"}</td>
      </tr>`).join("")
    : `<tr><td colspan="5" style="text-align:center;padding:32px;color:#aaa;">No user records found.</td></tr>`;
}

function renderAdmin(list) {
  const tbody = document.getElementById("adminTable");
  tbody.innerHTML = list.length
    ? list.map(r => `<tr>
        <td>${r.id}</td>
        <td>${r.user_id || "—"}</td>
        <td>${r.food_type || "—"}</td>
        <td>${spoilageBadge(r.spoilage_level)}</td>
        <td>${r.timestamp || "—"}</td>
        <td>${r.action_taken || "—"}</td>
      </tr>`).join("")
    : `<tr><td colspan="6" style="text-align:center;padding:32px;color:#aaa;">No admin records found.</td></tr>`;
}

// ── Summary cards ─────────────────────────────────────────────────────────────
function updateSummaries() {
  document.getElementById("all-total").textContent   = allData.length;
  document.getElementById("all-high").textContent    = allData.filter(r => r.spoilage_level === "High").length;
  document.getElementById("all-medium").textContent  = allData.filter(r => r.spoilage_level === "Medium").length;
  document.getElementById("all-low").textContent     = allData.filter(r => r.spoilage_level === "Low").length;

  document.getElementById("user-total").textContent  = userData.length;
  document.getElementById("user-high").textContent   = userData.filter(r => r.spoilage_level === "High").length;
  document.getElementById("user-top-food").textContent = topFood(userData);

  document.getElementById("admin-total").textContent = adminData.length;
  document.getElementById("admin-high").textContent  = adminData.filter(r => r.spoilage_level === "High").length;
  document.getElementById("admin-top-food").textContent = topFood(adminData);
}

function topFood(list) {
  if (!list.length) return "—";
  const freq = {};
  list.forEach(r => { if (r.food_type) freq[r.food_type] = (freq[r.food_type] || 0) + 1; });
  return Object.entries(freq).sort((a, b) => b[1] - a[1])[0]?.[0] || "—";
}

// ── Tab switching ─────────────────────────────────────────────────────────────
function switchTab(name, btn) {
  document.querySelectorAll(".tab-panel").forEach(p => p.classList.remove("active"));
  document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
  document.getElementById("tab-" + name).classList.add("active");
  btn.classList.add("active");
}

// ── Search & filter ───────────────────────────────────────────────────────────
function filterAll(q) {
  q = q.toLowerCase();
  filteredAll = allData.filter(r =>
    (r.id||"").toLowerCase().includes(q) ||
    (r.food_type||"").toLowerCase().includes(q) ||
    (r.user_id||"").toLowerCase().includes(q)
  );
  renderAll(filteredAll);
}
function filterAllBySpoilage(level) {
  filteredAll = level ? allData.filter(r => r.spoilage_level === level) : [...allData];
  renderAll(filteredAll);
}
function filterUser(q) {
  q = q.toLowerCase();
  filteredUser = userData.filter(r =>
    (r.id||"").toLowerCase().includes(q) ||
    (r.user_id||"").toLowerCase().includes(q) ||
    (r.food_type||"").toLowerCase().includes(q)
  );
  renderUser(filteredUser);
}
function filterUserBySpoilage(level) {
  filteredUser = level ? userData.filter(r => r.spoilage_level === level) : [...userData];
  renderUser(filteredUser);
}
function filterAdmin(q) {
  q = q.toLowerCase();
  filteredAdmin = adminData.filter(r =>
    (r.id||"").toLowerCase().includes(q) ||
    (r.user_id||"").toLowerCase().includes(q) ||
    (r.food_type||"").toLowerCase().includes(q)
  );
  renderAdmin(filteredAdmin);
}
function filterAdminBySpoilage(level) {
  filteredAdmin = level ? adminData.filter(r => r.spoilage_level === level) : [...adminData];
  renderAdmin(filteredAdmin);
}

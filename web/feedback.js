// feedback.js — reads from Firestore "reports" collection
// Features: truncated message preview, click to open full message modal,
//           search, status filter, mark as resolved

let allFeedback = [];
let activeFilter = "all";
const PREVIEW_LEN = 60; // characters shown before truncation

// ── Load from Firestore "reports" collection in real-time ─────────────────────
firebase
  .firestore()
  .collection("reports")
  .onSnapshot(
    (snapshot) => {
      allFeedback = [];
      snapshot.forEach((doc) => {
        allFeedback.push({ id: doc.id, ...doc.data() });
      });
      allFeedback.sort((a, b) => toMs(b) - toMs(a));
      updateCounts();
      applyFilters();
    },
    (error) => {
      console.error("Firestore error:", error);
      document.getElementById("feedbackTable").innerHTML = `
    <tr>
      <td colspan="5" style="text-align:center;padding:36px;color:#ef4444;">
        Failed to load feedback: ${error.message}<br>
        <small style="color:#64748b">Check Firestore security rules.</small>
      </td>
    </tr>`;
    },
  );

// ── Timestamp helpers ─────────────────────────────────────────────────────────
function toMs(item) {
  const t = item.timestamp || item.createdAt || item.date || 0;
  if (!t) return 0;
  if (t.toDate) return t.toDate().getTime();
  if (t.seconds) return t.seconds * 1000;
  return new Date(t).getTime() || 0;
}

function formatDate(item) {
  const t = item.timestamp || item.createdAt || item.date;
  if (!t) return "—";
  let d;
  if (t.toDate) d = t.toDate();
  else if (t.seconds) d = new Date(t.seconds * 1000);
  else d = new Date(t);
  return isNaN(d) ? String(t) : d.toLocaleString();
}

// ── Field resolvers ───────────────────────────────────────────────────────────
function getUser(item) {
  return item.user || item.userName || item.name || item.displayName || "—";
}
function getEmail(item) {
  return item.email || item.userEmail || item.user_email || "";
}
function getMessage(item) {
  return item.message || item.feedback || item.text || item.description || "—";
}

// ── Counts ────────────────────────────────────────────────────────────────────
function updateCounts() {
  const pending = allFeedback.filter((f) => f.status !== "resolved").length;
  const resolved = allFeedback.filter((f) => f.status === "resolved").length;
  document.getElementById("countTotal").textContent = allFeedback.length;
  document.getElementById("countPending").textContent = pending;
  document.getElementById("countResolved").textContent = resolved;
}

// ── Filter tab ────────────────────────────────────────────────────────────────
function setFilter(filter, btn) {
  activeFilter = filter;
  document
    .querySelectorAll(".filter-tab")
    .forEach((b) => b.classList.remove("active"));
  btn.classList.add("active");
  applyFilters();
}

// ── Search + status filter ────────────────────────────────────────────────────
function applyFilters() {
  const q = (document.getElementById("searchInput").value || "")
    .toLowerCase()
    .trim();
  let list = allFeedback;

  if (activeFilter === "pending")
    list = list.filter((f) => f.status !== "resolved");
  if (activeFilter === "resolved")
    list = list.filter((f) => f.status === "resolved");

  if (q) {
    list = list.filter(
      (f) =>
        getUser(f).toLowerCase().includes(q) ||
        getEmail(f).toLowerCase().includes(q) ||
        getMessage(f).toLowerCase().includes(q),
    );
  }
  renderFeedback(list);
}

// ── Render ────────────────────────────────────────────────────────────────────
function renderFeedback(list) {
  const tbody = document.getElementById("feedbackTable");

  if (!list.length) {
    tbody.innerHTML = `
      <tr>
        <td colspan="5" style="text-align:center;padding:36px;color:#64748b;">
          No feedback found.
        </td>
      </tr>`;
    return;
  }

  tbody.innerHTML = list
    .map((item) => {
      const isResolved = item.status === "resolved";
      const user = getUser(item);
      const email = getEmail(item);
      const fullMsg = getMessage(item);
      const date = formatDate(item);

      // Truncate message for table preview
      const isLong = fullMsg.length > PREVIEW_LEN;
      const preview = isLong
        ? fullMsg.slice(0, PREVIEW_LEN).trimEnd() + "…"
        : fullMsg;

      // Escape for use in onclick attribute
      const safeId = item.id.replace(/'/g, "\\'");

      const msgCell = isLong
        ? `<span class="msg-preview" onclick="openModal('${safeId}')" title="Click to read full message">${preview}</span>`
        : `<span class="msg-short">${preview}</span>`;

      const userCell = email
        ? `<div style="font-weight:500">${user}</div><div style="font-size:0.78rem;color:#94a3b8">${email}</div>`
        : `<span style="font-weight:500">${user}</span>`;

      const statusBadge = isResolved
        ? `<span class="status-badge status-resolved">✔ Resolved</span>`
        : `<span class="status-badge status-pending">● Pending</span>`;

      const resolvedInfo =
        isResolved && item.resolvedBy
          ? `<div style="font-size:0.72rem;color:#64748b;margin-top:4px;">by ${item.resolvedBy}<br/>${item.resolvedAt || ""}</div>`
          : "";

      const actionBtn = isResolved
        ? `<button class="resolve-btn" disabled>Resolved</button>`
        : `<button class="resolve-btn" onclick="markResolved('${safeId}')">Mark Resolved</button>`;

      return `
      <tr id="row-${item.id}">
        <td>${userCell}</td>
        <td>${msgCell}</td>
        <td style="white-space:nowrap;color:#64748b;font-size:0.82rem">${date}</td>
        <td>${statusBadge}${resolvedInfo}</td>
        <td>${actionBtn}</td>
      </tr>`;
    })
    .join("");
}

// ── Modal open ────────────────────────────────────────────────────────────────
function openModal(id) {
  const item = allFeedback.find((f) => f.id === id);
  if (!item) return;

  document.getElementById("modalUser").textContent = getUser(item);
  document.getElementById("modalEmail").textContent =
    getEmail(item) || "No email";
  document.getElementById("modalMessage").textContent = getMessage(item);
  document.getElementById("modalDate").textContent =
    "Sent: " + formatDate(item);
  document.getElementById("msgModal").classList.add("open");
  document.body.style.overflow = "hidden";
}

// ── Modal close ───────────────────────────────────────────────────────────────
function closeModalDirect() {
  document.getElementById("msgModal").classList.remove("open");
  document.body.style.overflow = "";
}

function closeModal(event) {
  // Only close if clicking the overlay itself, not the box inside
  if (event.target === document.getElementById("msgModal")) {
    closeModalDirect();
  }
}

// Close with Escape key
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") closeModalDirect();
});

// ── Mark as resolved ──────────────────────────────────────────────────────────
function markResolved(id) {
  const btn = document.querySelector(`#row-${id} .resolve-btn`);
  if (btn) {
    btn.disabled = true;
    btn.textContent = "Saving…";
  }

  auth.onAuthStateChanged(
    (user) => {
      const resolvedBy = user ? user.email : "admin";
      const resolvedAt = new Date().toLocaleString();

      firebase
        .firestore()
        .collection("reports")
        .doc(id)
        .update({ status: "resolved", resolvedBy, resolvedAt })
        .catch((err) => {
          console.error("Failed to resolve:", err);
          if (btn) {
            btn.disabled = false;
            btn.textContent = "Mark Resolved";
          }
        });
    },
    { once: true },
  );
}

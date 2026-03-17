// ── API helper ──────────────────────────────────────────────────────────────
const BASE = "";  // same origin

function getToken() { return localStorage.getItem("token"); }
function getUser()  { return JSON.parse(localStorage.getItem("user") || "null"); }

function saveAuth(data) {
  localStorage.setItem("token", data.token);
  localStorage.setItem("user", JSON.stringify({ id: data.user_id, name: data.name, email: data.email }));
}

function clearAuth() {
  localStorage.removeItem("token");
  localStorage.removeItem("user");
}

async function api(method, path, body) {
  const headers = { "Content-Type": "application/json" };
  const token = getToken();
  if (token) headers["Authorization"] = "Bearer " + token;

  const res = await fetch(BASE + path, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (res.status === 401) {
    clearAuth();
    window.location.href = "/index.html";
    return;
  }

  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || "Request failed");
  return data;
}

const API = {
  // auth
  register: (email, name, password) => api("POST", "/api/auth/register", { email, name, password }),
  login:    (email, password)         => api("POST", "/api/auth/login",    { email, password }),

  // groups
  listGroups:  ()              => api("GET",    "/api/groups"),
  createGroup: (name, code)    => api("POST",   "/api/groups", { name, invitation_code: code }),
  joinGroup:   (code)          => api("POST",   "/api/groups/join", { invitation_code: code }),
  getGroup:    (id)            => api("GET",    `/api/groups/${id}`),
  leaveGroup:  (id)            => api("DELETE", `/api/groups/${id}/leave`),

  // meetings
  getGroupMeetings:  (groupId)   => api("GET",  `/api/meetings/group/${groupId}`),
  getFolderMeetings: (folderId)  => api("GET",  `/api/meetings/folder/${folderId}`),
  getMeeting:        (id)        => api("GET",  `/api/meetings/${id}`),
  createMeeting:     (body)      => api("POST", "/api/meetings", body),
  createFolder:      (name, gid) => api("POST", "/api/meetings/folders", { name, group_id: gid }),
  finishMeeting:     (id)        => api("POST", `/api/meetings/${id}/finish`),

  // availability
  submitAvailability: (meetingId, slots)  => api("POST", `/api/availability/${meetingId}`, { slots }),
  getAvailability:    (meetingId)         => api("GET",  `/api/availability/${meetingId}`),

  // records
  getRecord:         (meetingId)          => api("GET",  `/api/records/${meetingId}`),
  saveNote:          (meetingId, text)    => api("POST", `/api/records/${meetingId}/note`, { record_text: text }),
  decideTime:        (meetingId, body)    => api("POST", `/api/records/${meetingId}/decide-time`, body),
  getAttendance:     (meetingId)          => api("GET",  `/api/records/${meetingId}/attendance`),
  saveAttendance:    (meetingId, items)   => api("POST", `/api/records/${meetingId}/attendance`, { items }),
  getSummary:        (meetingId)          => api("GET",  `/api/records/${meetingId}/summary`),
};

// ── Toast ────────────────────────────────────────────────────────────────────
function showToast(msg, duration = 2500) {
  let el = document.getElementById("toast");
  if (!el) {
    el = document.createElement("div");
    el.id = "toast";
    document.body.appendChild(el);
  }
  el.textContent = msg;
  el.classList.add("show");
  clearTimeout(el._timer);
  el._timer = setTimeout(() => el.classList.remove("show"), duration);
}

// ── Modal helpers ────────────────────────────────────────────────────────────
function openModal(id) {
  document.getElementById(id).classList.add("open");
}
function closeModal(id) {
  document.getElementById(id).classList.remove("open");
}

// ── Auth guard ───────────────────────────────────────────────────────────────
function requireAuth() {
  if (!getToken()) {
    window.location.href = "/index.html";
    return null;
  }
  return getUser();
}

// ── Topbar user display ───────────────────────────────────────────────────────
function initTopbar() {
  const user = getUser();
  const el = document.getElementById("topbar-user");
  if (el && user) el.textContent = user.email;
  const logoutBtn = document.getElementById("btn-logout");
  if (logoutBtn) logoutBtn.addEventListener("click", () => {
    clearAuth();
    window.location.href = "/index.html";
  });
}

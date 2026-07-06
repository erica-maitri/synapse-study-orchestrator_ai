const API_BASE = "http://localhost:8000";

function getHeaders() {
  const token = localStorage.getItem("synapse_token");
  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

async function request(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  const response = await fetch(url, {
    ...options,
    headers: {
      ...getHeaders(),
      ...options.headers,
    },
  });

  if (response.status === 401) {
    localStorage.removeItem("synapse_token");
    window.dispatchEvent(new Event("auth-change"));
    throw new Error("Session expired. Please log in again.");
  }

  if (!response.ok) {
    const errData = await response.json().catch(() => ({}));
    throw new Error(errData.detail || "Request failed");
  }

  return response.json();
}

export const api = {
  login: async (username, password) => {
    const data = await request("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    });
    localStorage.setItem("synapse_token", data.access_token);
    window.dispatchEvent(new Event("auth-change"));
    return data;
  },

  register: async (username, password) => {
    return request("/api/auth/register", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    });
  },

  logout: () => {
    localStorage.removeItem("synapse_token");
    window.dispatchEvent(new Event("auth-change"));
  },

  isLoggedIn: () => {
    return !!localStorage.getItem("synapse_token");
  },

  getTasks: () => request("/api/tasks"),
  createTask: (task) => request("/api/tasks", { method: "POST", body: JSON.stringify(task) }),
  updateTask: (id, task) => request(`/api/tasks/${id}`, { method: "PUT", body: JSON.stringify(task) }),
  deleteTask: (id) => request(`/api/tasks/${id}`, { method: "DELETE" }),

  getCalendar: () => request("/api/calendar"),
  createCalendarEvent: (event) => request("/api/calendar", { method: "POST", body: JSON.stringify(event) }),
  deleteCalendarEvent: (id) => request(`/api/calendar/${id}`, { method: "DELETE" }),
  
  getExportUrl: () => {
    const token = localStorage.getItem("synapse_token") || "";
    return `${API_BASE}/api/calendar/export?token=${token}`; // Token can be passed in query or fetched on page direct
  },

  getFlashcards: () => request("/api/flashcards"),
  getDueFlashcards: (date, all) => {
    const params = [];
    if (date) params.push(`date=${date}`);
    if (all) params.push(`all=true`);
    const query = params.length > 0 ? `?${params.join("&")}` : "";
    return request(`/api/vault/due${query}`);
  },
  createFlashcard: (fc) => request("/api/flashcards", { method: "POST", body: JSON.stringify(fc) }),
  updateFlashcard: (id, fc) => request(`/api/flashcards/${id}`, { method: "PUT", body: JSON.stringify(fc) }),
  deleteFlashcard: (id) => request(`/api/flashcards/${id}`, { method: "DELETE" }),
  reviewFlashcard: (id, quality) => request(`/api/flashcards/${id}/review`, {
    method: "POST",
    body: JSON.stringify({ quality }),
  }),
  getVaultStreak: () => request("/api/vault/streak"),
  getVaultHistory: (days) => request(`/api/vault/history?days=${days || 30}`),

  getAuditLogs: () => request("/api/audit-logs"),
  runAgentGoal: (goal) => request("/api/agent/run-goal", {
    method: "POST",
    body: JSON.stringify({ goal }),
  }),
  uploadFilePipeline: async (file) => {
    const token = localStorage.getItem("synapse_token");
    const formData = new FormData();
    formData.append("file", file);
    const url = `${API_BASE}/api/agent/upload-file`;
    const response = await fetch(url, {
      method: "POST",
      body: formData,
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    });
    if (response.status === 401) {
      localStorage.removeItem("synapse_token");
      window.dispatchEvent(new Event("auth-change"));
      throw new Error("Session expired. Please log in again.");
    }
    if (!response.ok) {
      const errData = await response.json().catch(() => ({}));
      throw new Error(errData.detail || "File upload failed");
    }
    return response.json();
  },
};

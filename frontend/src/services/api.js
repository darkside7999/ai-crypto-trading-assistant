const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || `${window.location.protocol}//${window.location.hostname}:8000`;

let token = localStorage.getItem("access_token");

export function setToken(nextToken) {
  token = nextToken;
  if (nextToken) {
    localStorage.setItem("access_token", nextToken);
  } else {
    localStorage.removeItem("access_token");
  }
}

async function request(path, options = {}) {
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {})
  };
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.detail || data.message || "Request failed");
  }
  return data;
}

export const api = {
  login: (username, password) => request("/auth/login", { method: "POST", body: JSON.stringify({ username, password }) }),
  status: () => request("/bot/status"),
  start: () => request("/bot/start", { method: "POST" }),
  stop: () => request("/bot/stop", { method: "POST" }),
  setDemo: () => request("/bot/mode/demo", { method: "POST" }),
  setReal: () => request("/bot/mode/real", { method: "POST", body: JSON.stringify({ confirmation: "ENABLE_REAL_MODE" }) }),
  setManual: () => request("/bot/mode/manual", { method: "POST" }),
  setAutonomous: () => request("/bot/mode/autonomous", { method: "POST" }),
  tick: () => request("/bot/tick", { method: "POST" }),
  riskSettings: () => request("/settings/risk"),
  updateRiskSettings: (settings) => request("/settings/risk", { method: "PUT", body: JSON.stringify(settings) }),
  openTrades: () => request("/trades/open"),
  history: () => request("/trades/history"),
  confirmBuy: (id) => request(`/trades/${id}/confirm-buy`, { method: "POST" }),
  confirmSell: (id) => request(`/trades/${id}/confirm-sell`, { method: "POST" }),
  convertLongTerm: (id) => request(`/trades/${id}/convert-long-term`, { method: "POST" }),
  decisions: () => request("/ai/decisions"),
  logs: () => request("/logs"),
  telegramTest: () => request("/telegram/test", { method: "POST" }),
  aiSettings: () => request("/ai/settings"),
  updateAiSettings: (settings) => request("/ai/settings", { method: "PUT", body: JSON.stringify(settings) }),
  aiCosts: () => request("/ai/costs"),
  aiAnalyze: (payload = {}) => request("/ai/analyze", { method: "POST", body: JSON.stringify(payload) }),
  marketIntel: () => request("/market/intel")
};

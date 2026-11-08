// Fetch wrapper + session helpers shared by login and app.
let csrfToken = null;

export class ApiError extends Error {
  constructor(status, message) { super(message); this.status = status; }
}

export function setCsrf(token) { csrfToken = token; }

export async function api(path, { method = "GET", body } = {}) {
  const headers = { Accept: "application/json" };
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (method !== "GET" && csrfToken) headers["X-CSRF-Token"] = csrfToken;
  let res;
  try {
    res = await fetch(path, { method, headers, credentials: "same-origin", body: body === undefined ? undefined : JSON.stringify(body) });
  } catch {
    throw new ApiError(0, "Network error. Is the AutoJob server running?");
  }
  const data = await res.json().catch(() => ({}));
  if (res.status === 401 && !path.startsWith("/api/auth/")) {
    location.href = `/login?next=${encodeURIComponent(location.pathname)}`;
  }
  if (!res.ok) throw new ApiError(res.status, data.error || `Request failed (${res.status})`);
  return data;
}

export async function getSession() {
  try {
    const me = await api("/api/auth/me");
    setCsrf(me.csrf_token);
    return me;
  } catch {
    return null;
  }
}

const ESC = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
export const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => ESC[c]);

// Only allow http(s) links from data into href attributes.
export const safeUrl = (u) => (/^https?:\/\//i.test(u || "") ? esc(u) : "#");

export const icon = (id, cls = "icon") => `<svg class="${cls}" aria-hidden="true"><use href="/assets/shared/sprite.svg#i-${id}"/></svg>`;

export function toast(message, kind = "ok") {
  let box = document.querySelector(".toasts");
  if (!box) {
    box = document.createElement("div");
    box.className = "toasts";
    box.setAttribute("role", "status");
    box.setAttribute("aria-live", "polite");
    document.body.append(box);
  }
  const el = document.createElement("div");
  el.className = `toast ${kind === "error" ? "error" : ""}`;
  el.innerHTML = `${icon(kind === "error" ? "x" : "check")}<span></span>`;
  el.querySelector("span").textContent = message;
  box.append(el);
  setTimeout(() => el.remove(), 4200);
}

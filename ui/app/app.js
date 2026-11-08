import { api, getSession, toast, icon, esc } from "/assets/shared/api.js";
import { gsap, reduced, scramble } from "/assets/shared/motion.js";
import { mountThemeToggle } from "/assets/shared/theme.js";
import overview from "./views/overview.js";
import pipeline from "./views/pipeline.js";
import opportunities from "./views/opportunities.js";
import inbox from "./views/inbox.js";
import profile from "./views/profile.js";
import consoleView from "./views/console.js";
import users from "./views/users.js";

const POLL_MS = 3000;
const VIEWS = {
  overview: { ...overview, icon: "grid", label: "Overview" },
  pipeline: { ...pipeline, icon: "pipeline", label: "Pipeline" },
  opportunities: { ...opportunities, icon: "briefcase", label: "Opportunities" },
  inbox: { ...inbox, icon: "inbox", label: "Inbox" },
  profile: { ...profile, icon: "user", label: "Dossier" },
  console: { ...consoleView, icon: "terminal", label: "Console", perm: "console:use" },
  users: { ...users, icon: "users", label: "Users", perm: "users:manage" },
};

const viewEl = document.getElementById("view");
const agentListeners = new Set();
let current = null;
let agentState = { running: false };

function makeCtx(session) {
  return {
    session,
    can: (perm) => session.permissions.includes(perm),
    onAgent(fn) { agentListeners.add(fn); fn(agentState); return () => agentListeners.delete(fn); },
    refreshAgent: pollAgent,
    navigate,
  };
}

function renderNav(ctx) {
  document.getElementById("nav").innerHTML = Object.entries(VIEWS)
    .filter(([, v]) => !v.perm || ctx.can(v.perm))
    .map(([key, v]) => `<a class="side-link" href="/app/${key}" data-view="${key}">${icon(v.icon)}${v.label}</a>`)
    .join("");
}

async function navigate(path, push = true) {
  const key = path.replace(/^\/app\/?/, "").split("/")[0] || "overview";
  const view = VIEWS[key] && (!VIEWS[key].perm || window.__ctx.can(VIEWS[key].perm)) ? key : "overview";
  if (push) history.pushState({}, "", `/app/${view}`);
  current?.destroy?.();
  document.querySelectorAll(".side-link[data-view]").forEach((a) => {
    if (a.dataset.view === view) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current");
  });
  scramble(document.getElementById("viewTitle"), VIEWS[view].label);
  document.title = `${VIEWS[view].label} · AutoJob`;
  document.getElementById("side").classList.remove("open");
  viewEl.innerHTML = `<div class="empty"><span class="spinner"></span></div>`;
  current = VIEWS[view];
  try {
    await current.render(viewEl, window.__ctx);
  } catch (err) {
    viewEl.innerHTML = `<div class="error-box">Could not load this view: ${esc(err.message)}</div>`;
  }
  if (gsap && !reduced) gsap.from(viewEl.children, { y: 10, opacity: 0, stagger: 0.04, duration: 0.3, ease: "power2.out" });
  viewEl.focus({ preventScroll: true });
}

async function pollAgent() {
  try {
    agentState = await api("/api/agent/status");
  } catch { return; }
  const chip = document.getElementById("agentChip");
  chip.className = `chip ${agentState.running ? "ok" : ""}`;
  chip.innerHTML = `<span class="dot ${agentState.running ? "pulse" : ""}"></span><span>${agentState.running ? "Agent running" : "Agent idle"}</span>`;
  const toggle = document.getElementById("agentToggle");
  const label = agentState.running ? "Stop agent" : "Start agent";
  toggle.innerHTML = `${icon(agentState.running ? "stop" : "play")}<span class="hide-sm">${label}</span>`;
  toggle.setAttribute("aria-label", label);
  agentListeners.forEach((fn) => fn(agentState));
}

async function toggleAgent() {
  try {
    await api(agentState.running ? "/api/agent/stop" : "/api/agent/start", { method: "POST" });
    await pollAgent();
  } catch (err) { toast(err.message, "error"); }
}

function introShell() {
  if (!gsap || reduced) return;
  gsap.timeline()
    // clearProps: the mobile drawer is positioned by a CSS transform that GSAP's inline style would override.
    .from(".side", { x: -24, opacity: 0, duration: 0.5, clearProps: "transform,opacity" })
    .from(".side-link", { x: -12, opacity: 0, stagger: 0.03, duration: 0.3 }, "<0.15")
    .from(".top > *", { y: -8, opacity: 0, stagger: 0.03, duration: 0.3 }, "<");
}

async function init() {
  const session = await getSession();
  if (!session) { location.replace(`/login?next=${encodeURIComponent(location.pathname)}`); return; }
  window.__ctx = makeCtx(session);
  renderNav(window.__ctx);
  document.getElementById("whoEmail").textContent = session.is_demo ? "demo" : session.email;
  document.getElementById("whoRole").textContent = session.role;
  document.getElementById("demoBanner").hidden = !session.is_demo;
  const toggle = document.getElementById("agentToggle");
  toggle.hidden = !window.__ctx.can("agent:control");
  toggle.addEventListener("click", toggleAgent);

  document.getElementById("nav").addEventListener("click", (e) => {
    const a = e.target.closest("a[data-view]");
    if (!a || e.metaKey || e.ctrlKey) return;
    e.preventDefault();
    navigate(a.getAttribute("href"));
  });
  addEventListener("popstate", () => navigate(location.pathname, false));
  const menuBtn = document.getElementById("menuBtn");
  menuBtn.addEventListener("click", () => {
    const open = document.getElementById("side").classList.toggle("open");
    menuBtn.setAttribute("aria-expanded", String(open));
  });
  document.getElementById("logoutBtn").addEventListener("click", async () => {
    await api("/api/auth/logout", { method: "POST" }).catch(() => {});
    location.href = "/";
  });

  document.querySelectorAll("[data-theme-toggle]").forEach(mountThemeToggle);
  // "/" jumps to the search box on views that have one.
  addEventListener("keydown", (e) => {
    if (e.key !== "/" || /^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement?.tagName)) return;
    const box = viewEl.querySelector("input[type=search]");
    if (box) { e.preventDefault(); box.focus(); }
  });
  introShell();
  await pollAgent();
  setInterval(() => { if (!document.hidden) pollAgent(); }, POLL_MS);
  navigate(location.pathname, false);
}

init();

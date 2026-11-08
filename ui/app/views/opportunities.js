import { api, esc, icon, safeUrl, toast } from "/assets/shared/api.js";
import { gsap, reduced } from "/assets/shared/motion.js";

const FILTERS = [["all", "All"], ["high", "≥70%"], ["discovered", "New"], ["applied", "Applied"]];
const TONES = ["standard", "concise", "technical", "friendly"];
const state = { jobs: [], filter: "all", q: "", platform: "all", selected: null, proposal: "", tone: "standard" };

const scoreClass = (s) => (s >= 70 ? "hi" : s < 45 ? "lo" : "");

function visibleJobs() {
  const q = state.q.toLowerCase();
  return state.jobs.filter((j) =>
    (state.filter === "all" || (state.filter === "high" ? j.match_score >= 70 : j.status === state.filter)) &&
    (state.platform === "all" || j.platform === state.platform) &&
    (!q || `${j.title} ${j.company} ${j.tags.join(" ")}`.toLowerCase().includes(q)));
}

function renderList(el) {
  const list = el.querySelector("#jobList");
  const flip = window.Flip && gsap && !reduced ? window.Flip.getState(list.children) : null;
  const jobs = visibleJobs();
  list.innerHTML = jobs.length ? jobs.map((j) => `
    <button class="job" role="option" data-id="${j.id}" aria-selected="${state.selected?.id === j.id}" data-flip-id="${j.id}">
      <span class="score ${scoreClass(j.match_score)}">${Math.round(j.match_score)}</span>
      <span><span class="job-title">${esc(j.title)}</span>
        <span class="job-meta" style="display:block">${esc(j.company)} · ${esc(j.platform)} · ${esc(j.location || "Remote")}</span></span>
      <span class="chip ${j.status === "applied" ? "ok" : ""}">${esc(j.status)}</span>
    </button>`).join("") : `<div class="empty">No roles match these filters.</div>`;
  el.querySelector("#jobCount").textContent = `${jobs.length} of ${state.jobs.length}`;
  if (flip) window.Flip.from(flip, { duration: 0.35, ease: "power2.out", absolute: false, onEnter: (els) => gsap.fromTo(els, { opacity: 0 }, { opacity: 1, duration: 0.25 }) });
}

function renderDetail(el, ctx) {
  const box = el.querySelector("#detail");
  const j = state.selected;
  if (!j) { box.innerHTML = `<div class="empty">Select a role to draft a proposal.</div>`; return; }
  const canRun = ctx.can("jobs:run");
  box.innerHTML = `
    <div class="card-h" style="align-items:flex-start"><div>
      <p class="label" style="margin:0 0 6px">${esc(j.platform)} · ${esc(j.budget_or_salary || "Budget n/a")}</p>
      <h2 style="font-size:20px">${esc(j.title)}</h2><p class="muted" style="margin:4px 0 0">${esc(j.company)} · ${esc(j.location || "Remote")}</p></div>
      <span class="score ${scoreClass(j.match_score)}" style="font-size:28px">${j.match_score}%</span></div>
    <div class="tags">${j.tags.slice(0, 10).map((t) => `<span class="chip">${esc(t)}</span>`).join("")}</div>
    <div class="row" style="margin:16px 0">
      <a class="btn btn-sm" href="${safeUrl(j.url)}" target="_blank" rel="noopener noreferrer">${icon("globe")}Open posting</a>
      ${canRun ? `<div class="toggle" role="group" aria-label="Tone">${TONES.map((t) => `<button data-tone="${t}" aria-pressed="${state.tone === t}">${t}</button>`).join("")}</div>
      <button class="btn btn-sm btn-primary" id="gen">${icon("bolt")}${state.proposal ? "Regenerate" : "Draft proposal"}</button>` : ""}
    </div>
    ${state.proposal ? `<div class="proposal" id="prop">${esc(state.proposal)}</div>
      <div class="row" style="margin-top:12px">
        <button class="btn btn-sm" id="copy">${icon("copy")}Copy</button>
        ${ctx.can("browser:prefill") ? `<button class="btn btn-sm" id="prefill">${icon("globe")}Pre-fill in browser</button>` : ""}
        ${ctx.can("applications:write") && j.status !== "applied" ? `<button class="btn btn-sm btn-primary" id="apply">${icon("check")}Mark applied</button>` : ""}
      </div>` : canRun ? "" : `<p class="muted">Your role can browse roles but not draft proposals.</p>`}`;
  bindDetail(el, ctx);
}

async function withBusy(btn, label, fn) {
  const html = btn.innerHTML;
  btn.disabled = true;
  btn.innerHTML = `<span class="spinner"></span>${label}`;
  try { await fn(); } catch (err) { toast(err.message, "error"); } finally { if (btn.isConnected) { btn.disabled = false; btn.innerHTML = html; } }
}

function bindDetail(el, ctx) {
  const j = state.selected;
  el.querySelectorAll("[data-tone]").forEach((b) => b.addEventListener("click", () => { state.tone = b.dataset.tone; renderDetail(el, ctx); }));
  el.querySelector("#gen")?.addEventListener("click", (e) => withBusy(e.currentTarget, "Drafting", async () => {
    const res = await api("/api/proposals/generate", { method: "POST", body: { job_id: j.id, tone: state.tone } });
    state.proposal = res.proposal_text;
    renderDetail(el, ctx);
    if (gsap && !reduced) gsap.from("#prop", { opacity: 0, y: 8, duration: 0.3 });
  }));
  el.querySelector("#copy")?.addEventListener("click", async () => {
    try { await navigator.clipboard.writeText(state.proposal); toast("Proposal copied."); }
    catch { toast("Clipboard blocked by the browser.", "error"); }
  });
  el.querySelector("#prefill")?.addEventListener("click", (e) => withBusy(e.currentTarget, "Launching", async () => {
    const res = await api("/api/browser/prefill", { method: "POST", body: { job_id: j.id, proposal_text: state.proposal } });
    toast(res.message || `Pre-fill ${res.status}`);
  }));
  el.querySelector("#apply")?.addEventListener("click", (e) => withBusy(e.currentTarget, "Saving", async () => {
    await api("/api/proposals/apply", { method: "POST", body: { job_id: j.id, proposal_text: state.proposal } });
    state.jobs = state.jobs.map((x) => (x.id === j.id ? { ...x, status: "applied" } : x));
    state.selected = { ...j, status: "applied" };
    toast("Application recorded.");
    renderList(el);
    renderDetail(el, ctx);
  }));
}

function exportCsv() {
  const cols = ["title", "company", "platform", "match_score", "status", "url"];
  const cell = (v) => `"${String(v ?? "").replace(/"/g, '""')}"`;
  const csv = [cols.join(","), ...visibleJobs().map((j) => cols.map((c) => cell(j[c])).join(","))].join("\n");
  const a = Object.assign(document.createElement("a"), { href: URL.createObjectURL(new Blob([csv], { type: "text/csv" })), download: "autojob-roles.csv" });
  a.click();
  URL.revokeObjectURL(a.href);
}

export default {
  async render(el, ctx) {
    state.jobs = await api("/api/jobs");
    state.selected = null; state.proposal = "";
    const platforms = [...new Set(state.jobs.map((j) => j.platform))];
    el.innerHTML = `
      <section class="card row" style="justify-content:space-between">
        <div class="row">
          <label class="sr-only" for="q">Search roles</label>
          <input class="input" id="q" type="search" placeholder="Search title, company, skill…" style="width:min(280px,100%)" value="${esc(state.q)}">
          <label class="sr-only" for="plat">Platform</label>
          <select class="select" id="plat" style="width:auto"><option value="all">All platforms</option>${platforms.map((p) => `<option ${p === state.platform ? "selected" : ""}>${esc(p)}</option>`).join("")}</select>
          <div class="toggle" role="group" aria-label="Filter">${FILTERS.map(([k, l]) => `<button data-filter="${k}" aria-pressed="${state.filter === k}">${l}</button>`).join("")}</div>
        </div>
        <div class="row">
          <button class="btn btn-sm" id="csv">${icon("download")}CSV</button>
          ${ctx.can("jobs:run") ? `<button class="btn btn-sm btn-primary" id="scout">${icon("search")}Run scout</button>` : ""}
        </div>
      </section>
      <div class="split">
        <section class="card" style="padding:0"><div class="card-h" style="padding:16px 16px 0"><h2>Roles</h2><span class="label" id="jobCount"></span></div>
          <div id="jobList" role="listbox" aria-label="Roles" style="max-height:70vh;overflow:auto"></div></section>
        <section class="card" id="detail" style="position:sticky;top:80px"></section>
      </div>`;
    renderList(el);
    renderDetail(el, ctx);

    el.querySelector("#q").addEventListener("input", (e) => { state.q = e.target.value; renderList(el); });
    el.querySelector("#plat").addEventListener("change", (e) => { state.platform = e.target.value; renderList(el); });
    el.querySelectorAll("[data-filter]").forEach((b) => b.addEventListener("click", () => {
      state.filter = b.dataset.filter;
      el.querySelectorAll("[data-filter]").forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
      renderList(el);
    }));
    el.querySelector("#jobList").addEventListener("click", (e) => {
      const btn = e.target.closest(".job");
      if (!btn) return;
      state.selected = state.jobs.find((j) => j.id === Number(btn.dataset.id));
      state.proposal = "";
      el.querySelectorAll(".job").forEach((x) => x.setAttribute("aria-selected", String(x === btn)));
      renderDetail(el, ctx);
    });
    el.querySelector("#csv").addEventListener("click", exportCsv);
    el.querySelector("#scout")?.addEventListener("click", (e) => withBusy(e.currentTarget, "Scouting", async () => {
      const res = await api("/api/agent/run", { method: "POST", body: { mode: "scout" } });
      toast(res.logs.at(-1));
      state.jobs = await api("/api/jobs");
      renderList(el);
    }));
  },
};

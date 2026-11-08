import { api, clearToasts, esc, icon, safeUrl, toast } from "/assets/shared/api.js";
import { gsap, reduced, typeText } from "/assets/shared/motion.js";

const FILTERS = [["all", "All"], ["high", "≥70%"], ["discovered", "New"], ["applied", "Applied"]];
const TONES = ["standard", "concise", "technical", "friendly"];
const state = { jobs: [], filter: "all", q: "", platform: "all", selected: null, proposal: "", tone: "standard", email: { configured: false, simulated: false } };
const STEPS = ["Draft", "Send", "Applied"];
const EMAIL_RE = /^[^@\s]+@[^@\s]+\.[a-z]{2,}$/i;
const narrow = () => window.matchMedia("(max-width: 1100px)").matches;

function stepsHtml(j) {
  const at = j.status === "applied" ? 3 : state.proposal ? 2 : 1;
  return `<ol class="steps" aria-label="Application progress">${STEPS.map((s, i) => `
    <li class="${i + 1 < at ? "done" : i + 1 === at ? "now" : ""}" ${i + 1 === at ? 'aria-current="step"' : ""}><span class="mono">0${i + 1}</span>${s}</li>`).join("")}</ol>`;
}

function emailHtml(j) {
  if (!state.email.configured) {
    return `<p class="hint">${icon("mail")}<span>Email is not set up. Add <code>SMTP_HOST</code>, <code>SMTP_USER</code> and <code>SMTP_PASSWORD</code> to <code>.env</code>, then restart.</span></p>`;
  }
  return `<form id="mailForm" class="mail-form" novalidate>
      <div class="field"><label class="label" for="mailTo">Recruiter email</label>
        <input class="input" id="mailTo" name="mailTo" type="email" required maxlength="254" placeholder="hiring@company.com" autocomplete="off"></div>
      <div class="field"><label class="label" for="mailSubj">Subject</label>
        <input class="input" id="mailSubj" name="mailSubj" required maxlength="200" value="${esc(`Application: ${j.title}`)}"></div>
      <button class="btn btn-sm btn-primary" type="submit">${icon("mail")}${state.email.simulated ? "Send (demo)" : "Send email"} &amp; mark applied</button>
    </form>`;
}

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
  const canApply = ctx.can("applications:write") && j.status !== "applied";
  box.innerHTML = `
    <button class="btn btn-sm back-list" id="backList" type="button">${icon("back")}Back to list</button>
    ${canRun ? stepsHtml(j) : ""}
    <div class="card-h" style="align-items:flex-start"><div>
      <p class="label" style="margin:0 0 6px">${esc(j.platform)} · ${esc(j.budget_or_salary || "Budget n/a")}</p>
      <h2 style="font-size:20px">${esc(j.title)}</h2><p class="muted" style="margin:4px 0 0">${esc(j.company)} · ${esc(j.location || "Remote")}</p></div>
      <span class="score ${scoreClass(j.match_score)}" style="font-size:28px">${j.match_score}%</span></div>
    <div class="tags">${j.tags.slice(0, 10).map((t) => `<span class="chip">${esc(t)}</span>`).join("")}</div>
    <div class="row" style="margin:16px 0">
      <a class="btn btn-sm" href="${safeUrl(j.url)}" target="_blank" rel="noopener noreferrer">${icon("globe")}Open posting</a>
      ${canRun && j.status !== "applied" ? `<div class="toggle" role="group" aria-label="Tone">${TONES.map((t) => `<button data-tone="${t}" aria-pressed="${state.tone === t}">${t}</button>`).join("")}</div>
      <button class="btn btn-sm btn-primary" id="gen">${icon("bolt")}${state.proposal ? "Regenerate" : "Draft proposal"}</button>` : ""}
    </div>
    ${state.proposal ? `<label class="sr-only" for="prop">Proposal (editable)</label>
      <textarea class="proposal textarea" id="prop" rows="12">${esc(state.proposal)}</textarea>
      <p class="hint">Edit freely before sending.</p>
      <div class="row" style="margin-top:8px">
        <button class="btn btn-sm" id="copy">${icon("copy")}Copy</button>
        ${ctx.can("browser:prefill") ? `<button class="btn btn-sm" id="prefill" title="Opens the job page and fills the form. You review and press submit yourself.">${icon("globe")}Pre-fill in browser</button>` : ""}
        ${canApply ? `<button class="btn btn-sm" id="apply">${icon("check")}Mark applied</button>` : ""}
      </div>
      ${canApply ? `<div class="send-box"><p class="label">Apply by email</p>${emailHtml(j)}</div>` : ""}`
    : j.status === "applied" ? `<p class="hint">${icon("check")}<span>Already applied.</span></p>`
    : canRun ? `<p class="hint">Pick a tone, then press <strong>Draft proposal</strong>.</p>` : `<p class="muted">Your role can browse roles but not draft proposals.</p>`}`;
  bindDetail(el, ctx);
}

async function withBusy(btn, label, fn) {
  clearToasts();
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
    typeText(el.querySelector("#prop"), state.proposal);
  }));
  el.querySelector("#prop")?.addEventListener("input", (e) => { state.proposal = e.target.value; });
  el.querySelector("#backList")?.addEventListener("click", () => el.querySelector("#jobList").scrollIntoView({ behavior: reduced ? "auto" : "smooth" }));
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
    markApplied(el, ctx, j);
    toast("Application recorded.");
  }));
  el.querySelector("#mailForm")?.addEventListener("submit", (e) => {
    e.preventDefault();
    const f = e.currentTarget;
    const to = f.mailTo.value.trim();
    f.mailTo.setAttribute("aria-invalid", String(!EMAIL_RE.test(to)));
    if (!EMAIL_RE.test(to)) { clearToasts(); toast("Enter a valid recruiter email address.", "error"); f.mailTo.focus(); return; }
    withBusy(f.querySelector("button"), "Sending", async () => {
      const res = await api("/api/email/send", { method: "POST", body: { to, subject: f.mailSubj.value.trim() || `Application: ${j.title}`, body: state.proposal, job_id: j.id } });
      markApplied(el, ctx, j);
      toast(res.status === "simulated" ? `Demo: email to ${to} simulated, application recorded.` : `Email sent to ${to}. Application recorded.`);
    });
  });
}

function markApplied(el, ctx, j) {
  state.jobs = state.jobs.map((x) => (x.id === j.id ? { ...x, status: "applied" } : x));
  state.selected = { ...j, status: "applied" };
  renderList(el);
  renderDetail(el, ctx);
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
    const [jobs, email] = await Promise.all([api("/api/jobs"), api("/api/email/status").catch(() => ({ configured: false }))]);
    state.jobs = jobs; state.email = email;
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
        <section class="card detail" id="detail"></section>
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
      if (narrow()) el.querySelector("#detail").scrollIntoView({ behavior: reduced ? "auto" : "smooth", block: "start" });
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

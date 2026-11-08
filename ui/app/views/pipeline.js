import { api, esc, icon, toast } from "/assets/shared/api.js";
import { gsap, reduced } from "/assets/shared/motion.js";

const PHASES = ["Scout", "Score", "Draft", "Pre-fill", "Hold"];
let unsubscribe = null;
let lastStep = -1;
let lastLogKey = "";

function paint(el, s) {
  const step = s.active_step || 0;
  el.querySelectorAll(".ph").forEach((ph, i) => {
    ph.classList.toggle("done", i + 1 < step);
    ph.classList.toggle("active", i + 1 === step);
  });
  // Only tween when the step actually changes; polls repeat the same state.
  if (step !== lastStep) {
    el.querySelectorAll(".ph-bar > i").forEach((bar, i) => {
      const target = i + 1 <= step ? 1 : 0;
      if (gsap && !reduced) gsap.to(bar, { scaleX: target, duration: 0.5, ease: "power2.out" });
      else bar.style.transform = `scaleX(${target})`;
    });
    lastStep = step;
  }
  el.querySelector("#stage").textContent = s.stage_name || "Standby";
  const job = s.current_job;
  el.querySelector("#curJob").innerHTML = job
    ? `<strong>${esc(job.title)}</strong><div class="muted">${esc(job.company)} · ${esc(job.platform)} · <span class="acid mono">${esc(job.score)}%</span></div>`
    : `<span class="muted">No target yet. Run phase 01.</span>`;
  const term = el.querySelector("#term");
  const logs = s.logs || [];
  const key = logs.at(-1) || "";
  if (key !== lastLogKey) {
    term.innerHTML = logs.slice(-40).map((l) => `<p>${esc(l)}</p>`).join("");
    if (gsap && !reduced && lastLogKey) gsap.from(term.lastElementChild, { x: -8, opacity: 0, duration: 0.25 });
    term.scrollTop = term.scrollHeight;
    lastLogKey = key;
  }
}

export default {
  async render(el, ctx) {
    lastStep = -1; lastLogKey = "";
    const canRun = ctx.can("agent:control");
    el.innerHTML = `
      <section class="card">
        <div class="card-h"><h2 id="stage">Standby</h2>
          ${canRun ? `<div class="row"><button class="btn btn-sm" id="reset">${icon("x")}Reset</button></div>` : `<span class="chip">Read-only</span>`}</div>
        <div class="phases">${PHASES.map((p, i) => `
          <div class="ph"><span class="label">Phase 0${i + 1}</span><strong>${p}</strong><div class="ph-bar"><i></i></div>
          ${canRun ? `<button class="btn btn-sm" style="margin-top:12px;width:100%" data-step="${i + 1}" aria-label="Run phase ${i + 1}: ${p}">${icon("bolt")}Run</button>` : ""}</div>`).join("")}
        </div>
      </section>
      <div class="split">
        <section class="card"><div class="card-h"><h2>Live telemetry</h2><span class="label">auto-refresh 3s</span></div><div class="terminal" id="term" aria-live="polite"></div></section>
        <section class="card"><div class="card-h"><h2>Current target</h2></div><div id="curJob"></div>
          ${canRun ? `<p class="muted" style="font-size:13px;margin-top:20px">Start the agent from the top bar to cycle all five phases continuously, or run a single phase here.</p>` : ""}</section>
      </div>`;

    const live = await api("/api/agent/live-process");
    paint(el, live);
    unsubscribe = ctx.onAgent((s) => paint(el, s));

    el.querySelectorAll("[data-step]").forEach((b) => b.addEventListener("click", async () => {
      b.disabled = true;
      b.innerHTML = `<span class="spinner"></span>Running`;
      try { paint(el, await api("/api/agent/live-process/step", { method: "POST", body: { step: Number(b.dataset.step) } })); }
      catch (err) { toast(err.message, "error"); }
      finally { b.disabled = false; b.innerHTML = `${icon("bolt")}Run`; }
    }));
    el.querySelector("#reset")?.addEventListener("click", async () => {
      try { paint(el, await api("/api/agent/live-process/step", { method: "POST", body: { step: 0 } })); }
      catch (err) { toast(err.message, "error"); }
    });
  },
  destroy() { unsubscribe?.(); unsubscribe = null; },
};

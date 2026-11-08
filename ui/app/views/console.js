import { api, esc, icon, toast } from "/assets/shared/api.js";

const MODES = [
  ["scout", "Scout feeds", "Pull and score fresh roles from all feeds."],
  ["top_proposal", "Draft top proposal", "Write a proposal for the best unapplied match."],
  ["responder", "Responder test", "Run three sample client messages through the auto-responder."],
  ["profile", "Generate profiles", "Upwork, LinkedIn and Fiverr copy from your dossier."],
  ["full_cycle", "Full cycle", "Scout, draft and respond in one run."],
];

export default {
  async render(el) {
    el.innerHTML = `
      <div class="split">
        <section class="card"><div class="card-h"><h2>Runtime console</h2><button class="btn btn-sm" id="clear">${icon("x")}Clear</button></div>
          <div class="terminal" id="out" aria-live="polite"><p>Ready. Pick a command.</p></div></section>
        <section class="card grid" style="gap:4px">${MODES.map(([k, t, d]) => `
          <button class="job" style="grid-template-columns:1fr auto" data-mode="${k}"><span><span class="job-title">${t}</span><span class="job-meta" style="display:block">${d}</span></span>${icon("arrow")}</button>`).join("")}
        </section>
      </div>`;
    const out = el.querySelector("#out");
    const write = (lines, cls = "") => {
      out.insertAdjacentHTML("beforeend", lines.map((l) => `<p class="${cls}">${esc(l)}</p>`).join(""));
      out.scrollTop = out.scrollHeight;
    };
    el.querySelector("#clear").addEventListener("click", () => { out.innerHTML = ""; });
    el.querySelectorAll("[data-mode]").forEach((b) => b.addEventListener("click", async () => {
      b.disabled = true;
      write([`$ autojob run --mode ${b.dataset.mode}`]);
      try {
        const res = await api("/api/agent/run", { method: "POST", body: { mode: b.dataset.mode } });
        write(res.logs);
        if (res.proposal_text) write(["--- proposal ---", res.proposal_text]);
      } catch (err) { write([`ERROR: ${err.message}`], "hot"); toast(err.message, "error"); }
      finally { b.disabled = false; }
    }));
  },
};

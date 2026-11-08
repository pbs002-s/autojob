import { api, clearToasts, esc, icon, toast } from "/assets/shared/api.js";

const msgHtml = (c) => `
  <article class="msg">
    <div class="row" style="justify-content:space-between">
      <strong>${esc(c.client_name)}</strong>
      <span class="row"><span class="chip">${esc(c.platform)}</span><span class="chip ${c.status === "escalation" ? "warn" : "ok"}">${c.status === "escalation" ? "needs you" : "auto-replied"}</span></span>
    </div>
    <div class="bubble">${esc(c.last_message_text)}</div>
    <div class="bubble reply">${esc(c.last_reply_text)}</div>
  </article>`;

export default {
  async render(el, ctx) {
    let convs = await api("/api/conversations");
    let filter = "all";
    const canRun = ctx.can("jobs:run");
    el.innerHTML = `
      <div class="split">
        <section class="card" style="padding:0">
          <div class="card-h" style="padding:16px 16px 0"><h2>Conversations</h2>
            <div class="toggle" role="group" aria-label="Filter">${[["all", "All"], ["escalation", "Needs you"], ["responded", "Handled"]].map(([k, l]) => `<button data-f="${k}" aria-pressed="${k === "all"}">${l}</button>`).join("")}</div></div>
          <div id="convs" style="max-height:72vh;overflow:auto"></div>
        </section>
        <section class="card">
          <div class="card-h"><h2>Test the auto-responder</h2></div>
          ${canRun ? `<form id="sim" class="grid">
            <div class="field"><label class="label" for="cn">Client</label><input class="input" id="cn" required maxlength="120" placeholder="Dana (Acme)"></div>
            <div class="field"><label class="label" for="ce">Client email <span class="muted">(optional: emails the auto-reply)</span></label><input class="input" id="ce" type="email" maxlength="254" placeholder="dana@acme.com" autocomplete="off"></div>
            <div class="field"><label class="label" for="pf">Platform</label><select class="select" id="pf"><option>Email</option><option>Upwork</option><option>LinkedIn</option><option>Web Inbound</option></select></div>
            <div class="field"><label class="label" for="mt">Message</label><textarea class="textarea" id="mt" required maxlength="5000" placeholder="What's your rate and availability?"></textarea></div>
            <button class="btn btn-primary" type="submit">${icon("bolt")}Send & auto-reply</button>
          </form>` : `<p class="muted">Viewers can read conversations but not send test messages.</p>`}
        </section>
      </div>`;

    const paint = () => {
      const list = convs.filter((c) => filter === "all" || c.status === filter);
      el.querySelector("#convs").innerHTML = list.length ? list.map(msgHtml).join("") : `<div class="empty">No conversations yet.</div>`;
    };
    paint();
    el.querySelectorAll("[data-f]").forEach((b) => b.addEventListener("click", () => {
      filter = b.dataset.f;
      el.querySelectorAll("[data-f]").forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
      paint();
    }));
    el.querySelector("#sim")?.addEventListener("submit", async (e) => {
      e.preventDefault();
      const f = e.currentTarget, btn = f.querySelector("button");
      clearToasts();
      btn.disabled = true;
      try {
        const res = await api("/api/conversations/receive", { method: "POST",
          body: { client_name: f.cn.value.trim(), platform: f.pf.value, message_text: f.mt.value.trim(), client_email: f.ce.value.trim() } });
        convs = [{ ...res, last_message_text: res.message_text, last_reply_text: res.reply_text }, ...convs];
        paint();
        const sentTo = f.ce.value.trim();
        f.reset();
        toast(res.status === "escalation" ? "Escalated for your review. Nothing was emailed."
          : res.emailed === "sent" ? `Auto-reply emailed to ${sentTo}.`
          : res.emailed === "simulated" ? "Demo: auto-reply email simulated." : "Auto-reply drafted.");
      } catch (err) { toast(err.message, "error"); } finally { btn.disabled = false; }
    });
  },
};

import { api, esc, icon, toast } from "/assets/shared/api.js";

const FIELDS = [
  ["full_name", "Full name", "text", true], ["professional_title", "Title", "text", true],
  ["email", "Email", "email", true], ["phone", "Phone", "tel", false],
  ["location", "Location", "text", true], ["portfolio_url", "Portfolio URL", "url", false],
  ["github_url", "GitHub URL", "url", false], ["linkedin_url", "LinkedIn URL", "url", false],
  ["calendar_booking_url", "Booking link", "url", false],
];

export default {
  async render(el, ctx) {
    const data = await api("/api/contact");
    const info = data.personal_info || {};
    const rates = data.preferences?.rates || {};
    const editable = ctx.can("profile:write");
    const dis = editable ? "" : "disabled";
    el.innerHTML = `
      <section class="card">
        <div class="card-h"><h2>Candidate dossier</h2>${editable ? "" : `<span class="chip">Admin only to edit</span>`}</div>
        <p class="muted" style="margin:-8px 0 20px;font-size:14px">Agents use this to score roles, write proposals and fill forms.</p>
        <form id="dossier" class="form-grid" novalidate>
          ${FIELDS.map(([k, l, t, req]) => `<div class="field"><label class="label" for="f_${k}">${l}${req ? " *" : ""}</label>
            <input class="input" id="f_${k}" name="${k}" type="${t}" value="${esc(info[k])}" ${req ? "required" : ""} ${dis}></div>`).join("")}
          <div class="field"><label class="label" for="f_rate">Hourly rate (USD)</label><input class="input" id="f_rate" name="preferred_hourly_usd" type="number" min="0" step="1" value="${esc(rates.preferred_hourly_usd ?? 65)}" ${dis}></div>
          <div class="field"><label class="label" for="f_min">Minimum project (USD)</label><input class="input" id="f_min" name="minimum_project_budget_usd" type="number" min="0" step="50" value="${esc(rates.minimum_project_budget_usd ?? 800)}" ${dis}></div>
          ${editable ? `<div class="full row"><button class="btn btn-primary" type="submit">${icon("check")}Save dossier</button><span class="err muted" id="formErr" role="alert"></span></div>` : ""}
        </form>
      </section>`;

    el.querySelector("#dossier").addEventListener("submit", async (e) => {
      e.preventDefault();
      const form = e.currentTarget;
      const errEl = el.querySelector("#formErr");
      const invalid = [...form.elements].filter((i) => i.name && !i.checkValidity());
      form.querySelectorAll("input").forEach((i) => i.setAttribute("aria-invalid", String(invalid.includes(i))));
      if (invalid.length) { errEl.textContent = `Check: ${invalid.map((i) => i.labels[0].textContent.replace(" *", "")).join(", ")}`; invalid[0].focus(); return; }
      errEl.textContent = "";
      const body = Object.fromEntries(FIELDS.map(([k]) => [k, form[k].value.trim()]));
      body.preferred_hourly_usd = Number(form.preferred_hourly_usd.value);
      body.minimum_project_budget_usd = Number(form.minimum_project_budget_usd.value);
      const btn = form.querySelector("button");
      btn.disabled = true;
      try { await api("/api/contact", { method: "POST", body }); toast("Dossier saved. Agents refreshed."); }
      catch (err) { errEl.textContent = err.message; toast(err.message, "error"); }
      finally { btn.disabled = false; }
    });
  },
};

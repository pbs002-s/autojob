import { api, esc, icon, toast } from "/assets/shared/api.js";

const ROLES = ["admin", "operator", "viewer"];

export default {
  async render(el, ctx) {
    const [users, audit] = await Promise.all([api("/api/users"), api("/api/users/audit")]);
    const demo = ctx.session.is_demo;
    el.innerHTML = `
      <section class="card">
        <div class="card-h"><h2>Users & roles</h2>${demo ? `<span class="chip">Read-only in demo</span>` : ""}</div>
        <div class="table-wrap"><table class="table">
          <thead><tr><th class="label">Email</th><th class="label">Role</th><th class="label">Status</th><th></th></tr></thead>
          <tbody>${users.map((u) => `<tr data-id="${u.id}">
            <td class="mono">${esc(u.email)}</td>
            <td><select class="select" style="width:auto;height:32px" data-role aria-label="Role for ${esc(u.email)}" ${demo ? "disabled" : ""}>${ROLES.map((r) => `<option ${r === u.role ? "selected" : ""}>${r}</option>`).join("")}</select></td>
            <td><span class="chip ${u.disabled ? "warn" : "ok"}">${u.disabled ? "disabled" : "active"}</span></td>
            <td style="text-align:right">${demo ? "" : `<button class="btn btn-sm btn-danger" data-toggle="${u.disabled ? 0 : 1}">${u.disabled ? "Enable" : "Disable"}</button>`}</td></tr>`).join("")}</tbody>
        </table></div>
      </section>
      ${demo ? "" : `<section class="card"><div class="card-h"><h2>Invite user</h2></div>
        <form id="newUser" class="form-grid">
          <div class="field"><label class="label" for="nu_e">Email</label><input class="input" id="nu_e" type="email" required></div>
          <div class="field"><label class="label" for="nu_p">Temporary password (min 10)</label><input class="input" id="nu_p" type="password" minlength="10" required autocomplete="new-password"></div>
          <div class="field"><label class="label" for="nu_r">Role</label><select class="select" id="nu_r">${ROLES.map((r) => `<option ${r === "operator" ? "selected" : ""}>${r}</option>`).join("")}</select></div>
          <div class="field" style="align-self:end"><button class="btn btn-primary" type="submit">${icon("users")}Create user</button></div>
        </form></section>`}
      <section class="card"><div class="card-h"><h2>Audit log</h2></div>
        ${audit.length ? `<div class="table-wrap"><table class="table"><tbody>${audit.slice(0, 50).map((a) => `<tr>
          <td class="mono muted" style="white-space:nowrap">${esc(a.created_at.slice(0, 19).replace("T", " "))}</td><td>${esc(a.email || "—")}</td><td class="mono">${esc(a.action)}</td><td class="muted">${esc(a.target)}</td></tr>`).join("")}</tbody></table></div>` : `<div class="empty">No events yet.</div>`}
      </section>`;
    if (demo) return;

    const patch = async (id, body) => {
      try { await api(`/api/users/${id}`, { method: "PATCH", body }); toast("User updated."); }
      catch (err) { toast(err.message, "error"); }
      ctx.navigate("/app/users", false);
    };
    el.querySelectorAll("[data-role]").forEach((s) => s.addEventListener("change", () => patch(s.closest("tr").dataset.id, { role: s.value })));
    el.querySelectorAll("[data-toggle]").forEach((b) => b.addEventListener("click", () => patch(b.closest("tr").dataset.id, { disabled: b.dataset.toggle === "1" })));
    el.querySelector("#newUser").addEventListener("submit", async (e) => {
      e.preventDefault();
      const f = e.currentTarget;
      try {
        await api("/api/users", { method: "POST", body: { email: f.nu_e.value.trim(), password: f.nu_p.value, role: f.nu_r.value } });
        toast("User created.");
        ctx.navigate("/app/users", false);
      } catch (err) { toast(err.message, "error"); }
    });
  },
};

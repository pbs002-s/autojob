import { api, esc, icon } from "/assets/shared/api.js";
import { countUp } from "/assets/shared/motion.js";
import { lineChart, barChart, donutChart, gaugeChart, hbarChart } from "../charts.js";

const card = (id, title, extra = "") => `<section class="card"><div class="card-h"><h2>${title}</h2>${extra}</div><div id="${id}"></div></section>`;

export default {
  async render(el, ctx) {
    const [stats, a] = await Promise.all([api("/api/stats"), api("/api/analytics")]);
    const kpis = [
      ["total_jobs", "Roles tracked"], ["high_matches", "High matches"],
      ["total_applied", "Applications"], ["total_conversations", "Clients held"],
    ];
    el.innerHTML = `
      <section class="card" style="display:flex;flex-wrap:wrap;gap:16px;align-items:center;justify-content:space-between">
        <div><p class="label" style="margin:0 0 6px">Operating as</p>
          <strong style="font-size:22px;letter-spacing:-.02em">${esc(stats.profile.name)}</strong>
          <span class="muted"> · ${esc(stats.profile.title)} · $${esc(stats.profile.hourly_rate)}/hr</span></div>
        <div class="row">
          <a class="btn btn-sm" href="/app/opportunities" data-nav>${icon("briefcase")}Review ${stats.pending_jobs} pending</a>
          <a class="btn btn-sm btn-primary" href="/app/pipeline" data-nav>${icon("pipeline")}Open pipeline</a>
        </div>
      </section>
      <section class="kpis">${kpis.map(([k, l]) => `<div class="kpi"><span class="label">${l}</span><span class="kpi-n ${k === "high_matches" ? "acid" : ""}" data-k="${k}">0</span></div>`).join("")}</section>
      <div class="cols-3">
        ${card("cApps", "Applications per day")}
        ${card("cScore", "Average match score")}
        ${card("cStatus", "Pipeline status")}
      </div>
      <div class="cols-3">
        ${card("cPlat", "Roles per platform")}
        ${card("cBuckets", "Score distribution")}
        ${card("cTags", "Top skills in demand")}
      </div>`;
    el.querySelectorAll("[data-k]").forEach((n) => countUp(n, stats[n.dataset.k] ?? 0, { duration: 0.9 }));
    el.querySelectorAll("[data-nav]").forEach((a) => a.addEventListener("click", (e) => { e.preventDefault(); ctx.navigate(a.getAttribute("href")); }));
    lineChart(el.querySelector("#cApps"), a.applications_per_day, "Applications per day");
    gaugeChart(el.querySelector("#cScore"), a.avg_score, "Average match score");
    donutChart(el.querySelector("#cStatus"), a.status_split, "Jobs by status");
    barChart(el.querySelector("#cPlat"), a.jobs_per_platform, "Jobs per platform");
    barChart(el.querySelector("#cBuckets"), a.score_buckets, "Match score distribution");
    hbarChart(el.querySelector("#cTags"), a.top_tags.slice(0, 7), "Top tags");
  },
};

// Tiny SVG chart renderer: line, bars, donut, gauge, horizontal bars. No chart library.
import { esc } from "/assets/shared/api.js";
import { gsap, reduced } from "/assets/shared/motion.js";

const SERIES = ["#ccff00", "#e4e4e7", "#ff3300", "#71717a", "#a3e635", "#52525b"];
const W = 400, H = 200, PAD = { t: 12, r: 8, b: 24, l: 28 };

const tip = () => document.getElementById("chartTip");
function bindTips(svg) {
  svg.querySelectorAll("[data-tip]").forEach((el) => {
    el.addEventListener("pointermove", (e) => {
      const t = tip();
      t.hidden = false;
      t.textContent = el.dataset.tip;
      t.style.left = `${Math.min(e.clientX + 12, innerWidth - t.offsetWidth - 8)}px`;
      t.style.top = `${e.clientY - 36}px`;
    });
    el.addEventListener("pointerleave", () => { tip().hidden = true; });
  });
}

const animate = (fn) => { if (gsap && !reduced) fn(); };
const empty = (el) => { el.innerHTML = `<div class="empty">No data yet</div>`; };

function frame(el, inner, label) {
  el.innerHTML = `<svg class="chart" viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(label)}">${inner}</svg>`;
  const svg = el.querySelector("svg");
  bindTips(svg);
  return svg;
}

function yAxis(max) {
  const ih = H - PAD.t - PAD.b;
  return [0, 0.5, 1].map((f) => {
    const y = PAD.t + ih * (1 - f);
    return `<line class="grid-l" x1="${PAD.l}" x2="${W - PAD.r}" y1="${y}" y2="${y}"/><text x="${PAD.l - 6}" y="${y + 3}" text-anchor="end">${Math.round(max * f)}</text>`;
  }).join("");
}

export function lineChart(el, data, label) {
  if (!data.length) return empty(el);
  const max = Math.max(1, ...data.map((d) => d.value));
  const iw = W - PAD.l - PAD.r, ih = H - PAD.t - PAD.b;
  const pts = data.map((d, i) => [PAD.l + (data.length === 1 ? iw / 2 : (i / (data.length - 1)) * iw), PAD.t + ih * (1 - d.value / max)]);
  const path = pts.map((p, i) => `${i ? "L" : "M"}${p[0]},${p[1]}`).join("");
  const area = `${path}L${pts.at(-1)[0]},${PAD.t + ih}L${pts[0][0]},${PAD.t + ih}Z`;
  const dots = pts.map((p, i) => `<circle cx="${p[0]}" cy="${p[1]}" r="4" fill="#000" stroke="#ccff00" stroke-width="2" data-tip="${esc(data[i].label)}: ${data[i].value}"/>`).join("");
  const xl = [0, data.length - 1].map((i) => `<text x="${pts[i][0]}" y="${H - 6}" text-anchor="${i ? "end" : "start"}">${esc(String(data[i].label).slice(5))}</text>`).join("");
  const svg = frame(el, `${yAxis(max)}<path d="${area}" fill="rgba(204,255,0,.08)"/><path class="ln" d="${path}" fill="none" stroke="#ccff00" stroke-width="2"/>${dots}${xl}`, label);
  animate(() => {
    const ln = svg.querySelector(".ln"), len = ln.getTotalLength();
    gsap.fromTo(ln, { strokeDasharray: len, strokeDashoffset: len }, { strokeDashoffset: 0, duration: 1.2, ease: "power2.inOut" });
  });
}

export function barChart(el, data, label) {
  if (!data.length) return empty(el);
  const max = Math.max(1, ...data.map((d) => d.value));
  const iw = W - PAD.l - PAD.r, ih = H - PAD.t - PAD.b, bw = iw / data.length;
  const bars = data.map((d, i) => {
    const h = ih * (d.value / max), x = PAD.l + i * bw + bw * 0.15;
    return `<rect class="bar" x="${x}" y="${PAD.t + ih - h}" width="${bw * 0.7}" height="${h}" fill="${i ? "#3f3f46" : "#ccff00"}" data-tip="${esc(d.label)}: ${d.value}"/>
      <text x="${x + bw * 0.35}" y="${H - 6}" text-anchor="middle">${esc(String(d.label).slice(0, 9))}</text>`;
  }).join("");
  const svg = frame(el, yAxis(max) + bars, label);
  animate(() => gsap.from(svg.querySelectorAll(".bar"), { scaleY: 0, transformOrigin: "50% 100%", stagger: 0.05, duration: 0.7 }));
}

export function donutChart(el, data, label) {
  const total = data.reduce((s, d) => s + d.value, 0);
  if (!total) return empty(el);
  const R = 70, C = 2 * Math.PI * R;
  let offset = 0;
  const arcs = data.map((d, i) => {
    const len = (d.value / total) * C;
    const arc = `<circle class="arc" r="${R}" cx="100" cy="100" fill="none" stroke="${SERIES[i % SERIES.length]}" stroke-width="22"
      stroke-dasharray="${len} ${C - len}" stroke-dashoffset="${-offset}" transform="rotate(-90 100 100)" data-tip="${esc(d.label)}: ${d.value}"/>`;
    offset += len;
    return arc;
  }).join("");
  el.innerHTML = `<div class="row" style="gap:20px;flex-wrap:nowrap">
    <svg class="chart" viewBox="0 0 200 200" style="width:160px;height:160px;flex:none" role="img" aria-label="${esc(label)}">${arcs}
      <text x="100" y="98" text-anchor="middle" style="font-size:28px;fill:#e4e4e7">${total}</text><text x="100" y="118" text-anchor="middle">total</text></svg>
    <div class="legend">${data.map((d, i) => `<span><i style="background:${SERIES[i % SERIES.length]}"></i>${esc(d.label)} <b class="mono">${d.value}</b></span>`).join("")}</div></div>`;
  const svg = el.querySelector("svg");
  bindTips(svg);
  animate(() => gsap.from(svg.querySelectorAll(".arc"), { opacity: 0, rotation: -30, transformOrigin: "100px 100px", stagger: 0.08, duration: 0.8 }));
}

export function gaugeChart(el, value, label) {
  const R = 80, half = Math.PI * R, v = Math.max(0, Math.min(100, value));
  el.innerHTML = `<svg class="chart" viewBox="0 0 200 120" role="img" aria-label="${esc(label)}: ${v}%">
    <path d="M20 110 A80 80 0 0 1 180 110" fill="none" stroke="#222" stroke-width="14"/>
    <path class="g" d="M20 110 A80 80 0 0 1 180 110" fill="none" stroke="#ccff00" stroke-width="14" stroke-dasharray="${half}" stroke-dashoffset="${half * (1 - v / 100)}"/>
    <text x="100" y="100" text-anchor="middle" style="font-size:30px;fill:#e4e4e7">${v}%</text></svg>`;
  animate(() => gsap.from(el.querySelector(".g"), { strokeDashoffset: half, duration: 1.2, ease: "power3.out" }));
}

export function hbarChart(el, data, label) {
  if (!data.length) return empty(el);
  const max = Math.max(1, ...data.map((d) => d.value));
  el.innerHTML = `<div class="grid" style="gap:8px" role="img" aria-label="${esc(label)}">${data.map((d) => `
    <div style="display:grid;grid-template-columns:110px 1fr 28px;gap:10px;align-items:center;font-size:13px">
      <span class="muted" style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${esc(d.label)}</span>
      <span style="height:8px;background:#1a1a1a"><i class="hb" style="display:block;height:100%;width:${(d.value / max) * 100}%;background:#ccff00"></i></span>
      <span class="mono">${d.value}</span></div>`).join("")}</div>`;
  animate(() => gsap.from(el.querySelectorAll(".hb"), { scaleX: 0, transformOrigin: "0 50%", stagger: 0.04, duration: 0.6 }));
}

import { gsap, reduced, splitWords, countUp, leave } from "/assets/shared/motion.js";
import { mountThemeToggle } from "/assets/shared/theme.js";

const PHASE_COUNT = 5;

// Fog: a few large soft radial blobs drifting on a canvas. Cheap and GPU friendly.
function initFog() {
  const canvas = document.getElementById("fog");
  const ctx = canvas.getContext("2d");
  const blobs = Array.from({ length: 6 }, (_, i) => ({
    x: Math.random(), y: Math.random(), r: 0.25 + Math.random() * 0.25,
    vx: (Math.random() - 0.5) * 0.0004, vy: (Math.random() - 0.5) * 0.0004, acid: i === 0,
  }));
  const resize = () => { canvas.width = canvas.offsetWidth; canvas.height = canvas.offsetHeight; };
  resize();
  addEventListener("resize", resize);
  const draw = () => {
    const { width: w, height: h } = canvas;
    ctx.clearRect(0, 0, w, h);
    for (const b of blobs) {
      b.x = (b.x + b.vx + 1) % 1; b.y = (b.y + b.vy + 1) % 1;
      const g = ctx.createRadialGradient(b.x * w, b.y * h, 0, b.x * w, b.y * h, b.r * Math.max(w, h));
      g.addColorStop(0, b.acid ? "rgba(204,255,0,0.10)" : "rgba(160,160,170,0.08)");
      g.addColorStop(1, "rgba(0,0,0,0)");
      ctx.fillStyle = g;
      ctx.fillRect(0, 0, w, h);
    }
    if (!reduced) requestAnimationFrame(draw);
  };
  draw();
}

function initCore() {
  const nodes = document.querySelector("#core .nodes");
  nodes.innerHTML = Array.from({ length: PHASE_COUNT }, (_, i) => {
    const a = (i / PHASE_COUNT) * Math.PI * 2 - Math.PI / 2;
    return `<g transform="translate(${Math.cos(a) * 130} ${Math.sin(a) * 130})"><circle r="7" style="fill:var(--void);stroke:var(--acid)"/><text y="-14" text-anchor="middle" style="fill:var(--text-3)" font-family="JetBrains Mono" font-size="10">0${i + 1}</text></g>`;
  }).join("");
  if (!gsap || reduced) return;
  const svg = document.querySelector("#core svg");
  const rx = gsap.quickTo(svg, "rotationX", { duration: 0.8, ease: "power3" });
  const ry = gsap.quickTo(svg, "rotationY", { duration: 0.8, ease: "power3" });
  addEventListener("pointermove", (e) => {
    ry(((e.clientX / innerWidth) - 0.5) * 24);
    rx(((e.clientY / innerHeight) - 0.5) * -24);
  });
  gsap.to("#core .nodes circle", { attr: { r: 9 }, repeat: -1, yoyo: true, stagger: 0.3, duration: 0.9, ease: "sine.inOut" });
}

function initIntro() {
  if (!gsap) return;
  const words = splitWords(document.querySelector(".hero-title"));
  gsap.timeline()
    .from(".nav > *", { y: -16, opacity: 0, stagger: 0.06 })
    .from(words, { yPercent: 110, stagger: 0.04, duration: 1 }, "<0.1")
    .from(".hero-kicker, .hero-sub, .hero-ctas", { y: 20, opacity: 0, stagger: 0.08 }, "<0.3")
    .from("#core", { scale: 0.85, opacity: 0, duration: 1.4 }, "<")
    .from(".float-card", { x: 30, opacity: 0 }, "<0.5");
}

function initPipeline() {
  const phases = [...document.querySelectorAll(".phase")];
  const setActive = (p) => {
    const idx = Math.min(PHASE_COUNT - 1, Math.floor(p * PHASE_COUNT));
    phases.forEach((el, i) => el.classList.toggle("on", i <= idx));
  };
  const desktop = window.matchMedia("(min-width: 901px)").matches;
  if (!gsap || !window.ScrollTrigger || reduced || !desktop) {
    phases.forEach((el) => el.classList.add("on"));
    return;
  }
  gsap.set(".how-fill", { attr: { "stroke-dasharray": 400, "stroke-dashoffset": 400 } });
  gsap.timeline({
    scrollTrigger: { trigger: ".how", start: "top top", end: "+=1600", pin: ".how-pin", scrub: 0.5,
      onUpdate: (st) => setActive(st.progress) },
  }).to(".how-fill", { attr: { "stroke-dashoffset": 0 }, ease: "none" });

  // Section headings reveal word by word as they scroll in.
  gsap.utils.toArray(".cta h2, .feat h3").forEach((h) => {
    gsap.from(splitWords(h), { yPercent: 110, stagger: 0.05, duration: 0.9, scrollTrigger: { trigger: h, start: "top 88%" } });
  });

  gsap.utils.toArray(".feat").forEach((el, i) => {
    gsap.from(el, { y: 40, opacity: 0, delay: (i % 3) * 0.08, scrollTrigger: { trigger: el, start: "top 85%" } });
  });
}

async function initStats() {
  try {
    const res = await fetch("/api/public/stats");
    if (!res.ok) return;
    const data = await res.json();
    document.querySelectorAll(".stat-n").forEach((el) => {
      const run = () => countUp(el, data[el.dataset.key] ?? 0);
      if (window.ScrollTrigger && !reduced) window.ScrollTrigger.create({ trigger: el, start: "top 90%", once: true, onEnter: run });
      else run();
    });
  } catch { /* stats are decorative; leave placeholders */ }
}

async function initSessionCta() {
  try {
    const res = await fetch("/api/auth/session", { credentials: "same-origin" });
    if (!res.ok || !(await res.json()).signed_in) return;
    for (const id of ["navCta", "heroSignin"]) {
      const el = document.getElementById(id);
      el.textContent = "Open console";
      el.href = "/app/overview";
    }
  } catch { /* signed-out state is the default */ }
}

document.querySelectorAll("a[data-leave], #navCta").forEach((a) => a.addEventListener("click", (e) => {
  e.preventDefault();
  leave(a.getAttribute("href"));
}));

document.querySelectorAll("[data-theme-toggle]").forEach(mountThemeToggle);
initFog();
initCore();
initIntro();
initPipeline();
initStats();
initSessionCta();

// GSAP helpers. GSAP is loaded globally from cdnjs before this module.
export const gsap = window.gsap;
export const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

if (gsap) {
  gsap.defaults({ ease: "expo.out", duration: reduced ? 0 : 0.8 });
  if (window.ScrollTrigger) gsap.registerPlugin(window.ScrollTrigger);
  if (window.Flip) gsap.registerPlugin(window.Flip);
}

// Split text into word spans for a staggered reveal (SplitText-lite, keeps a11y via aria-label).
export function splitWords(el) {
  const text = el.textContent.trim();
  el.setAttribute("aria-label", text);
  el.innerHTML = text.split(/\s+/).map((w) =>
    `<span class="w" aria-hidden="true" style="display:inline-block;overflow:hidden;vertical-align:top"><span style="display:inline-block">${w.replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" })[c])}</span></span>`
  ).join(" ");
  return el.querySelectorAll(".w > span");
}

const GLYPHS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789/<>_";

// Decode-style text reveal: characters settle left to right.
export function scramble(el, text, { duration = 0.5 } = {}) {
  if (!gsap || reduced) { el.textContent = text; return; }
  const obj = { p: 0 };
  gsap.killTweensOf(el.__scramble || {});
  el.__scramble = obj;
  gsap.to(obj, { p: 1, duration, ease: "power2.out", onUpdate: () => {
    const settled = Math.floor(obj.p * text.length);
    el.textContent = text.slice(0, settled) + [...text.slice(settled)].map((c) => (c === " " ? " " : GLYPHS[(Math.random() * GLYPHS.length) | 0])).join("");
  }, onComplete: () => { el.textContent = text; } });
}

// Typewriter reveal, capped so long text still finishes in about a second.
export function typeText(el, text, { maxDuration = 1.1 } = {}) {
  if (!gsap || reduced) { if (el.tagName === "TEXTAREA") el.value = text; else el.textContent = text; return; }
  const set = (t) => { if (el.tagName === "TEXTAREA") el.value = t; else el.textContent = t; };
  const obj = { n: 0 };
  el.classList.add("typing");
  gsap.to(obj, { n: text.length, duration: Math.min(maxDuration, text.length / 600), ease: "none",
    onUpdate: () => set(text.slice(0, Math.round(obj.n))),
    onComplete: () => { set(text); el.classList.remove("typing"); } });
}

export function countUp(el, to, { duration = 1.2, decimals = 0, suffix = "" } = {}) {
  if (!gsap || reduced) { el.textContent = Number(to).toFixed(decimals) + suffix; return; }
  const obj = { v: 0 };
  gsap.to(obj, { v: to, duration, ease: "power2.out", onUpdate: () => { el.textContent = obj.v.toFixed(decimals) + suffix; } });
}

// Restore content if the page comes back from the back/forward cache after leave().
addEventListener("pageshow", (e) => { if (e.persisted && gsap) gsap.set("main, header, nav", { clearProps: "opacity,transform" }); });

// Exit animation before navigating to another page.
export function leave(href) {
  if (!gsap || reduced) { location.href = href; return; }
  gsap.to("main, header, nav", { opacity: 0, y: -12, duration: 0.35, ease: "power2.in", onComplete: () => { location.href = href; } });
}

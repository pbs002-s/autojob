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
    `<span class="w" aria-hidden="true" style="display:inline-block;overflow:hidden;vertical-align:top"><span style="display:inline-block">${w}</span></span>`
  ).join(" ");
  return el.querySelectorAll(".w > span");
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

import { api, getSession } from "/assets/shared/api.js";
import { gsap, leave } from "/assets/shared/motion.js";

// Only follow same-site relative paths after login (no open redirect).
function nextUrl() {
  const next = new URLSearchParams(location.search).get("next") || "";
  return /^\/app(\/[\w-]*)?$/.test(next) ? next : "/app/overview";
}

async function init() {
  if (await getSession()) { location.replace(nextUrl()); return; }

  const { demo_enabled } = await api("/api/auth/config").catch(() => ({ demo_enabled: false }));
  document.getElementById("demo").hidden = !demo_enabled;

  if (gsap) {
    gsap.from("main > section", { y: 24, opacity: 0, stagger: 0.12 });
    gsap.from(".demo-card", { x: 24, opacity: 0, stagger: 0.07, delay: 0.25 });
  }
  if (location.hash === "#demo" && demo_enabled) document.querySelector(".demo-card")?.focus();

  const form = document.getElementById("loginForm");
  const err = document.getElementById("loginErr");
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    err.textContent = "";
    const email = form.email.value.trim();
    const password = form.password.value;
    form.email.setAttribute("aria-invalid", String(!email.includes("@")));
    form.password.setAttribute("aria-invalid", String(!password));
    if (!email.includes("@") || !password) { err.textContent = "Enter your email and password."; return; }
    const btn = form.querySelector("button");
    btn.disabled = true;
    try {
      await api("/api/auth/login", { method: "POST", body: { email, password } });
      leave(nextUrl());
    } catch (ex) {
      err.textContent = ex.message;
      gsap?.fromTo(form, { x: -6 }, { x: 0, duration: 0.4, ease: "elastic.out(1, 0.3)" });
    } finally {
      btn.disabled = false;
    }
  });

  document.querySelectorAll(".demo-card").forEach((card) => card.addEventListener("click", async () => {
    try {
      await api("/api/auth/demo", { method: "POST", body: { role: card.dataset.role } });
      leave("/app/overview");
    } catch (ex) {
      err.textContent = ex.message;
    }
  }));
}

init();

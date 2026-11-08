// Light/dark theme: stored choice wins, otherwise follow the OS. Pages set data-theme early in <head>.
import { icon } from "/assets/shared/api.js";

const KEY = "aj-theme";
const root = document.documentElement;
const osLight = window.matchMedia("(prefers-color-scheme: light)");

export const currentTheme = () => root.dataset.theme || (osLight.matches ? "light" : "dark");

function paint(btn) {
  const next = currentTheme() === "light" ? "dark" : "light";
  btn.innerHTML = icon(next === "light" ? "sun" : "moon");
  btn.setAttribute("aria-label", `Switch to ${next} mode`);
  btn.title = `Switch to ${next} mode`;
}

export function mountThemeToggle(btn) {
  paint(btn);
  btn.addEventListener("click", () => {
    const next = currentTheme() === "light" ? "dark" : "light";
    root.dataset.theme = next;
    try { localStorage.setItem(KEY, next); } catch { /* private mode: theme still applies for this page */ }
    paint(btn);
    document.dispatchEvent(new CustomEvent("themechange", { detail: next }));
  });
  osLight.addEventListener("change", () => paint(btn));
}

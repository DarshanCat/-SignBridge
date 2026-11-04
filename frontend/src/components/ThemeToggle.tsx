"use client";
import { Moon, Sun } from "lucide-react";
import { useSyncExternalStore } from "react";

export type Theme = "light" | "dark";
const KEY = "sb-theme";
const EVENT = "sb-theme-change";

function systemTheme(): Theme {
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

/** The theme in effect: the visitor's choice (data-theme) or else the system setting. */
export function currentTheme(): Theme {
  const a = document.documentElement.getAttribute("data-theme");
  return a === "light" || a === "dark" ? a : systemTheme();
}

function subscribe(cb: () => void): () => void {
  const mq = window.matchMedia("(prefers-color-scheme: dark)");
  window.addEventListener(EVENT, cb);
  mq.addEventListener("change", cb);
  return () => {
    window.removeEventListener(EVENT, cb);
    mq.removeEventListener("change", cb);
  };
}

function setTheme(t: Theme): void {
  document.documentElement.setAttribute("data-theme", t);
  try {
    localStorage.setItem(KEY, t); // a per-visitor convenience only; the page works without it
  } catch {
    /* private window or blocked storage */
  }
  window.dispatchEvent(new Event(EVENT));
}

/** Subscribe to the theme in effect (the 3D stage reads its colours from CSS variables and needs to know when they change). */
export function useTheme(): Theme {
  return useSyncExternalStore(subscribe, currentTheme, () => "light" as Theme);
}

/** Script text that applies a saved theme before the first paint (no flash of the wrong theme). */
export const THEME_INIT_SCRIPT = `(function(){try{var t=localStorage.getItem("${KEY}");if(t==="light"||t==="dark")document.documentElement.setAttribute("data-theme",t)}catch(e){}})()`;

export function ThemeToggle() {
  const theme = useTheme();
  const next: Theme = theme === "dark" ? "light" : "dark";
  return (
    <button type="button" onClick={() => setTheme(next)} className="btn h-12 w-12 !min-h-12 !p-0" aria-label={`Switch to ${next} mode`} title={`Switch to ${next} mode`}>
      {theme === "dark" ? <Sun size={20} aria-hidden /> : <Moon size={20} aria-hidden />}
    </button>
  );
}

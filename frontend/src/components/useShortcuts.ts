"use client";
import { useEffect, useRef } from "react";
import { actionForKey, type ShortcutAction } from "@/lib/shortcuts";

/** Runs the handler of a pressed shortcut key. Only the handlers given here react; other keys are left alone. */
export function useShortcuts(handlers: Partial<Record<ShortcutAction, () => void>>): void {
  const ref = useRef(handlers);
  useEffect(() => {
    ref.current = handlers;
  });
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.defaultPrevented || e.repeat) return;
      const t = e.target as HTMLElement | null;
      const action = actionForKey({ key: e.key, ctrlKey: e.ctrlKey, altKey: e.altKey, metaKey: e.metaKey, targetTag: t?.tagName, editable: t?.isContentEditable });
      const run = action ? ref.current[action] : undefined;
      if (run) {
        e.preventDefault();
        run();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);
}

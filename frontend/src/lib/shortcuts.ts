export type ShortcutAction = "record" | "play" | "replay" | "undo" | "clear" | "send";

/** Single key shortcuts. They never fire while typing in a field or together with Ctrl, Alt or Meta (browser shortcuts stay untouched). */
export const SHORTCUTS: { key: string; action: ShortcutAction; label: string }[] = [
  { key: "r", action: "record", label: "R record" },
  { key: "p", action: "play", label: "P play or pause" },
  { key: "a", action: "replay", label: "A replay (again)" },
  { key: "u", action: "undo", label: "U undo last sign" },
  { key: "c", action: "clear", label: "C clear" },
  { key: "s", action: "send", label: "S send the signed sentence" },
];

export interface KeyInfo {
  key: string;
  ctrlKey?: boolean;
  altKey?: boolean;
  metaKey?: boolean;
  /** tagName of the focused element, if any. */
  targetTag?: string;
  /** True for contenteditable elements. */
  editable?: boolean;
}

const TYPING_TAGS = new Set(["INPUT", "TEXTAREA", "SELECT"]);

export function actionForKey(e: KeyInfo): ShortcutAction | null {
  if (e.ctrlKey || e.altKey || e.metaKey) return null;
  if (e.editable || (e.targetTag && TYPING_TAGS.has(e.targetTag.toUpperCase()))) return null;
  const hit = SHORTCUTS.find((s) => s.key === e.key.toLowerCase());
  return hit ? hit.action : null;
}

export const shortcutHelp = (actions: ShortcutAction[]): string =>
  SHORTCUTS.filter((s) => actions.includes(s.action)).map((s) => s.label).join(", ");

import type { TokenView } from "./avatar/sentence";

export type Speaker = "signer" | "typist";

export interface ChatMessage {
  id: number;
  from: Speaker;
  text: string;
  /** Glosses: recognized from the signing (signer) or produced by text to gloss (typist). */
  gloss: string[];
  /** Typist messages only: glosses that have no clip and were therefore not signed. */
  notSigned: string[];
  /** Typist messages only: how many clips the avatar plays for this message. */
  clipCount: number;
  at: number;
}

export const MAX_MESSAGES = 200;
export const MAX_TYPED_LENGTH = 500; // the text to gloss endpoint accepts 1 to 500 characters

export function appendMessage(log: ChatMessage[], m: ChatMessage): ChatMessage[] {
  const next = [...log, m];
  return next.length > MAX_MESSAGES ? next.slice(next.length - MAX_MESSAGES) : next;
}

/** A message from the deaf user: the sentence built from the recognized signs. Empty sentences cannot be sent. */
export function signedMessage(id: number, english: string, gloss: string[], at: number): ChatMessage | null {
  const text = english.trim();
  if (!text || gloss.length === 0) return null;
  return { id, from: "signer", text, gloss: [...gloss], notSigned: [], clipCount: 0, at };
}

/** A message from the hearing user. `views` says which glosses the avatar can sign; the others are listed, never faked. */
export function typedMessage(id: number, text: string, gloss: string[], views: TokenView[], clipCount: number, at: number): ChatMessage | null {
  const t = text.trim();
  if (!t) return null;
  return { id, from: "typist", text: t, gloss: [...gloss], notSigned: views.filter((v) => v.status === "no_clip").map((v) => v.gloss), clipCount, at };
}

/** One line under a typed message that says how much of it the avatar could sign. */
export function signingSummary(m: ChatMessage): string {
  if (m.from !== "typist") return "";
  if (m.gloss.length === 0) return "No signable words found.";
  const total = m.gloss.length;
  if (m.notSigned.length === 0) return `Signed all ${total} sign${total === 1 ? "" : "s"}.`;
  return `Signed ${total - m.notSigned.length} of ${total}. No clip for: ${m.notSigned.join(", ")}.`;
}

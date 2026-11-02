import { isValidGloss, normalizeGloss } from "./recorder";

export const DEFAULT_TAKES = 8;
export const MIN_TAKES = 1;
export const MAX_TAKES = 50;
export const SIGNER_PATTERN = /^[A-Za-z0-9][A-Za-z0-9_-]{0,31}$/;

export interface SessionConfig {
  signerId: string;
  glosses: string[];
  takesPerGloss: number;
}

export interface SessionState {
  config: SessionConfig;
  index: number;
  /** Saved takes per gloss: takes found on disk when the session started plus the ones saved since. Rejected takes never count. */
  accepted: Record<string, number>;
  /** Attempts made in this session, rejected ones included. */
  attempts: Record<string, number>;
  done: boolean;
}

export const normalizeSigner = (raw: string): string => raw.trim().toUpperCase();
export const isValidSigner = (raw: string): boolean => SIGNER_PATTERN.test(raw.trim());

/** Split free text (commas, spaces, new lines) into normalized glosses without duplicates; invalid names are returned separately. */
export function parseGlossList(text: string): { glosses: string[]; invalid: string[] } {
  const seen = new Set<string>();
  const glosses: string[] = [];
  const invalid: string[] = [];
  for (const raw of text.split(/[\s,;]+/).filter(Boolean)) {
    const g = normalizeGloss(raw);
    if (!isValidGloss(raw)) {
      if (!invalid.includes(raw)) invalid.push(raw);
    } else if (!seen.has(g)) {
      seen.add(g);
      glosses.push(g);
    }
  }
  return { glosses, invalid };
}

export function validateConfig(c: SessionConfig): string[] {
  const errors: string[] = [];
  if (!isValidSigner(c.signerId)) errors.push("Signer ID: 1 to 32 letters, digits, hyphens or underscores (for example P01).");
  if (c.glosses.length === 0) errors.push("Add at least one gloss.");
  if (!Number.isInteger(c.takesPerGloss) || c.takesPerGloss < MIN_TAKES || c.takesPerGloss > MAX_TAKES) {
    errors.push(`Takes per sign: a whole number from ${MIN_TAKES} to ${MAX_TAKES}.`);
  }
  return errors;
}

const target = (s: SessionState) => s.config.takesPerGloss;
const have = (s: SessionState, g: string) => s.accepted[g] ?? 0;
const unfinished = (s: SessionState, i: number) => have(s, s.config.glosses[i]) < target(s);

/** First unfinished gloss at or after `from`, wrapping around; -1 when every gloss has enough takes. */
function nextUnfinished(s: SessionState, from: number): number {
  const n = s.config.glosses.length;
  for (let k = 0; k < n; k++) {
    const i = (from + k) % n;
    if (unfinished(s, i)) return i;
  }
  return -1;
}

/** Start (or resume): `existing` are the takes already saved for this signer, so a stopped session continues where it ended. */
export function startSession(config: SessionConfig, existing: Record<string, number> = {}): SessionState {
  const accepted: Record<string, number> = {};
  for (const g of config.glosses) accepted[g] = existing[g] ?? 0;
  const s: SessionState = { config: { ...config, signerId: normalizeSigner(config.signerId) }, index: 0, accepted, attempts: {}, done: false };
  const i = nextUnfinished(s, 0);
  return i < 0 ? { ...s, done: true } : { ...s, index: i };
}

export const currentGloss = (s: SessionState): string | null => (s.done ? null : (s.config.glosses[s.index] ?? null));

/** Result of one take. An accepted take counts; when the gloss has enough takes the session moves on, and ends when every gloss is complete. */
export function applyTake(s: SessionState, accepted: boolean): SessionState {
  const g = currentGloss(s);
  if (!g) return s;
  const next: SessionState = {
    ...s,
    attempts: { ...s.attempts, [g]: (s.attempts[g] ?? 0) + 1 },
    accepted: accepted ? { ...s.accepted, [g]: have(s, g) + 1 } : s.accepted,
  };
  if (!unfinished(next, s.index)) {
    const i = nextUnfinished(next, s.index + 1);
    return i < 0 ? { ...next, done: true } : { ...next, index: i };
  }
  return next;
}

/** Skip the current gloss for now; it stays unfinished and comes back after the others. */
export function skipGloss(s: SessionState): SessionState {
  if (s.done) return s;
  const i = nextUnfinished(s, s.index + 1);
  return i < 0 ? s : { ...s, index: i };
}

/** Go back to the previous gloss (even a finished one) to record more takes of it. */
export function previousGloss(s: SessionState): SessionState {
  const n = s.config.glosses.length;
  if (n === 0) return s;
  return { ...s, done: false, index: (s.index - 1 + n) % n };
}

export interface Progress {
  takes: number;
  targetTakes: number;
  glossesDone: number;
  glossesTotal: number;
}

export function progress(s: SessionState): Progress {
  const t = target(s);
  const gl = s.config.glosses;
  return {
    takes: gl.reduce((a, g) => a + Math.min(have(s, g), t), 0),
    targetTakes: gl.length * t,
    glossesDone: gl.filter((g) => have(s, g) >= t).length,
    glossesTotal: gl.length,
  };
}

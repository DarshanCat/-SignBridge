import type { PlanStep } from "../api";

export interface GlossTokenIn {
  gloss: string;
  kind: string; // "sign" or "fingerspell"
  letters?: string[] | null;
}

export type TokenStatus = "clip" | "fingerspelled" | "no_clip";

export interface TokenView {
  gloss: string;
  status: TokenStatus;
  /** Glosses whose clips are played for this token (the sign itself, or one clip per letter). Empty for no_clip. */
  play: string[];
  /** Plain text for the UI, for example "no clip for WHERE". */
  label: string;
}

/** Clip gloss used for one fingerspelled letter. A letter is only usable if a clip with this gloss exists. */
export const letterGloss = (letter: string): string => `FS-${letter.toUpperCase()}`;

/** Every gloss the backend plan must be asked about: each sign, and the letter glosses of each fingerspelled word. */
export function glossesToPlan(tokens: GlossTokenIn[]): string[] {
  const out = new Set<string>();
  for (const t of tokens) {
    if (t.kind === "fingerspell") (t.letters ?? []).forEach((l) => out.add(letterGloss(l)));
    else out.add(t.gloss);
  }
  return [...out];
}

/**
 * Decide, per token, whether it can be shown. `available` are the glosses that have a clip that loaded and validated.
 * A fingerspelled word is played only if EVERY letter has a clip; otherwise the whole word is reported as having no clip.
 * Nothing is ever substituted or invented.
 */
export function describeTokens(tokens: GlossTokenIn[], available: ReadonlySet<string>): TokenView[] {
  return tokens.map((t) => {
    if (t.kind === "fingerspell") {
      const letters = (t.letters ?? []).map(letterGloss);
      if (letters.length > 0 && letters.every((l) => available.has(l))) {
        return { gloss: t.gloss, status: "fingerspelled", play: letters, label: `${t.gloss} (fingerspelled)` };
      }
      return { gloss: t.gloss, status: "no_clip", play: [], label: `no clip for ${t.gloss} (no fingerspelling clips)` };
    }
    if (available.has(t.gloss)) return { gloss: t.gloss, status: "clip", play: [t.gloss], label: t.gloss };
    return { gloss: t.gloss, status: "no_clip", play: [], label: `no clip for ${t.gloss}` };
  });
}

/** Glosses to play, in sentence order. A gloss used twice is played twice. */
export function playOrder(views: TokenView[]): string[] {
  return views.flatMap((v) => v.play);
}

/** Plan steps (clip URLs) needed for the sentence, keeping order and repeats. */
export function playableSteps(views: TokenView[], steps: PlanStep[]): PlanStep[] {
  const byGloss = new Map(steps.map((s) => [s.gloss, s]));
  return playOrder(views).flatMap((g) => {
    const s = byGloss.get(g);
    return s ? [s] : [];
  });
}

export const CLARITY_LABELS: Record<number, string> = {
  1: "Not clear at all",
  2: "Hard to follow",
  3: "Understandable",
  4: "Clear",
  5: "Very clear",
};
export const MAX_COMMENT = 500;
export const REVIEWER_PATTERN = /^[A-Za-z0-9][A-Za-z0-9_-]{0,31}$/;

export type Verdict = "correct" | "wrong";

export interface ReviewRecord {
  reviewer_id: string;
  gloss: string;
  clarity: number;
  verdict: Verdict;
  comment: string;
  reviewed_at_utc: string;
  clip_sha256: string | null;
}
export interface MineResponse {
  reviewer_id: string;
  reviews: ReviewRecord[];
  total_clips: number;
  reviewed: number;
}

export const isValidReviewer = (raw: string): boolean => REVIEWER_PATTERN.test(raw.trim());

export interface ReviewForm {
  reviewerId: string;
  gloss: string | null;
  clarity: number | null;
  verdict: Verdict | null;
  comment: string;
}

/** Messages for what is still missing; an empty list means the review can be saved. */
export function validateReview(f: ReviewForm): string[] {
  const out: string[] = [];
  if (!isValidReviewer(f.reviewerId)) out.push("Enter your reviewer ID (letters and digits, for example R01; not your name).");
  if (!f.gloss) out.push("Choose a sign to review.");
  if (f.clarity === null || !Number.isInteger(f.clarity) || f.clarity < 1 || f.clarity > 5) out.push("Rate the clarity from 1 to 5.");
  if (f.verdict !== "correct" && f.verdict !== "wrong") out.push("Mark the sign as correct or wrong.");
  if (f.comment.trim().length > MAX_COMMENT) out.push(`A comment is at most ${MAX_COMMENT} characters.`);
  return out;
}

export interface ClipRow {
  gloss: string;
  reviewed: ReviewRecord | null;
}

/** Search by gloss (hyphens and spaces count the same) and optionally only the signs this reviewer has not reviewed yet. */
export function filterClips(glosses: string[], mine: ReviewRecord[], query: string, onlyUnreviewed: boolean): ClipRow[] {
  const by = new Map(mine.map((r) => [r.gloss, r]));
  const q = query.trim().toLowerCase().replace(/[-\s]+/g, " ");
  return [...glosses]
    .sort()
    .filter((g) => !q || g.toLowerCase().replace(/[-\s]+/g, " ").includes(q))
    .map((g) => ({ gloss: g, reviewed: by.get(g) ?? null }))
    .filter((r) => !onlyUnreviewed || !r.reviewed);
}

/** The next sign after `gloss` that this reviewer has not reviewed (wrapping around), or null when everything is reviewed. */
export function nextUnreviewed(glosses: string[], mine: ReviewRecord[], gloss: string | null): string | null {
  const done = new Set(mine.map((r) => r.gloss));
  const sorted = [...glosses].sort();
  const start = gloss ? sorted.indexOf(gloss) + 1 : 0;
  for (let i = 0; i < sorted.length; i++) {
    const g = sorted[(start + i) % sorted.length];
    if (!done.has(g) && g !== gloss) return g;
  }
  return null;
}

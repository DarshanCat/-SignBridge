import type { ClipLandmarks, SignClip } from "./clip";
import { sourceFrame, SIDES, type Side } from "./sourceLandmarks";

/** Seconds (of clip time) that the key handshape of a sign is held at its peak. */
export const HOLD_S = 0.28;

const cache = new WeakMap<SignClip, number | null>();

/**
 * The moment of a sign to hold: the stroke's end, found from the source as the slowest moment of the hand in the middle of the sign, after it
 * has moved. Returns the clip time of that source frame, or null for a clip with no landmarks, too few frames or no movement to speak of.
 * Nothing is invented: the hold repeats the pose the clip already has at that time.
 */
export function peakTime(clip: SignClip): number | null {
  const lm = clip.landmarks;
  if (!lm) return null;
  if (cache.has(clip)) return cache.get(clip) ?? null;
  const t = findPeak(lm);
  cache.set(clip, t);
  return t;
}

function findPeak(lm: ClipLandmarks): number | null {
  const n = lm.t.length;
  if (n < 8) return null;
  const frames = lm.t.map((_, i) => sourceFrame(lm, i));
  // speed of the faster hand (central difference), only where the hand was detected
  const speed: number[] = [];
  for (let i = 0; i < n; i++) {
    const a = frames[Math.max(0, i - 1)];
    const b = frames[Math.min(n - 1, i + 1)];
    const dt = lm.t[Math.min(n - 1, i + 1)] - lm.t[Math.max(0, i - 1)] || 1;
    let best = 0;
    for (const s of SIDES as readonly Side[]) {
      if (!a.hand[s] || !b.hand[s]) continue;
      best = Math.max(best, a.wrist[s].distanceTo(b.wrist[s]) / dt);
    }
    speed.push(best);
  }
  const max = Math.max(...speed);
  if (max < 0.25) return null; // the hands hardly move: nothing to hold
  const lo = Math.floor(0.2 * n);
  const hi = Math.ceil(0.9 * n);
  let k = -1;
  for (let i = Math.max(1, lo); i < Math.min(n - 1, hi); i++) {
    const slow = speed[i] <= speed[i - 1] && speed[i] <= speed[i + 1] && speed[i] < 0.45 * max && speed[i] > 0;
    // and the hand is up: at least one hand is above the waist line of the shoulders' scale
    const up = SIDES.some((s) => frames[i].hand[s] && frames[i].wrist[s].y > -1.6);
    if (slow && up && (k < 0 || speed[i] <= speed[k])) k = i;
  }
  return k < 0 ? null : lm.t[k];
}

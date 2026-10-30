import type { Euler3, Pose } from "./clip";

/**
 * Rule-based approximation of ISL non-manual markers on the head bone only (no face is tracked or animated).
 * Amplitudes are small on purpose and are NOT taken from signer-validated data.
 *   negation:           head shake (yaw about the vertical axis)
 *   yes-no-question:    slight forward head tilt (pitch)
 *   wh-question:        slight sideways head tilt (roll)
 */
export const NMM_PARAMS = {
  shakeAmp: 0.22, // rad
  shakeHz: 2.5,
  yesNoPitch: 0.12, // rad, forward
  whRoll: 0.12, // rad
  rampS: 0.3, // seconds to ease in at the start and out at the end of the sentence
} as const;

export const NMM_TAGS = ["negation", "yes-no-question", "wh-question"] as const;

const smooth = (x: number): number => {
  const c = Math.min(1, Math.max(0, x));
  return c * c * (3 - 2 * c);
};

/** Easing factor 0..1 for time t inside a sentence of the given total duration. */
export function nmmEnvelope(t: number, total: number): number {
  return smooth(t / NMM_PARAMS.rampS) * smooth((total - t) / NMM_PARAMS.rampS);
}

/** Head rotation offset (x pitch, y yaw, z roll; rad) for the given tags at time t of a sentence lasting total seconds. */
export function nmmHeadOffset(tags: readonly string[], t: number, total: number): Euler3 {
  const e = nmmEnvelope(t, total);
  let x = 0;
  let y = 0;
  let z = 0;
  if (tags.includes("negation")) y += NMM_PARAMS.shakeAmp * Math.sin(2 * Math.PI * NMM_PARAMS.shakeHz * t);
  if (tags.includes("yes-no-question")) x += NMM_PARAMS.yesNoPitch;
  if (tags.includes("wh-question")) z += NMM_PARAMS.whRoll;
  return [x * e, y * e, z * e];
}

/** Add the head offset to a pose without touching the other bones. */
export function withNmm(pose: Pose, tags: readonly string[], t: number, total: number): Pose {
  if (!tags.some((g) => (NMM_TAGS as readonly string[]).includes(g))) return pose;
  const [dx, dy, dz] = nmmHeadOffset(tags, t, total);
  const h = pose.head ?? [0, 0, 0];
  return { ...pose, head: [h[0] + dx, h[1] + dy, h[2] + dz] };
}

import { sampleClip, type Euler3, type Pose, type SignClip } from "./clip";
import { FINGER_SPLIT } from "./mixamo";
import { SignRetargeter, type Solved } from "./retarget";
import { FINGERS, SIDES, sourceFrameAtTime } from "./sourceLandmarks";

const smooth = (x: number) => {
  const c = Math.min(1, Math.max(0, x));
  return c * c * (3 - 2 * c);
};

/** 0 at the rest ends of a clip (its first and last keyframes are rest ramps) and 1 for the body of the sign, where the source frames are. */
export function bodyWeight(clip: SignClip, t: number): number {
  const lm = clip.landmarks;
  if (!lm) return 0;
  const t0 = lm.t[0];
  const tl = lm.t[lm.t.length - 1];
  if (t < t0) return smooth(t / (t0 || 1));
  if (t > tl) return 1 - smooth((t - tl) / (clip.duration - tl || 1));
  return 1;
}

/**
 * The clip's pose at time t, with the retargeted arms, hands and fingers in place of the clip's own where the source has them. During the rest
 * ramps at both ends the two are cross-faded, so a sign still rises from and settles back to the relaxed pose exactly as before.
 */
export function makeSampler(rt: SignRetargeter): (clip: SignClip, t: number) => Pose {
  return (clip, t) => {
    const legacy = sampleClip(clip, t);
    const lm = clip.landmarks;
    const w = lm ? bodyWeight(clip, t) : 0;
    if (!lm || w <= 0.001) return legacy;
    const solved = rt.solve(sourceFrameAtTime(lm, t));
    return blendSolved(legacy, solved, w);
  };
}

const mix = (a: Euler3, b: Euler3, f: number): Euler3 => [a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f, a[2] + (b[2] - a[2]) * f];

/** Replace the clip's bones by the solved ones, cross-faded with weight w (1 = solved). Fingers of a solved hand are expressed per joint on both sides of the fade. */
export function blendSolved(legacy: Pose, solved: Solved, w: number): Pose {
  const out: Pose = { ...legacy };
  for (const s of SIDES) {
    if (!solved.hand[s]) continue;
    for (const f of FINGERS) {
      const key = `hand_${s}.${f}`;
      const curl = out[key] ?? [0, 0, 0];
      delete out[key];
      FINGER_SPLIT[f[0].toUpperCase() + f.slice(1)].forEach((frac, k) => {
        out[`${key}#${k + 1}`] = [curl[0] * frac, 0, 0];
      });
    }
  }
  for (const [bone, e] of Object.entries(solved.pose)) out[bone] = mix(out[bone] ?? [0, 0, 0], e, w);
  return out;
}


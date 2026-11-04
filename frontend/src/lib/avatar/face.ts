import { nmmEnvelope } from "./nmm";

/**
 * Face of the VRM avatar: natural blinking, a neutral face while signing, and the existing non-manual markers shown as VRM expressions in
 * addition to the head movements of nmm.ts.
 *
 * These are RULE-BASED APPROXIMATIONS, not taken from signer-validated data and not tracked from a person. A VRM has no eyebrow preset, so the
 * closest presets are used: `surprised` (raised brows, wider eyes) for yes-no questions and `sad` (brows drawn down and in, mouth corners
 * down) for negation, both at low weight. Wh-questions keep only the head tilt.
 */
export const FACE = {
  blinkGapS: [2.6, 6.0] as const, // seconds between blinks (random in this range, seeded)
  blinkCloseS: 0.07,
  blinkHoldS: 0.04,
  blinkOpenS: 0.12,
  doubleBlinkChance: 0.12,
  yesNoSurprised: 0.4, // weight of the `surprised` preset at full marker strength
  negationFrown: 0.45, // weight of the `sad` preset
  easeTauS: 0.1, // expression smoothing time constant
} as const;

/** Expression presets that the rule-based markers drive. */
export type FaceTargets = { surprised: number; sad: number };

export interface NmmState {
  tags: readonly string[];
  t: number; // playing time since the sentence started
  total: number; // sentence duration
}

export const NO_FACE: FaceTargets = { surprised: 0, sad: 0 };

/** Target expression weights for the markers of the current sentence (all zero when nothing is playing). */
export function nmmFaceTargets(state: NmmState | null): FaceTargets {
  if (!state || state.total <= 0) return { ...NO_FACE };
  const e = nmmEnvelope(state.t, state.total);
  return {
    surprised: state.tags.includes("yes-no-question") ? FACE.yesNoSurprised * e : 0,
    sad: state.tags.includes("negation") ? FACE.negationFrown * e : 0,
  };
}

const smooth01 = (x: number): number => {
  const c = Math.min(1, Math.max(0, x));
  return c * c * (3 - 2 * c);
};

/** Blink weight (0 open, 1 closed) over time; deterministic for a given seed. Call step(dt) once per frame. */
export class Blinker {
  private rng: number;
  private untilNext: number;
  private phase = -1; // seconds since this blink started, -1 when not blinking
  private pending = false; // a second blink of a double blink follows

  constructor(seed = 12345) {
    this.rng = seed >>> 0 || 1;
    this.untilNext = this.gap();
  }

  private rand(): number {
    // xorshift32: small, deterministic, good enough for timing
    let x = this.rng;
    x ^= x << 13;
    x >>>= 0;
    x ^= x >>> 17;
    x ^= x << 5;
    x >>>= 0;
    this.rng = x || 1;
    return this.rng / 4294967296;
  }

  private gap(): number {
    const [lo, hi] = FACE.blinkGapS;
    return lo + (hi - lo) * this.rand();
  }

  step(dt: number): number {
    if (this.phase < 0) {
      this.untilNext -= dt;
      if (this.untilNext > 0) return 0;
      this.phase = 0;
      this.pending = this.rand() < FACE.doubleBlinkChance;
    } else {
      this.phase += dt;
    }
    const { blinkCloseS: c, blinkHoldS: h, blinkOpenS: o } = FACE;
    const p = this.phase;
    if (p < c) return smooth01(p / c);
    if (p < c + h) return 1;
    if (p < c + h + o) return 1 - smooth01((p - c - h) / o);
    this.phase = -1;
    this.untilNext = this.pending ? 0.14 : this.gap();
    this.pending = false;
    return 0;
  }
}

/** Frame-rate independent easing of expression weights so the face never snaps. */
export class ExpressionSmoother {
  private cur: FaceTargets = { ...NO_FACE };

  step(target: FaceTargets, dt: number): FaceTargets {
    const a = dt <= 0 ? 1 : 1 - Math.exp(-dt / FACE.easeTauS);
    this.cur = { surprised: this.cur.surprised + (target.surprised - this.cur.surprised) * a, sad: this.cur.sad + (target.sad - this.cur.sad) * a };
    return { ...this.cur };
  }
}

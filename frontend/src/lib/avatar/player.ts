import { slerpEuler, smoothstep } from "./idle";
import { withNmm } from "./nmm";
import { sampleClip, type Euler3, type Pose, type SignClip } from "./clip";
import { HOLD_S, peakTime } from "./peak";

/** Seconds over which the avatar blends from the end of one sign into the start of the next. */
export const TRANSITION_S = 0.25;

/** Signs play slower than the source by default: clear handshapes matter more than speed. The speed control stays. */
export const DEFAULT_SIGN_RATE = 0.75;

/** Blend two poses: body bones are slerped as quaternions (no shortcut through a wrong angle), finger curls (names with a dot) lerped. */
export function blendPoses(a: Pose, b: Pose, f: number): Pose {
  const out: Pose = {};
  for (const bone of new Set([...Object.keys(a), ...Object.keys(b)])) {
    const x = a[bone] ?? [0, 0, 0];
    const y = b[bone] ?? [0, 0, 0];
    out[bone] = bone.includes(".") ? ([0, 1, 2].map((i) => x[i] + (y[i] - x[i]) * f) as Euler3) : slerpEuler(x, y, f);
  }
  return out;
}

export type PlayerStatus = "idle" | "playing" | "paused" | "finished";

export interface PlayerSnapshot {
  status: PlayerStatus;
  index: number;
  total: number;
  gloss: string | null;
}

/** Plays a list of sign clips back to back. Time advances only through tick(), so it is deterministic and testable. */
export class SequencePlayer {
  private playlist: SignClip[] = [];
  private status: PlayerStatus = "idle";
  private index = 0;
  private time = 0;
  private fromPose: Pose | null = null; // end pose of the previous sign while blending into the next
  private blend = 0;
  private listeners = new Set<() => void>();
  private snap: PlayerSnapshot = { status: "idle", index: 0, total: 0, gloss: null };
  private rate = 1;
  private sampler: (clip: SignClip, t: number) => Pose = sampleClip;
  private holdLeft = 0; // clip time still to be held at the peak of the current sign
  private holdDone = false; // the hold of the current sign has happened
  private nmm: string[] = [];
  private elapsed = 0; // playing time since the sentence started (for the head markers)

  setRate(rate: number): void {
    this.rate = rate;
  }

  /** Replace how a clip is turned into a pose (the avatar plugs in its retargeter here); null restores the clip's own tracks. */
  setSampler(fn: ((clip: SignClip, t: number) => Pose) | null): void {
    this.sampler = fn ?? sampleClip;
  }

  /** The sign being played and the time inside it, or null when nothing is playing or paused. */
  current(): { clip: SignClip; time: number; index: number } | null {
    if ((this.status !== "playing" && this.status !== "paused") || !this.playlist.length) return null;
    return { clip: this.playlist[this.index], time: this.time, index: this.index };
  }

  /**
   * "sign" while the body of a sign plays (between its first and last source frame, not blending), "transition" for the rise from rest, the blend
   * between signs and the settling, "rest" otherwise. The avatar smooths less in the body of a sign and more in a transition.
   */
  phase(): "sign" | "transition" | "rest" {
    const c = this.current();
    if (!c) return "rest";
    const lm = c.clip.landmarks;
    if (this.fromPose || !lm) return "transition";
    return c.time >= lm.t[0] && c.time <= lm.t[lm.t.length - 1] ? "sign" : "transition";
  }

  /** Jump to a time inside a sign and stay there (paused). For stepping through a sign and for checks; the hold is skipped. */
  seek(index: number, time: number): void {
    if (!this.playlist.length) return;
    this.index = Math.min(Math.max(0, index), this.playlist.length - 1);
    this.time = Math.min(Math.max(0, time), this.playlist[this.index].duration);
    this.fromPose = null;
    this.holdLeft = 0;
    this.holdDone = true;
    this.elapsed = this.playlist.slice(0, this.index).reduce((a, c) => a + c.duration, 0) + this.time;
    this.set("paused");
  }

  private totalSeconds(): number {
    return this.playlist.reduce((a, c) => a + c.duration + (peakTime(c) === null ? 0 : HOLD_S), 0);
  }

  /** Non-manual marker tags for the loaded sentence (negation, yes-no-question, wh-question): rule-based head motion. */
  setNmm(tags: string[]): void {
    this.nmm = tags;
  }

  load(clips: SignClip[]): void {
    this.playlist = clips;
    this.nmm = [];
    this.elapsed = 0;
    this.index = 0;
    this.time = 0;
    this.fromPose = null;
    this.holdLeft = 0;
    this.holdDone = false;
    this.status = "idle";
    this.emit();
  }

  play(): void {
    if (!this.playlist.length) return;
    if (this.status === "finished") this.restart();
    else this.set("playing");
  }

  pause(): void {
    if (this.status === "playing") this.set("paused");
  }

  /** Halt and rewind to the first sign; the playlist stays loaded. */
  stop(): void {
    this.elapsed = 0;
    this.index = 0;
    this.time = 0;
    this.fromPose = null;
    this.holdLeft = 0;
    this.holdDone = false;
    this.set("idle");
  }

  /** Unload everything (same as loading an empty playlist). */
  reset(): void {
    this.load([]);
  }

  /** Release the playlist and subscribers; the player must not be used afterwards. */
  dispose(): void {
    this.listeners.clear();
    this.playlist = [];
    this.fromPose = null;
  }

  /** Start the current sign again from its beginning. */
  replay(): void {
    if (!this.playlist.length) return;
    this.time = 0;
    this.fromPose = null;
    this.holdLeft = 0;
    this.holdDone = false;
    if (this.status === "finished") this.index = this.playlist.length - 1;
    this.elapsed = this.playlist.slice(0, this.index).reduce((a, c) => a + c.duration, 0);
    this.set("playing");
  }

  /** Start the whole sequence again from the first sign. */
  restart(): void {
    if (!this.playlist.length) return;
    this.elapsed = 0;
    this.index = 0;
    this.time = 0;
    this.fromPose = null;
    this.holdLeft = 0;
    this.holdDone = false;
    this.set("playing");
  }

  tick(dt: number): void {
    if (this.status !== "playing") return;
    let adv = dt * this.rate;
    this.elapsed += adv;
    if (this.fromPose) {
      this.blend += adv;
      if (this.blend >= TRANSITION_S) this.fromPose = null;
    }
    if (this.holdLeft > 0) {
      const used = Math.min(adv, this.holdLeft);
      this.holdLeft -= used;
      adv -= used;
    }
    if (adv > 0) {
      const before = this.time;
      this.time += adv;
      const peak = this.holdDone ? null : peakTime(this.playlist[this.index]);
      if (peak !== null && before < peak && this.time >= peak) {
        // hold the key handshape: the clip stands still at its peak for HOLD_S, then continues
        const over = this.time - peak;
        this.time = peak;
        this.holdDone = true;
        this.holdLeft = Math.max(0, HOLD_S - over);
      }
    }
    while (this.time >= this.playlist[this.index].duration) {
      this.time -= this.playlist[this.index].duration;
      this.holdLeft = 0;
      this.holdDone = false;
      if (this.index === this.playlist.length - 1) {
        this.time = 0;
        this.fromPose = null;
        this.set("finished");
        return;
      }
      const prev = this.playlist[this.index];
      this.index++;
      this.fromPose = this.sampler(prev, prev.duration);
      this.blend = this.time;
      this.emit();
    }
  }

  /** Pose to render now; empty (rest pose) when idle or finished. */
  pose(): Pose {
    if (this.status === "idle" || this.status === "finished" || !this.playlist.length) return {};
    const current = this.sampler(this.playlist[this.index], this.time);
    const pose = this.fromPose ? blendPoses(this.fromPose, current, smoothstep(this.blend / TRANSITION_S)) : current;
    if (!this.nmm.length) return pose;
    return withNmm(pose, this.nmm, this.elapsed, this.totalSeconds());
  }

  /** Non-manual marker state for the face: the tags, the playing time and the sentence length, or null when no sentence is playing. */
  nmmState(): { tags: readonly string[]; t: number; total: number } | null {
    if (this.status === "idle" || this.status === "finished" || !this.playlist.length || !this.nmm.length) return null;
    return { tags: this.nmm, t: this.elapsed, total: this.totalSeconds() };
  }

  snapshot(): PlayerSnapshot {
    return this.snap;
  }

  subscribe(cb: () => void): () => void {
    this.listeners.add(cb);
    return () => this.listeners.delete(cb);
  }

  private set(status: PlayerStatus): void {
    this.status = status;
    this.emit();
  }

  private emit(): void {
    this.snap = {
      status: this.status,
      index: this.index,
      total: this.playlist.length,
      gloss: this.playlist[this.index]?.gloss ?? null,
    };
    this.listeners.forEach((l) => l());
  }
}

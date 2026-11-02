import { slerpEuler, smoothstep } from "./idle";
import { withNmm } from "./nmm";
import { sampleClip, type Euler3, type Pose, type SignClip } from "./clip";

/** Seconds over which the avatar blends from the end of one sign into the start of the next. */
export const TRANSITION_S = 0.25;

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
  private nmm: string[] = [];
  private elapsed = 0; // playing time since the sentence started (for the head markers)

  setRate(rate: number): void {
    this.rate = rate;
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
    this.set("playing");
  }

  tick(dt: number): void {
    if (this.status !== "playing") return;
    this.time += dt * this.rate;
    this.elapsed += dt * this.rate;
    if (this.fromPose) {
      this.blend += dt * this.rate;
      if (this.blend >= TRANSITION_S) this.fromPose = null;
    }
    while (this.time >= this.playlist[this.index].duration) {
      this.time -= this.playlist[this.index].duration;
      if (this.index === this.playlist.length - 1) {
        this.time = 0;
        this.fromPose = null;
        this.set("finished");
        return;
      }
      const prev = this.playlist[this.index];
      this.index++;
      this.fromPose = sampleClip(prev, prev.duration);
      this.blend = this.time;
      this.emit();
    }
  }

  /** Pose to render now; empty (rest pose) when idle or finished. */
  pose(): Pose {
    if (this.status === "idle" || this.status === "finished" || !this.playlist.length) return {};
    const current = sampleClip(this.playlist[this.index], this.time);
    const pose = this.fromPose ? blendPoses(this.fromPose, current, smoothstep(this.blend / TRANSITION_S)) : current;
    if (!this.nmm.length) return pose;
    const total = this.playlist.reduce((a, c) => a + c.duration, 0);
    return withNmm(pose, this.nmm, this.elapsed, total);
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

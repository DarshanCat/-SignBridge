import bones from "./bones.json";

export type Euler3 = [number, number, number];
export type Pose = Record<string, Euler3>;

export interface Keyframe {
  t: number;
  rot: Euler3;
}
export interface Track {
  bone: string;
  keyframes: Keyframe[];
}
export interface SignClip {
  gloss: string;
  duration: number;
  tracks: Track[];
  source: { author: string; license: string; description: string };
}

export const BONES: readonly string[] = bones;

const isNum = (v: unknown): v is number => typeof v === "number" && Number.isFinite(v);

/** Validate untrusted JSON as a clip; throws a descriptive Error (mirrors backend/app/avatar/clip.py). */
export function parseClip(raw: unknown): SignClip {
  const c = raw as Partial<SignClip> | null;
  if (!c || typeof c !== "object") throw new Error("clip is not an object");
  if (typeof c.gloss !== "string" || !c.gloss.trim()) throw new Error("clip has no gloss");
  if (!isNum(c.duration) || c.duration <= 0 || c.duration > 20) throw new Error("clip duration must be in (0, 20]");
  if (!Array.isArray(c.tracks) || c.tracks.length === 0) throw new Error("clip has no tracks");
  const s = c.source;
  if (!s || !s.author || !s.license || !s.description) throw new Error("clip must state source author, license and description");

  for (const tr of c.tracks) {
    if (!BONES.includes(tr.bone)) throw new Error(`unknown bone ${String(tr.bone)}`);
    if (!Array.isArray(tr.keyframes) || tr.keyframes.length === 0) throw new Error(`track ${tr.bone} has no keyframes`);
    let prev = -1;
    for (const k of tr.keyframes) {
      if (!isNum(k.t) || k.t < prev || k.t > c.duration) throw new Error(`track ${tr.bone} has invalid keyframe times`);
      if (!Array.isArray(k.rot) || k.rot.length !== 3 || !k.rot.every(isNum)) throw new Error(`track ${tr.bone} has invalid rotation`);
      prev = k.t;
    }
  }
  return c as SignClip;
}

/** Linearly interpolate every track at time t (seconds). Bones without tracks are omitted (rest pose). */
export function sampleClip(clip: SignClip, t: number): Pose {
  const pose: Pose = {};
  for (const { bone, keyframes } of clip.tracks) {
    const first = keyframes[0];
    const last = keyframes[keyframes.length - 1];
    if (t <= first.t) pose[bone] = first.rot;
    else if (t >= last.t) pose[bone] = last.rot;
    else {
      const i = keyframes.findIndex((k) => k.t > t);
      const a = keyframes[i - 1];
      const b = keyframes[i];
      const f = (t - a.t) / (b.t - a.t || 1);
      pose[bone] = [0, 1, 2].map((n) => a.rot[n] + (b.rot[n] - a.rot[n]) * f) as Euler3;
    }
  }
  return pose;
}

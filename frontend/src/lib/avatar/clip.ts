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
/**
 * Source landmarks of the dataset sample the clip was retargeted from (added by backend/retarget/add_source_landmarks.py), at the keyframe
 * times t. Values are the stored normalized features (origin shoulder midpoint, unit shoulder width, image axes x right, y down, z depth).
 * pose holds the MediaPipe pose points named in pose_idx; left and right hold the 21 hand points, or null when the hand was not detected.
 */
export interface ClipLandmarks {
  version: number;
  t: number[];
  pose_idx: number[];
  pose: number[][][];
  left: (number[][] | null)[];
  right: (number[][] | null)[];
}

export interface SignClip {
  gloss: string;
  duration: number;
  tracks: Track[];
  landmarks?: ClipLandmarks;
  source: { author: string; license: string; description: string; review_status?: "not_signer_reviewed" | "signer_reviewed" };
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
  const clip = c as SignClip;
  if (clip.landmarks !== undefined && !validLandmarks(clip.landmarks)) delete clip.landmarks; // optional extra: an unusable one is ignored, never fatal
  return clip;
}

const isPoint = (p: unknown): boolean => Array.isArray(p) && p.length === 3 && p.every(isNum);

function validLandmarks(l: unknown): l is ClipLandmarks {
  const m = l as Partial<ClipLandmarks> | null;
  if (!m || m.version !== 1 || !Array.isArray(m.t) || !m.t.length || !m.t.every(isNum)) return false;
  if (!Array.isArray(m.pose_idx) || !m.pose_idx.every(isNum) || !Array.isArray(m.pose) || !Array.isArray(m.left) || !Array.isArray(m.right)) return false;
  const n = m.t.length;
  if (m.pose.length !== n || m.left.length !== n || m.right.length !== n) return false;
  const hand = (h: unknown) => h === null || (Array.isArray(h) && h.length === 21 && h.every(isPoint));
  return m.pose.every((f) => Array.isArray(f) && f.length === m.pose_idx!.length && f.every(isPoint)) && m.left.every(hand) && m.right.every(hand);
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

export interface Point {
  x: number;
  y: number;
  z: number;
}

/** One frame of landmarks, matching the backend `LandmarkFrame` schema. */
export interface LandmarkFrame {
  pose: Point[] | null;
  left_hand: Point[] | null;
  right_hand: Point[] | null;
}

export interface HolisticResults {
  poseLandmarks?: Point[];
  leftHandLandmarks?: Point[];
  rightHandLandmarks?: Point[];
}

export const BUFFER_FRAMES = 60;

const strip = (pts?: Point[]): Point[] | null =>
  pts && pts.length ? pts.map((p) => ({ x: p.x, y: p.y, z: p.z ?? 0 })) : null;

export function toFrame(r: HolisticResults): LandmarkFrame {
  return { pose: strip(r.poseLandmarks), left_hand: strip(r.leftHandLandmarks), right_hand: strip(r.rightHandLandmarks) };
}

/** Append a frame, keeping only the newest `max` frames (landmarks only; no video is stored). */
export function pushFrame(buffer: LandmarkFrame[], frame: LandmarkFrame, max = BUFFER_FRAMES): LandmarkFrame[] {
  const next = [...buffer, frame];
  return next.length > max ? next.slice(next.length - max) : next;
}

/** Consecutive frames without a body pose after which the buffered sequence is considered stale and dropped. */
export const MAX_MISSING_POSE = 15;

export interface BufferState {
  frames: LandmarkFrame[];
  missingStreak: number;
}

export const EMPTY_BUFFER: BufferState = { frames: [], missingStreak: 0 };

/**
 * Append a frame to a bounded buffer. If tracking is lost (no body pose for more than `maxMissing` frames in a row)
 * the buffer is cleared so an old partial sign is never mixed with a new one.
 */
export function appendFrame(
  state: BufferState,
  frame: LandmarkFrame,
  max = BUFFER_FRAMES,
  maxMissing = MAX_MISSING_POSE,
): BufferState {
  const missingStreak = frame.pose ? 0 : state.missingStreak + 1;
  if (missingStreak > maxMissing) return { frames: [], missingStreak };
  return { frames: pushFrame(state.frames, frame, max), missingStreak };
}

export interface CaptureStats {
  frames: number;
  withPose: number;
  withHands: number;
}

export function summarize(buffer: LandmarkFrame[]): CaptureStats {
  return {
    frames: buffer.length,
    withPose: buffer.filter((f) => f.pose).length,
    withHands: buffer.filter((f) => f.left_hand || f.right_hand).length,
  };
}

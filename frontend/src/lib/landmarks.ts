import { FACE_INDICES, FULL_FACE_POINTS } from "./faceIndices";

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
  /** The 50 eyebrow, eye and mouth points (FACE_INDICES order); null when no face was found. Optional: the backend ignores it unless the model uses the face. */
  face?: Point[] | null;
}

export interface HolisticResults {
  faceLandmarks?: Point[];
  poseLandmarks?: Point[];
  leftHandLandmarks?: Point[];
  rightHandLandmarks?: Point[];
}

export const BUFFER_FRAMES = 60;

/**
 * MediaPipe gives x as a fraction of the image width and y as a fraction of its height, so one unit of y is a different physical length
 * than one unit of x unless the image is square. The model was trained on 16:9 INCLUDE videos; a 4:3 webcam stretches y by (16/9)/(4/3) in
 * those units, which changes the pose the model sees (measured on test videos: wrong signs on 4:3 input, right signs after resizing to 16:9).
 * toFrame therefore rescales y to what the same pose would be in a 16:9 image. x and z are unchanged. Backend normalization stays as it is.
 */
export const REFERENCE_ASPECT = 16 / 9;

export function yScaleFor(aspect: number): number {
  return Number.isFinite(aspect) && aspect > 0 ? REFERENCE_ASPECT / aspect : 1;
}

const strip = (pts: Point[] | undefined, ys: number): Point[] | null =>
  pts && pts.length ? pts.map((p) => ({ x: p.x, y: p.y * ys, z: p.z ?? 0 })) : null;

/** aspect: width / height of the image the landmarks were measured on (the camera video); omit for no correction. */
export function toFrame(r: HolisticResults, aspect: number = REFERENCE_ASPECT): LandmarkFrame {
  const ys = yScaleFor(aspect);
  const face = r.faceLandmarks && r.faceLandmarks.length === FULL_FACE_POINTS ? strip(FACE_INDICES.map((i) => r.faceLandmarks![i]), ys) : null;
  return { pose: strip(r.poseLandmarks, ys), left_hand: strip(r.leftHandLandmarks, ys), right_hand: strip(r.rightHandLandmarks, ys), face };
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

/** Landmark overlay drawing and a plain readout of what the body pose tracker sees. Display only; nothing here touches the stored frames. */

export interface OverlayPoint {
  x: number;
  y: number;
  visibility?: number;
}

export interface OverlayResults {
  poseLandmarks?: OverlayPoint[];
  leftHandLandmarks?: OverlayPoint[];
  rightHandLandmarks?: OverlayPoint[];
}

/** Body pose bones that matter for signing: shoulders, arms, torso. (MediaPipe pose indices.) */
export const POSE_BONES: [number, number][] = [
  [11, 12], [11, 13], [13, 15], [12, 14], [14, 16], [11, 23], [12, 24], [23, 24],
];
export const VISIBLE = 0.5;
export const NOSE = 0;
export const LEFT_SHOULDER = 11;
export const RIGHT_SHOULDER = 12;
export const LEFT_ELBOW = 13;
export const RIGHT_ELBOW = 14;
export const LEFT_WRIST = 15;
export const RIGHT_WRIST = 16;

export interface PoseReadout {
  detected: boolean;
  /** Landmarks (of 33) with visibility above the threshold. */
  visible: number;
  shoulders: boolean;
  elbows: boolean;
  wrists: boolean;
  /** Distance between the shoulders as a fraction of the picture width (x only), or null when a shoulder is not visible. */
  shoulderWidth: number | null;
}

/**
 * Smallest shoulder width (fraction of the picture width) that is not warned about. Chosen on validation videos shrunk toward the centre
 * (docs/evaluation/BROWSER_PATH.md, section on framing): accuracy was 0.83 to 0.89 at 0.10 and above, 0.71 at 0.08 to 0.10, about 0.55 below 0.08
 * with 12 to 14 percent confident wrong answers. INCLUDE signers measure 0.12 to 0.15.
 */
export const MIN_SHOULDER_WIDTH = 0.1;

/** A warning when the signer is too small in the picture (too far from the camera); null when the size is fine or unknown. */
export function framingWarning(r: PoseReadout): string | null {
  if (r.shoulderWidth === null || r.shoulderWidth >= MIN_SHOULDER_WIDTH) return null;
  return "You look small in the picture. Move closer or zoom in so your head, shoulders and both hands fill most of the frame; small signers are recognized less reliably.";
}

const seen = (p: OverlayPoint | undefined): boolean => !!p && (p.visibility ?? 1) > VISIBLE && p.x >= 0 && p.x <= 1 && p.y >= 0 && p.y <= 1;

export function poseReadout(pose: OverlayPoint[] | undefined): PoseReadout {
  if (!pose || pose.length < 17) return { detected: false, visible: 0, shoulders: false, elbows: false, wrists: false, shoulderWidth: null };
  const both = seen(pose[LEFT_SHOULDER]) && seen(pose[RIGHT_SHOULDER]);
  return {
    shoulderWidth: both ? Math.abs(pose[LEFT_SHOULDER].x - pose[RIGHT_SHOULDER].x) : null,
    detected: true,
    visible: pose.filter(seen).length,
    shoulders: seen(pose[LEFT_SHOULDER]) && seen(pose[RIGHT_SHOULDER]),
    elbows: seen(pose[LEFT_ELBOW]) || seen(pose[RIGHT_ELBOW]),
    wrists: seen(pose[LEFT_WRIST]) || seen(pose[RIGHT_WRIST]),
  };
}

/** One sentence telling the signer what to adjust. */
export function poseAdvice(r: PoseReadout): string {
  if (!r.detected) return "Body pose not detected: step back until your head, shoulders and arms are in view, with even lighting.";
  if (!r.shoulders) return "Shoulders not fully visible: step back or lower the camera. The model needs both shoulders to normalize the landmarks.";
  if (!r.elbows) return "Elbows are out of view: step back a little so your arms are visible.";
  return `Body pose detected (${r.visible} of 33 landmarks visible).`;
}

interface Ctx2D {
  clearRect(x: number, y: number, w: number, h: number): void;
  beginPath(): void;
  arc(x: number, y: number, r: number, a: number, b: number): void;
  fill(): void;
  moveTo(x: number, y: number): void;
  lineTo(x: number, y: number): void;
  stroke(): void;
  fillStyle: string | CanvasGradient | CanvasPattern;
  strokeStyle: string | CanvasGradient | CanvasPattern;
  lineWidth: number;
}

/** Draw the pose skeleton (lines and joints, visible landmarks only) and both hands. */
export function drawOverlay(ctx: Ctx2D, w: number, h: number, r: OverlayResults): void {
  ctx.clearRect(0, 0, w, h);
  const pose = r.poseLandmarks;
  if (pose) {
    ctx.strokeStyle = "#5eead4";
    ctx.lineWidth = 4;
    for (const [a, b] of POSE_BONES) {
      if (!seen(pose[a]) || !seen(pose[b])) continue;
      ctx.beginPath();
      ctx.moveTo(pose[a].x * w, pose[a].y * h);
      ctx.lineTo(pose[b].x * w, pose[b].y * h);
      ctx.stroke();
    }
    ctx.fillStyle = "#5eead4";
    for (const i of [NOSE, LEFT_SHOULDER, RIGHT_SHOULDER, LEFT_ELBOW, RIGHT_ELBOW, LEFT_WRIST, RIGHT_WRIST, 23, 24]) {
      if (!seen(pose[i])) continue;
      ctx.beginPath();
      ctx.arc(pose[i].x * w, pose[i].y * h, 6, 0, 2 * Math.PI);
      ctx.fill();
    }
  }
  const dots = (pts: OverlayPoint[] | undefined, color: string) => {
    ctx.fillStyle = color;
    pts?.forEach((p) => {
      ctx.beginPath();
      ctx.arc(p.x * w, p.y * h, 3, 0, 2 * Math.PI);
      ctx.fill();
    });
  };
  dots(r.leftHandLandmarks, "#fbbf24");
  dots(r.rightHandLandmarks, "#f472b6");
}

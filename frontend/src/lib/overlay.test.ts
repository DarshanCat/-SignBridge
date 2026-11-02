import { describe, expect, it } from "vitest";
import { drawOverlay, poseAdvice, poseReadout, type OverlayPoint } from "./overlay";

const pt = (x: number, y: number, visibility = 0.9): OverlayPoint => ({ x, y, visibility });
const fullPose = (): OverlayPoint[] => Array.from({ length: 33 }, (_, i) => pt(0.3 + (i % 5) * 0.1, 0.2 + Math.floor(i / 5) * 0.1));

function fakeCtx() {
  const calls: string[] = [];
  return {
    calls,
    ctx: {
      clearRect: () => calls.push("clear"),
      beginPath: () => {},
      arc: () => calls.push("arc"),
      fill: () => {},
      moveTo: () => {},
      lineTo: () => calls.push("line"),
      stroke: () => {},
      fillStyle: "",
      strokeStyle: "",
      lineWidth: 1,
    },
  };
}

describe("pose overlay", () => {
  it("draws body bones and joints, not only the face", () => {
    const { ctx, calls } = fakeCtx();
    drawOverlay(ctx, 640, 480, { poseLandmarks: fullPose() });
    expect(calls.filter((c) => c === "line").length).toBe(8); // shoulders, both arms, torso
    expect(calls.filter((c) => c === "arc").length).toBe(9); // nose, shoulders, elbows, wrists, hips
  });

  it("skips landmarks that are not visible or out of frame", () => {
    const pose = fullPose();
    pose[13] = pt(0.5, 0.5, 0.1); // left elbow not visible
    pose[16] = pt(1.4, 0.5); // right wrist outside the image
    const { ctx, calls } = fakeCtx();
    drawOverlay(ctx, 640, 480, { poseLandmarks: pose });
    expect(calls.filter((c) => c === "line").length).toBe(5);
  });

  it("draws hands as dots", () => {
    const { ctx, calls } = fakeCtx();
    drawOverlay(ctx, 640, 480, { leftHandLandmarks: Array.from({ length: 21 }, () => pt(0.2, 0.2)) });
    expect(calls.filter((c) => c === "arc").length).toBe(21);
  });

  it("reports what the tracker sees and tells the signer what to fix", () => {
    expect(poseReadout(undefined).detected).toBe(false);
    expect(poseAdvice(poseReadout(undefined))).toMatch(/not detected/);
    const noShoulders = fullPose();
    noShoulders[11] = pt(0.5, 1.2);
    expect(poseAdvice(poseReadout(noShoulders))).toMatch(/Shoulders not fully visible/);
    const r = poseReadout(fullPose());
    expect(r).toMatchObject({ detected: true, shoulders: true, elbows: true, wrists: true });
    expect(poseAdvice(r)).toMatch(/Body pose detected/);
  });
});

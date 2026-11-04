import { mkdirSync, writeFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { sampleClip, type SignClip } from "./clip";
import { applyMixamoPose } from "./mixamo";
import { mergePose, SignRetargeter } from "./retarget";
import { Accumulator, handPenetrates, measureFrame } from "./retargetError";
import { frameCount, sourceFrame } from "./sourceLandmarks";
import { hasClip, hasVrm, loadAvatar, loadClip, MEASURE_CLIPS } from "./testSupport";

/**
 * Retarget accuracy on the real avatar and real clips: forward kinematics of the pose each method produces, against the source landmarks.
 * Set RETARGET_REPORT=<file.json> to write the numbers (docs/avatar_retarget uses it). The thresholds are a regression guard for the improved
 * retarget; the first describe block records the legacy numbers for comparison and only checks that they are measurable.
 */
const clips = MEASURE_CLIPS.filter(hasClip);
const enough = hasVrm && clips.length >= 8;

export interface Method {
  name: string;
  /** Apply the pose of this method for source frame i of the clip to the avatar rig. */
  apply: (clip: SignClip, i: number) => void;
}

export async function measure(methods: Method[]) {
  const { rig, anatomy, vrm } = await loadAvatar();
  const report: Record<string, ReturnType<Accumulator["result"]>> = {};
  for (const method of methods) {
    const acc = new Accumulator();
    for (const name of clips) {
      const clip = loadClip(name);
      const lm = clip.landmarks;
      if (!lm) throw new Error(`${name} has no landmarks: run backend/retarget/add_source_landmarks.py`);
      for (let i = 0; i < frameCount(lm); i++) {
        method.apply(clip, i);
        for (const { side, m } of measureFrame(anatomy, vrm.humanoid, sourceFrame(lm, i))) {
          acc.add(m);
          acc.addPenetration(handPenetrates(anatomy, vrm.humanoid, side));
        }
      }
    }
    report[method.name] = acc.result();
  }
  void rig;
  return report;
}

export const legacy: Method = {
  name: "legacy",
  apply: (clip, i) => {
    // the tracks were built from exactly these frames; applying them at the frame times reproduces what the avatar shows
    return void applyLegacy(clip, i);
  },
};

let rigRef: Awaited<ReturnType<typeof loadAvatar>> | null = null;
let retargeter: SignRetargeter | null = null;

function solverMethod(name: string, options: { mapToBody: boolean; collide: boolean; liftDepth: boolean }): Method {
  return {
    name,
    apply: (clip, i) => {
      if (!rigRef) throw new Error("avatar not loaded");
      retargeter ??= new SignRetargeter(rigRef.rig, rigRef.anatomy);
      Object.assign(retargeter.options, options);
      const t = clip.landmarks!.t[i];
      const solved = retargeter.solve(sourceFrame(clip.landmarks!, i));
      applyMixamoPose(rigRef.rig, mergePose(sampleClip(clip, t), solved));
    },
  };
}
export const solver = solverMethod("solver", { mapToBody: true, collide: true, liftDepth: true });
export const solverPlain = solverMethod("solver_plain", { mapToBody: false, collide: false, liftDepth: false });
export const solverNoCollide = solverMethod("solver_no_collision", { mapToBody: true, collide: false, liftDepth: true });
function applyLegacy(clip: SignClip, i: number): void {
  if (!rigRef) throw new Error("avatar not loaded");
  applyMixamoPose(rigRef.rig, sampleClip(clip, clip.landmarks!.t[i]));
}

describe.skipIf(!enough)("retarget accuracy on signer.vrm: legacy clip tracks against the new retargeter", () => {
  it("measures every joint, writes the reports when asked, and the new retargeter is better", async () => {
    rigRef = await loadAvatar();
    const { anatomy } = rigRef;
    // the anatomy read from the model is plausible: the mouth is just below the eyes and the head is above the shoulders
    expect(anatomy.mouthFrom).toBe("morph");
    expect(anatomy.eyes.y - anatomy.mouth.y).toBeGreaterThan(0.01);
    expect(anatomy.head.center.y).toBeGreaterThan(anatomy.shoulderMid.y);
    const report = await measure([legacy, solverPlain, solverNoCollide, solver]);
    if (process.env.RETARGET_REPORT_DIR) {
      mkdirSync(process.env.RETARGET_REPORT_DIR, { recursive: true });
      for (const [name, r] of Object.entries(report))
        writeFileSync(`${process.env.RETARGET_REPORT_DIR}/measurement_${name}.json`, JSON.stringify({ clips, anatomy: { sw: anatomy.sw, mouth: anatomy.mouth, eyes: anatomy.eyes, head: anatomy.head, armLen: anatomy.armLen, torso: anatomy.torso }, report: { [name]: r } }, null, 1));
    }
    const pick = (r: (typeof report)[string]) => ({ wrist3d: +r.position.wrist.mean.toFixed(3), wrist2d: +r.position2d.wrist.mean.toFixed(3), tip2d: +r.position2d["index.tip"].mean.toFixed(3), fore: +r.direction.foreArm.mean.toFixed(1), hand: +r.direction.hand.mean.toFixed(1), idxMCP: +r.direction["index.MCP-PIP"].mean.toFixed(1), pen: +r.penetration.any.mean.toFixed(3) });
    expect(report.legacy.position.wrist.n).toBeGreaterThan(100);
    // the improved retarget against the legacy tracks (picture-plane error, because the source depth is unreliable) and against its own earlier numbers
    const L = report.legacy;
    const S = report.solver;
    expect(S.position2d.wrist.mean).toBeLessThan(0.05); // legacy 0.23 shoulder widths
    expect(S.position2d["index.tip"].mean).toBeLessThan(0.2); // legacy 0.35
    expect(S.direction.hand.mean).toBeLessThan(3); // legacy 11 degrees
    expect(S.direction["index.MCP-PIP"].mean).toBeLessThan(10); // legacy 28 degrees
    expect(S.direction["thumb.CMC-MCP"].mean).toBeLessThan(L.direction["thumb.CMC-MCP"].mean / 2);
    expect(S.penetration.any.mean).toBeLessThan(0.05); // without collision about a third of the frames put a hand into the body
    expect(report.solver_no_collision.penetration.any.mean).toBeGreaterThan(0.15);
    for (const k of ["wrist", "index.tip", "pinky.tip", "thumb.tip"]) expect(S.position2d[k].mean, k).toBeLessThan(L.position2d[k].mean);
    console.warn(JSON.stringify(Object.fromEntries(Object.entries(report).map(([k, v]) => [k, pick(v)]))));
  });
});

import { readdirSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { sampleClip } from "./clip";
import { mergePose, SignRetargeter } from "./retarget";
import { makeSampler } from "./solverSampler";
import { frameCount, sourceFrame, sourceFrameAtTime } from "./sourceLandmarks";
import { hasVrm, loadAvatar, loadClip } from "./testSupport";

const dir = join(process.cwd(), "public", "animations");
let names: string[] = [];
try {
  names = readdirSync(dir).filter((f) => f.endsWith(".json") && f !== "index.json").map((f) => f.slice(0, -5));
} catch {
  names = [];
}

describe.skipIf(!hasVrm || names.length < 50)("the retargeter never produces a non-finite rotation (a NaN would break the avatar for good)", () => {
  it("every clip, every source frame and a dense sweep of times", async () => {
    const { rig, anatomy } = await loadAvatar();
    const rt = new SignRetargeter(rig, anatomy);
    const sampler = makeSampler(rt);
    const bad: string[] = [];
    let withLandmarks = 0;
    for (const name of names) {
      const clip = loadClip(name);
      const lm = clip.landmarks;
      if (!lm) continue;
      withLandmarks++;
      const check = (pose: Record<string, number[]>, where: string) => {
        for (const [bone, e] of Object.entries(pose)) if (!e.every(Number.isFinite)) bad.push(`${name} ${where} ${bone}`);
      };
      for (let i = 0; i < frameCount(lm); i++) check(mergePose(sampleClip(clip, lm.t[i]), rt.solve(sourceFrame(lm, i))), `frame ${i}`);
      for (let t = 0; t <= clip.duration; t += 0.05) check(sampler(clip, t), `t ${t.toFixed(2)}`);
      // interpolated source frames are sound too
      const f = sourceFrameAtTime(lm, clip.duration / 2);
      expect(Number.isFinite(f.wrist.l.x + f.wrist.r.y)).toBe(true);
    }
    expect(withLandmarks).toBeGreaterThan(200);
    expect(bad.slice(0, 5)).toEqual([]);
  });
});

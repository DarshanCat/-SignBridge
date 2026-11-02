import { describe, expect, it } from "vitest";
import type { AvatarPlan, TextToGloss } from "../api";
import type { SignClip } from "./clip";
import { textToClips } from "./pipeline";

const clip = (gloss: string): SignClip => ({ gloss, duration: 1, source: { author: "t", license: "t", description: "t" }, tracks: [] });
const gloss = (tokens: string[], nmm: string[] = []): TextToGloss => ({
  gloss: tokens, tokens: tokens.map((g) => ({ gloss: g, kind: "sign", source: g })), nmm, tense: "present", dropped: [], fingerspelled: [], note: "",
});

describe("textToClips", () => {
  it("plays clips in sentence order, reports glosses without a clip and reports its stages", async () => {
    const stages: string[] = [];
    const out = await textToClips("Where is the hospital?", {
      textToGloss: async () => gloss(["HOSPITAL", "WHERE"], ["wh-question"]),
      plan: async (g): Promise<AvatarPlan> => ({
        steps: g.map((x) => ({ gloss: x, available: x === "HOSPITAL", clip_url: x === "HOSPITAL" ? "/animations/hospital.json" : null })),
        missing: ["WHERE"], playable: true, message: "",
      }),
      load: async () => ({ clips: [clip("HOSPITAL")], failed: [] }),
      onStage: (s) => stages.push(s),
    });
    expect(out.clips.map((c) => c.gloss)).toEqual(["HOSPITAL"]);
    expect(out.views.map((v) => v.status)).toEqual(["clip", "no_clip"]);
    expect(out.gloss.nmm).toEqual(["wh-question"]);
    expect(stages).toEqual(["Converting text to gloss", "Looking up sign clips", "Loading 1 clip(s)"]);
  });

  it("does not call the plan for text without signable tokens and keeps repeats", async () => {
    let planned = false;
    const none = await textToClips("...", { textToGloss: async () => gloss([]), plan: async () => { planned = true; throw new Error("no"); } });
    expect(none).toMatchObject({ clips: [], views: [] });
    expect(planned).toBe(false);
    const twice = await textToClips("I I", {
      textToGloss: async () => gloss(["I", "I"]),
      plan: async (): Promise<AvatarPlan> => ({ steps: [{ gloss: "I", available: true, clip_url: "/a/i.json" }], missing: [], playable: true, message: "" }),
      load: async () => ({ clips: [clip("I")], failed: [] }),
    });
    expect(twice.clips).toHaveLength(2);
  });
});

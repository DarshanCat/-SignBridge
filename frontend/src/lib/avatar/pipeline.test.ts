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

  it("spells an unknown word letter by letter when every ISL alphabet clip (FS-A to FS-Z) exists, and reports the whole word as missing otherwise", async () => {
    const spelled: TextToGloss = {
      gloss: ["HELLO", "FS:RAJ"],
      tokens: [{ gloss: "HELLO", kind: "sign", source: "hello" }, { gloss: "FS:RAJ", kind: "fingerspell", source: "raj", letters: ["R", "A", "J"] }],
      nmm: [], tense: "present", dropped: [], fingerspelled: ["RAJ"], note: "",
    } as TextToGloss;
    const run = (have: string[]) =>
      textToClips("Hello Raj", {
        textToGloss: async () => spelled,
        plan: async (g): Promise<AvatarPlan> => ({
          steps: g.map((x) => ({ gloss: x, available: have.includes(x), clip_url: have.includes(x) ? `/animations/${x.toLowerCase()}.json` : null })),
          missing: g.filter((x) => !have.includes(x)), playable: true, message: "",
        }),
        load: async (steps) => ({ clips: steps.filter((x) => x.available).map((x) => clip(x.gloss)), failed: [] }),
      });
    const all = await run(["HELLO", "FS-R", "FS-A", "FS-J"]);
    expect(all.clips.map((c) => c.gloss)).toEqual(["HELLO", "FS-R", "FS-A", "FS-J"]);
    expect(all.views.map((v) => v.status)).toEqual(["clip", "fingerspelled"]);
    const partial = await run(["HELLO", "FS-R", "FS-A"]); // FS-J is missing: nothing is invented, the word is skipped
    expect(partial.clips.map((c) => c.gloss)).toEqual(["HELLO"]);
    expect(partial.views[1]).toMatchObject({ gloss: "FS:RAJ", status: "no_clip" });
  });
});

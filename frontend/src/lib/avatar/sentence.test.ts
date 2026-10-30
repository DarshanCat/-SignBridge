import { describe, expect, it } from "vitest";
import { describeTokens, glossesToPlan, playableSteps } from "./sentence";

const toks = [
  { gloss: "HOSPITAL", kind: "sign" },
  { gloss: "WHERE", kind: "sign" },
  { gloss: "FS:RAJ", kind: "fingerspell", letters: ["R", "A", "J"] },
];

describe("sentence token availability", () => {
  it("asks the plan about signs and letter glosses", () => {
    expect(glossesToPlan(toks)).toEqual(["HOSPITAL", "WHERE", "FS-R", "FS-A", "FS-J"]);
  });

  it("marks glosses without a clip clearly and never fakes one", () => {
    const v = describeTokens(toks, new Set(["HOSPITAL"]));
    expect(v.map((t) => t.status)).toEqual(["clip", "no_clip", "no_clip"]);
    expect(v[1].label).toBe("no clip for WHERE");
    expect(v[2].play).toEqual([]);
  });

  it("uses fingerspelling only when every letter has a clip", () => {
    expect(describeTokens(toks, new Set(["FS-R", "FS-A"]))[2].status).toBe("no_clip");
    const v = describeTokens(toks, new Set(["FS-R", "FS-A", "FS-J"]))[2];
    expect(v.status).toBe("fingerspelled");
    expect(v.play).toEqual(["FS-R", "FS-A", "FS-J"]);
  });

  it("orders playable steps by the sentence and keeps repeats", () => {
    const steps = [
      { gloss: "HOSPITAL", available: true, clip_url: "/animations/hospital.json" },
      { gloss: "HELLO", available: true, clip_url: "/animations/hello.json" },
    ];
    const t = [{ gloss: "HELLO", kind: "sign" }, { gloss: "HOSPITAL", kind: "sign" }, { gloss: "HELLO", kind: "sign" }];
    const v = describeTokens(t, new Set(["HOSPITAL", "HELLO"]));
    expect(playableSteps(v, steps).map((s) => s.gloss)).toEqual(["HELLO", "HOSPITAL", "HELLO"]);
  });
});

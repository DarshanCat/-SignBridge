import { describe, expect, it } from "vitest";
import { buildRecordRequest } from "./recorder";
import { applyTake, currentGloss, parseGlossList, previousGloss, progress, skipGloss, startSession, validateConfig } from "./recordSession";

const cfg = { signerId: "p01", glosses: ["WHERE", "GO", "LIKE"], takesPerGloss: 2 };

describe("record session state", () => {
  it("starts at the first gloss, normalizes the signer and counts only accepted takes", () => {
    let s = startSession(cfg);
    expect(s.config.signerId).toBe("P01");
    expect(currentGloss(s)).toBe("WHERE");
    s = applyTake(s, false); // rejected: not counted, same gloss again
    expect(currentGloss(s)).toBe("WHERE");
    expect(s.accepted.WHERE).toBe(0);
    expect(s.attempts.WHERE).toBe(1);
    s = applyTake(s, true);
    expect(currentGloss(s)).toBe("WHERE");
    s = applyTake(s, true); // second accepted take: on to GO
    expect(currentGloss(s)).toBe("GO");
    expect(progress(s)).toEqual({ takes: 2, targetTakes: 6, glossesDone: 1, glossesTotal: 3 });
  });

  it("ends when every gloss has enough takes", () => {
    let s = startSession(cfg);
    for (let i = 0; i < 6; i++) s = applyTake(s, true);
    expect(s.done).toBe(true);
    expect(currentGloss(s)).toBeNull();
    expect(applyTake(s, true)).toBe(s);
  });

  it("resumes from the takes already on disk and skips finished glosses", () => {
    const s = startSession(cfg, { WHERE: 2, GO: 1 });
    expect(currentGloss(s)).toBe("GO");
    expect(progress(s).takes).toBe(3);
    expect(startSession(cfg, { WHERE: 5, GO: 2, LIKE: 2 }).done).toBe(true);
  });

  it("skip leaves the gloss unfinished and brings it back after the others; back revisits a finished gloss", () => {
    let s = startSession(cfg);
    s = skipGloss(s);
    expect(currentGloss(s)).toBe("GO");
    s = applyTake(applyTake(s, true), true); // GO complete
    expect(currentGloss(s)).toBe("LIKE");
    s = applyTake(applyTake(s, true), true); // LIKE complete: WHERE is the only one left
    expect(currentGloss(s)).toBe("WHERE");
    s = previousGloss(s);
    expect(currentGloss(s)).toBe("LIKE");
    expect(skipGloss(startSession({ ...cfg, glosses: ["A"] }))).toMatchObject({ index: 0 });
  });

  it("validates the setup and parses the gloss list", () => {
    expect(validateConfig(cfg)).toEqual([]);
    expect(validateConfig({ signerId: "../x", glosses: [], takesPerGloss: 0 })).toHaveLength(3);
    expect(parseGlossList("where, go\nlike  NOT ; where good-morning").glosses).toEqual(["WHERE", "GO", "LIKE", "NOT", "GOOD-MORNING"]);
    expect(parseGlossList("ok ../x -bad").invalid).toEqual(["../x", "-bad"]);
  });

  it("session takes are sent with the signer and without a clip", () => {
    const frame = { pose: null, left_hand: null, right_hand: null };
    const body = buildRecordRequest("where", [frame, frame], 1000, { signerId: "P01", makeClip: false });
    expect(body).toMatchObject({ gloss: "WHERE", signer_id: "P01", make_clip: false, fps: 2 });
    expect(Object.keys(buildRecordRequest("where", [frame], 1000)).sort()).toEqual(["fps", "frames", "gloss"]);
  });
});

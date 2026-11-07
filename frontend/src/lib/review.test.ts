import { describe, expect, it } from "vitest";
import { filterClips, isValidReviewer, nextUnreviewed, validateReview, type ReviewRecord } from "./review";

const rec = (gloss: string): ReviewRecord => ({ reviewer_id: "R01", gloss, clarity: 4, verdict: "correct", comment: "", reviewed_at_utc: "2026-11-07T00:00:00+00:00", clip_sha256: null });
const ok = { reviewerId: "R01", gloss: "HELLO", clarity: 4, verdict: "correct" as const, comment: "" };

describe("validateReview", () => {
  it("accepts a complete review", () => expect(validateReview(ok)).toEqual([]));
  it("names everything that is missing", () => {
    expect(validateReview({ ...ok, reviewerId: "" })).toHaveLength(1);
    expect(validateReview({ ...ok, gloss: null })).toHaveLength(1);
    expect(validateReview({ ...ok, clarity: null })).toHaveLength(1);
    expect(validateReview({ ...ok, clarity: 6 })).toHaveLength(1);
    expect(validateReview({ ...ok, verdict: null })).toHaveLength(1);
    expect(validateReview({ ...ok, comment: "x".repeat(501) })).toHaveLength(1);
    expect(validateReview({ reviewerId: "", gloss: null, clarity: null, verdict: null, comment: "" })).toHaveLength(4);
  });
  it("only accepts an ID like the recorder's signer ID", () => {
    expect(isValidReviewer(" r-01 ")).toBe(true);
    expect(isValidReviewer("Ravi Kumar")).toBe(false);
    expect(isValidReviewer("../x")).toBe(false);
  });
});

describe("clip list", () => {
  const glosses = ["WHERE", "HELLO", "THANK-YOU", "DOCTOR"];
  it("is sorted, searchable (hyphen and space alike) and can hide the reviewed ones", () => {
    expect(filterClips(glosses, [], "", false).map((r) => r.gloss)).toEqual(["DOCTOR", "HELLO", "THANK-YOU", "WHERE"]);
    expect(filterClips(glosses, [], "thank you", false).map((r) => r.gloss)).toEqual(["THANK-YOU"]);
    expect(filterClips(glosses, [rec("HELLO")], "", true).map((r) => r.gloss)).toEqual(["DOCTOR", "THANK-YOU", "WHERE"]);
    expect(filterClips(glosses, [rec("HELLO")], "hel", false)[0].reviewed?.gloss).toBe("HELLO");
  });
  it("finds the next sign not yet reviewed, wrapping around, or null when all are done", () => {
    expect(nextUnreviewed(glosses, [rec("DOCTOR")], "DOCTOR")).toBe("HELLO");
    expect(nextUnreviewed(glosses, [rec("WHERE")], "THANK-YOU")).toBe("DOCTOR");
    expect(nextUnreviewed(glosses, glosses.map(rec), "HELLO")).toBeNull();
    expect(nextUnreviewed(glosses, [], null)).toBe("DOCTOR");
  });
});

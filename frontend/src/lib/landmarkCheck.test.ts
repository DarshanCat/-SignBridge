import { describe, expect, it } from "vitest";
import { buildCheckFile, compareCommand, extensionFor, fileStem, pickMimeType } from "./landmarkCheck";

const f = { pose: null, left_hand: null, right_hand: null };

describe("landmark check helpers", () => {
  it("picks the first supported recording format", () => {
    expect(pickMimeType((m) => m === "video/webm")).toBe("video/webm");
    expect(pickMimeType(() => true)).toBe("video/webm;codecs=vp9");
    expect(pickMimeType(() => false)).toBeNull();
    expect(extensionFor("video/mp4")).toBe("mp4");
    expect(extensionFor("video/webm;codecs=vp9")).toBe("webm");
  });

  it("names both files with the same stem", () => {
    expect(fileStem(new Date(2026, 9, 31, 10, 5, 2))).toBe("signbridge_check_20261031_100502");
  });

  it("builds the landmark file with times relative to the video start and drops frames outside the recording", () => {
    const file = buildCheckFile("s", "video/webm", 1000, [f, f, f, f], [990, 1100, 1900, 2200], 1000, true, new Date(0));
    expect(file.frames.map((x) => x.t)).toEqual([100, 900]); // 990 is before the start, 2200 after the end
    expect(file).toMatchObject({ version: 1, video_file: "s.webm", video_duration_ms: 1000, extractor: { delegate: "cpu" } });
  });

  it("prints the comparison command for the two files", () => {
    const c = compareCommand("signbridge_check_x", "video/webm");
    expect(c).toContain("training.compare_landmarks");
    expect(c).toContain("signbridge_check_x.webm");
    expect(c).toContain("signbridge_check_x.landmarks.json");
  });
});

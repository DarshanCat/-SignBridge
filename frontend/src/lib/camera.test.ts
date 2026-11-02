import { describe, expect, it } from "vitest";
import { aspectOf, cameraConstraintSets, cameraErrorMessage, openCamera, resolutionLabel } from "./camera";

describe("cameraErrorMessage", () => {
  it("explains denied permission", () => {
    expect(cameraErrorMessage(new DOMException("x", "NotAllowedError"))).toMatch(/permission/i);
  });
  it("explains a missing camera", () => {
    expect(cameraErrorMessage(new DOMException("x", "NotFoundError"))).toMatch(/no camera/i);
  });
  it("explains a busy camera", () => {
    expect(cameraErrorMessage(new DOMException("x", "NotReadableError"))).toMatch(/in use/i);
  });
  it("falls back to the error message", () => {
    expect(cameraErrorMessage(new Error("boom"))).toBe("boom");
  });
});

describe("camera constraints and fallback", () => {
  const stream = {} as MediaStream;

  it("asks for 1280x720 first and then for any camera", () => {
    const sets = cameraConstraintSets();
    expect(sets[0].video).toMatchObject({ width: { ideal: 1280 }, height: { ideal: 720 } });
    expect(sets[1].video).toBe(true);
  });

  it("uses the first set that works", async () => {
    const seen: MediaStreamConstraints[] = [];
    const s = await openCamera(async (c) => (seen.push(c), stream));
    expect(s).toBe(stream);
    expect(seen).toHaveLength(1);
  });

  it("falls back to whatever the camera gives when the preferred size is refused", async () => {
    let calls = 0;
    const s = await openCamera(async () => {
      if (calls++ === 0) throw new DOMException("x", "OverconstrainedError");
      return stream;
    });
    expect(s).toBe(stream);
    expect(calls).toBe(2);
  });

  it("does not retry after a permission error or a busy camera", async () => {
    for (const name of ["NotAllowedError", "NotReadableError"]) {
      let calls = 0;
      await expect(openCamera(async () => { calls++; throw new DOMException("x", name); })).rejects.toMatchObject({ name });
      expect(calls).toBe(1);
    }
  });

  it("reports the aspect of the real picture, 4:3 before it is known", () => {
    expect(aspectOf({ width: 1280, height: 720 })).toBeCloseTo(16 / 9);
    expect(aspectOf(null)).toBeCloseTo(4 / 3);
    expect(resolutionLabel({ width: 640, height: 480 })).toBe("640 x 480");
  });
});

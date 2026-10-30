import { describe, expect, it } from "vitest";
import { cameraErrorMessage } from "./camera";

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

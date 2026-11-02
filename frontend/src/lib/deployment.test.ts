import { describe, expect, it } from "vitest";
import { isOn } from "./deployment";
import { predictUrl } from "./predictSocket";

describe("deployment switches", () => {
  it("reads on values", () => {
    for (const v of ["1", "true", "TRUE", " yes ", "on"]) expect(isOn(v)).toBe(true);
    for (const v of ["0", "false", "", undefined, "no"]) expect(isOn(v)).toBe(false);
  });

  it("uses an explicit WebSocket URL when one is set, else derives it from the API URL", () => {
    expect(predictUrl("https://api.example.org", "wss://ws.example.org/ws/predict")).toBe("wss://ws.example.org/ws/predict");
    expect(predictUrl("https://api.example.org", "  ")).toBe("wss://api.example.org/ws/predict");
    expect(predictUrl("https://api.example.org", undefined)).toBe("wss://api.example.org/ws/predict");
  });
});

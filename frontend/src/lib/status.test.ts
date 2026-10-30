import { describe, expect, it } from "vitest";
import { buildStatusItems } from "./status";

const base = {
  backend: "connected" as const,
  webcam: "available" as const,
  animations: { count: 0, animations: [], message: "none", invalid: [] },
};

describe("buildStatusItems", () => {
  it("reports an untrained model honestly", () => {
    const items = buildStatusItems({
      ...base,
      model: { state: "not_trained", loaded: false, model_path: "", classes: 0, message: "m" },
    });
    expect(items.find((i) => i.id === "model")?.label).toBe("Model not trained");
  });

  it("reports landmarks ready only once the extractor has loaded", () => {
    const find = (extractor: "not_loaded" | "ready") =>
      buildStatusItems({ ...base, model: null, extractor }).find((i) => i.id === "landmarks");
    expect(find("not_loaded")?.level).toBe("warn");
    expect(find("ready")?.label).toBe("Landmark extraction ready");
  });

  it("flags an unreachable backend", () => {
    const items = buildStatusItems({ ...base, backend: "unreachable", model: null });
    expect(items[0].level).toBe("off");
  });

  it("reports animation unavailable when the registry is empty", () => {
    const items = buildStatusItems({ ...base, model: null });
    expect(items.find((i) => i.id === "anim")?.label).toBe("Animation unavailable");
  });
});

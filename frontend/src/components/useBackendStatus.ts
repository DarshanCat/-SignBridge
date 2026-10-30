"use client";
import { useEffect, useState } from "react";
import { apiGet, type AnimationRegistry, type HealthResponse, type ModelStatus } from "@/lib/api";
import type { StatusInput } from "@/lib/status";

export function useBackendStatus(): StatusInput {
  const [state, setState] = useState<StatusInput>({
    backend: "checking",
    model: null,
    animations: null,
    webcam: "unknown",
  });

  useEffect(() => {
    const ctl = new AbortController();
    (async () => {
      try {
        await apiGet<HealthResponse>("/api/health", ctl.signal);
        const [model, animations] = await Promise.all([
          apiGet<ModelStatus>("/api/model/status", ctl.signal),
          apiGet<AnimationRegistry>("/api/avatar/animations", ctl.signal),
        ]);
        setState((s) => ({ ...s, backend: "connected", model, animations }));
      } catch {
        if (!ctl.signal.aborted) setState((s) => ({ ...s, backend: "unreachable" }));
      }
    })();
    return () => ctl.abort();
  }, []);

  useEffect(() => {
    const devices = typeof navigator !== "undefined" ? navigator.mediaDevices : undefined;
    const detect = async (): Promise<"available" | "unavailable"> => {
      if (!devices?.enumerateDevices) return "unavailable";
      try {
        const list = await devices.enumerateDevices();
        return list.some((d) => d.kind === "videoinput") ? "available" : "unavailable";
      } catch {
        return "unavailable";
      }
    };
    void detect().then((webcam) => setState((s) => ({ ...s, webcam })));
  }, []);

  return state;
}

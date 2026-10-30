"use client";
import { useState } from "react";
import { EnglishToSignPanel } from "@/components/EnglishToSignPanel";
import { StatusPanel } from "@/components/StatusPanel";
import { useBackendStatus } from "@/components/useBackendStatus";
import { useLandmarkCapture } from "@/components/useLandmarkCapture";
import { WebcamPanel } from "@/components/WebcamPanel";
import { buildStatusItems } from "@/lib/status";

type Mode = "sign-to-english" | "english-to-sign";
const TABS: { id: Mode; label: string }[] = [
  { id: "sign-to-english", label: "Sign → English" },
  { id: "english-to-sign", label: "English → Sign" },
];

export default function Home() {
  const [mode, setMode] = useState<Mode>("sign-to-english");
  const status = useBackendStatus();
  const capture = useLandmarkCapture();

  return (
    <main className="mx-auto max-w-6xl px-4 py-8">
      <header className="mb-6">
        <h1 className="text-3xl font-bold tracking-tight">
          Sign<span className="text-accent">Bridge</span>
        </h1>
        <p className="mt-1 text-sm text-slate-400">
          Academic prototype: Indian Sign Language (ISL) and English with a 3D avatar. Not a complete
          natural-language ISL translator.
        </p>
      </header>

      <div role="tablist" aria-label="Translation mode" className="mb-4 flex gap-2">
        {TABS.map((t) => (
          <button
            key={t.id}
            role="tab"
            id={`tab-${t.id}`}
            aria-selected={mode === t.id}
            aria-controls={`panel-${t.id}`}
            onClick={() => setMode(t.id)}
            className={`rounded-lg px-4 py-2 text-sm font-medium transition ${
              mode === t.id ? "bg-accent text-ink" : "bg-panel text-slate-300 hover:bg-white/10"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className="grid gap-4 lg:grid-cols-[2fr_1fr]">
        <div role="tabpanel" id={`panel-${mode}`} aria-labelledby={`tab-${mode}`}>
          {mode === "sign-to-english" ? <WebcamPanel capture={capture} backendUp={status.backend === "connected"} modelLoaded={status.model?.loaded === true} /> : <EnglishToSignPanel backendUp={status.backend === "connected"} />}
        </div>
        <StatusPanel items={buildStatusItems({ ...status, extractor: capture.extractor })} />
      </div>
    </main>
  );
}

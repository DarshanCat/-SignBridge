"use client";
import { useEffect, useState } from "react";
import { API_URL } from "@/lib/api";
import { ConversationPanel } from "@/components/ConversationPanel";
import { EnglishToSignPanel } from "@/components/EnglishToSignPanel";
import { LandmarkCheckPanel } from "@/components/LandmarkCheckPanel";
import { RecordSignPanel } from "@/components/RecordSignPanel";
import { StatusPanel } from "@/components/StatusPanel";
import { useBackendStatus } from "@/components/useBackendStatus";
import { useLandmarkCapture } from "@/components/useLandmarkCapture";
import { WebcamPanel } from "@/components/WebcamPanel";
import { Footer } from "@/components/Footer";
import { RECORDING_DISABLED } from "@/lib/deployment";
import { buildStatusItems } from "@/lib/status";

type Mode = "conversation" | "sign-to-english" | "english-to-sign" | "record-sign" | "landmark-check";
const ALL_TABS: { id: Mode; label: string }[] = [
  { id: "conversation", label: "Conversation" },
  { id: "sign-to-english", label: "Sign → English" },
  { id: "english-to-sign", label: "English → Sign" },
  { id: "record-sign", label: "Record sign" },
  { id: "landmark-check", label: "Landmark check" },
];
// the public deployment has no recorder (NEXT_PUBLIC_DISABLE_RECORDING=1)
const TABS = ALL_TABS.filter((t) => !(RECORDING_DISABLED && t.id === "record-sign"));

export default function Home() {
  const [mode, setMode] = useState<Mode>("conversation");
  const status = useBackendStatus();
  const capture = useLandmarkCapture();
  const { preload } = capture;
  useEffect(() => {
    // load the landmark model while the user reads the page, so Start camera is instant
    if (mode === "english-to-sign") return;
    const t = setTimeout(preload, 800); // after first paint, not during it
    return () => clearTimeout(t);
  }, [mode, preload]);
  const backendUp = status.backend === "connected";

  return (
    <>
    <main className="mx-auto max-w-6xl px-4 py-6 sm:py-8">
      <header className="mb-6">
        <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">
          Sign<span className="text-accent">Bridge</span>
        </h1>
        <p className="mt-1 text-sm text-slate-400">
          Academic prototype: Indian Sign Language (ISL) and English with a 3D avatar. Not a complete
          natural-language ISL translator.
        </p>
      </header>

      {status.backend === "unreachable" && (
        <p role="alert" className="mb-4 rounded-lg bg-amber-400/15 p-3 text-sm text-amber-200">
          The backend is not reachable at {API_URL}. Recognition, text to gloss and recording need it. Start it with scripts\serve.ps1 (it takes about 15 seconds to start), then reload this page.
        </p>
      )}
      <div role="tablist" aria-label="Translation mode" className="mb-4 flex flex-wrap gap-2">
        {TABS.map((t) => (
          <button
            key={t.id}
            role="tab"
            id={`tab-${t.id}`}
            aria-selected={mode === t.id}
            aria-controls={`panel-${t.id}`}
            onClick={() => {
              capture.stop(); // the camera preview belongs to one tab at a time
              setMode(t.id);
            }}
            className={`min-h-11 rounded-lg px-4 py-2 text-sm font-medium transition ${
              mode === t.id ? "bg-accent text-ink" : "bg-panel text-slate-300 hover:bg-white/10"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className={`grid gap-4 ${mode === "conversation" ? "" : "lg:grid-cols-[2fr_1fr]"}`}>
        <div role="tabpanel" id={`panel-${mode}`} aria-labelledby={`tab-${mode}`}>
          {mode === "conversation" && <ConversationPanel capture={capture} backendUp={backendUp} />}
          {mode === "sign-to-english" && <WebcamPanel capture={capture} backendUp={backendUp} />}
          {mode === "english-to-sign" && <EnglishToSignPanel backendUp={backendUp} />}
          {mode === "record-sign" && !RECORDING_DISABLED && <RecordSignPanel capture={capture} backendUp={backendUp} />}
          {mode === "landmark-check" && <LandmarkCheckPanel capture={capture} />}
        </div>
        <StatusPanel items={buildStatusItems({ ...status, extractor: capture.extractor })} />
      </div>
    </main>
      <Footer />
    </>
  );
}

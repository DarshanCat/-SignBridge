"use client";
import { Flower2 } from "lucide-react";
import { useEffect, useRef, useState, type KeyboardEvent } from "react";
import { API_URL } from "@/lib/api";
import { ConversationPanel } from "@/components/ConversationPanel";
import { EnglishToSignPanel } from "@/components/EnglishToSignPanel";
import { KnownSignsPanel } from "@/components/KnownSignsPanel";
import { TestSentencesPanel } from "@/components/TestSentencesPanel";
import { LandmarkCheckPanel } from "@/components/LandmarkCheckPanel";
import { RecordSignPanel } from "@/components/RecordSignPanel";
import { StatusPanel } from "@/components/StatusPanel";
import { ThemeToggle } from "@/components/ThemeToggle";
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
  const tabRefs = useRef<Record<string, HTMLButtonElement | null>>({});
  useEffect(() => {
    // load the landmark model while the user reads the page, so Start camera is instant
    if (mode === "english-to-sign") return;
    const t = setTimeout(preload, 800); // after first paint, not during it
    return () => clearTimeout(t);
  }, [mode, preload]);
  const backendUp = status.backend === "connected";

  function select(id: Mode) {
    capture.stop(); // the camera preview belongs to one tab at a time
    setMode(id);
  }

  /** ARIA tabs pattern: arrow keys, Home and End move between tabs. */
  function onKeyDown(e: KeyboardEvent<HTMLDivElement>) {
    const i = TABS.findIndex((t) => t.id === mode);
    let n = -1;
    if (e.key === "ArrowRight") n = (i + 1) % TABS.length;
    else if (e.key === "ArrowLeft") n = (i + TABS.length - 1) % TABS.length;
    else if (e.key === "Home") n = 0;
    else if (e.key === "End") n = TABS.length - 1;
    if (n < 0) return;
    e.preventDefault();
    select(TABS[n].id);
    tabRefs.current[TABS[n].id]?.focus();
  }

  return (
    <>
      <div className="mx-auto max-w-[1360px] px-4 pb-4 pt-5 sm:px-8">
        <header className="flex flex-wrap items-center gap-x-6 gap-y-3">
          <h1 className="flex items-center gap-2.5 font-display text-2xl font-black tracking-tight sm:text-[28px]">
            <span aria-hidden className="grid h-9 w-9 place-items-center rounded-xl bg-accent text-onaccent" style={{ boxShadow: "0 6px 16px rgb(var(--accent) / 0.35)" }}>
              <Flower2 size={20} />
            </span>
            <span>
              Sign<span className="text-accent">Bridge</span>
            </span>
          </h1>
          <div className="order-last w-full overflow-x-auto pb-1 lg:order-none lg:w-auto">
            <div
              role="tablist"
              aria-label="Translation mode"
              onKeyDown={onKeyDown}
              className="inline-flex gap-1.5 rounded-full border border-line bg-surface p-1.5"
              style={{ boxShadow: "0 6px 20px rgb(var(--shadow-rgb) / 0.08)" }}
            >
              {TABS.map((t) => (
                <button
                  key={t.id}
                  ref={(el) => {
                    tabRefs.current[t.id] = el;
                  }}
                  role="tab"
                  id={`tab-${t.id}`}
                  aria-selected={mode === t.id}
                  aria-controls={`panel-${t.id}`}
                  tabIndex={mode === t.id ? 0 : -1}
                  onClick={() => select(t.id)}
                  className={`min-h-11 whitespace-nowrap rounded-full px-4 py-2 text-[15px] font-extrabold transition duration-200 ease-out sm:px-5 ${
                    mode === t.id ? "bg-accent text-onaccent" : "text-ink2 hover:bg-surface2 hover:text-ink"
                  }`}
                  style={mode === t.id ? { boxShadow: "0 6px 16px rgb(var(--accent) / 0.35)" } : undefined}
                >
                  {t.label}
                </button>
              ))}
            </div>
          </div>
          <div className="ml-auto flex items-center gap-2.5">
            <span className="hidden rounded-full border border-line bg-surface px-3.5 py-2 text-sm font-bold text-ink2 sm:inline-block">Research prototype</span>
            <ThemeToggle />
          </div>
          <p className="order-last w-full text-sm font-semibold text-ink2 lg:order-none">
            Academic prototype: Indian Sign Language (ISL) and English with an anime avatar. Not a complete natural-language ISL translator.
          </p>
        </header>

        <main id="main" tabIndex={-1} className="mt-5 outline-none">
          {status.backend === "unreachable" && (
            <p role="alert" className="notice notice-warn mb-4">
              The backend is not reachable at {API_URL}. Recognition, text to gloss and recording need it. Start it with scripts\serve.ps1 (it takes about 15 seconds to start), then reload this page.
            </p>
          )}
          <div key={mode} role="tabpanel" id={`panel-${mode}`} aria-labelledby={`tab-${mode}`} className="fade-up">
            {mode === "conversation" && <ConversationPanel capture={capture} backendUp={backendUp} />}
            {mode === "sign-to-english" && <WebcamPanel capture={capture} backendUp={backendUp} />}
            {mode === "english-to-sign" && (
              <>
                <EnglishToSignPanel backendUp={backendUp} />
                <TestSentencesPanel backendUp={backendUp} />
              </>
            )}
            {(mode === "conversation" || mode === "sign-to-english") && <KnownSignsPanel backendUp={backendUp} />}
            {mode === "record-sign" && !RECORDING_DISABLED && <RecordSignPanel capture={capture} backendUp={backendUp} />}
            {mode === "landmark-check" && <LandmarkCheckPanel capture={capture} />}
          </div>
          <div className="mt-6">
            <StatusPanel items={buildStatusItems({ ...status, extractor: capture.extractor })} />
          </div>
        </main>
      </div>
      <Footer />
    </>
  );
}

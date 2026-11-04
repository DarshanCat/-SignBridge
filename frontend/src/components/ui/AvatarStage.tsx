"use client";
import dynamic from "next/dynamic";
import { useCallback, useState, type ReactNode } from "react";
import type { SequencePlayer } from "@/lib/avatar/player";
import type { AvatarKind } from "@/components/avatar/GlbHumanoid";

const AvatarViewer = dynamic(() => import("@/components/avatar/AvatarViewer"), {
  ssr: false,
  loading: () => <p className="flex h-full items-center justify-center text-sm font-semibold text-ink2">Loading the avatar…</p>,
});

/** Decorative petals: position, size of the drift, duration and delay (all CSS variables; still when motion is reduced). */
const PETALS = [
  { left: "8%", y: "18%", r: "20deg", dx: "40px", t: "24s", d: "-3s" },
  { left: "22%", y: "62%", r: "-35deg", dx: "-30px", t: "30s", d: "-14s" },
  { left: "38%", y: "10%", r: "60deg", dx: "30px", t: "27s", d: "-9s" },
  { left: "63%", y: "30%", r: "10deg", dx: "-40px", t: "26s", d: "-18s" },
  { left: "80%", y: "12%", r: "-30deg", dx: "30px", t: "32s", d: "-6s" },
  { left: "92%", y: "48%", r: "50deg", dx: "-20px", t: "28s", d: "-21s" },
];

/**
 * The avatar as the visual centre of a tab: a rounded stage with a soft gradient (theme aware), the 3D avatar on a transparent canvas, badges at
 * the top and a caption card at the bottom that is always visible (the current sign, the sentence, status text).
 */
export function AvatarStage({
  player,
  onKind,
  badges,
  caption,
  className = "",
}: {
  player: SequencePlayer;
  onKind?: (k: AvatarKind) => void;
  badges?: ReactNode;
  caption: ReactNode;
  className?: string;
}) {
  const [loaded, setLoaded] = useState(false);
  const handleKind = useCallback(
    (k: AvatarKind) => {
      setLoaded(true);
      onKind?.(k);
    },
    [onKind],
  );
  return (
    <div className={`stage-bg relative isolate overflow-hidden rounded-[36px] border border-line ${className || "h-[500px] sm:h-[600px] lg:h-[680px]"}`} style={{ boxShadow: "0 18px 50px rgb(var(--shadow-rgb) / 0.14)" }}>
      <div aria-hidden className="absolute inset-0 z-0 overflow-hidden">
        {PETALS.map((p, i) => (
          <span key={i} className="petal" style={{ left: p.left, ["--y" as string]: p.y, ["--r" as string]: p.r, ["--dx" as string]: p.dx, ["--t" as string]: p.t, ["--d" as string]: p.d }} />
        ))}
      </div>
      <div className="absolute inset-0 z-[1]">
        <AvatarViewer player={player} onKind={handleKind} />
      </div>
      {!loaded && (
        <p role="status" className="absolute inset-x-0 top-1/3 z-[1] text-center font-display text-lg font-bold text-ink2">
          Loading the avatar…
        </p>
      )}
      {badges && <div className="absolute left-4 top-4 z-[2] flex max-w-[calc(100%-2rem)] flex-wrap gap-2">{badges}</div>}
      <div className="glass absolute inset-x-3 bottom-3 z-[2] rounded-3xl px-4 py-3 sm:inset-x-5 sm:bottom-5 sm:px-6 sm:py-4" style={{ boxShadow: "0 10px 30px rgb(var(--shadow-rgb) / 0.16)" }}>
        {caption}
      </div>
    </div>
  );
}

/** A pill on the stage (model name, honesty labels). */
export function StageBadge({ children, tone = "plain" }: { children: ReactNode; tone?: "plain" | "warn" }) {
  return <span className={`glass rounded-full px-3 py-1.5 text-xs font-bold sm:text-sm ${tone === "warn" ? "!bg-warnbg text-warnfg" : "text-ink2"}`}>{children}</span>;
}

/** Caption card content: the sign now playing in large type, the sentence below, and a progress bar over the signs of the sentence. */
export function StageCaption({ gloss, sentence, detail, progress, done }: { gloss?: ReactNode; sentence?: ReactNode; detail: ReactNode; progress?: number; done?: boolean }) {
  return (
    <div aria-live="polite">
      {gloss && <p className="font-display text-2xl font-black leading-tight tracking-wide text-ink sm:text-3xl">{gloss}</p>}
      {sentence && <p className="mt-0.5 text-base font-bold text-ink sm:text-lg">{sentence}</p>}
      <p className={`${gloss || sentence ? "mt-1" : ""} text-sm font-semibold text-ink2 sm:text-base`}>{detail}</p>
      {progress !== undefined && (
        <div className="mt-2.5 h-2 overflow-hidden rounded-full bg-soft" role="presentation">
          <div className="h-full rounded-full bg-accent transition-[width] duration-300 ease-out" style={{ width: `${Math.round((done ? 1 : progress) * 100)}%` }} />
        </div>
      )}
    </div>
  );
}

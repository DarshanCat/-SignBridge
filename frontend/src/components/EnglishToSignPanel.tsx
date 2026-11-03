"use client";
import { Pause, Play, RotateCcw, SkipBack, Square } from "lucide-react";
import dynamic from "next/dynamic";
import { useEffect, useState, useSyncExternalStore } from "react";
import { apiGet, apiPost, type AvatarPlan, type SignRegistry, type TextToGloss } from "@/lib/api";
import { SequencePlayer } from "@/lib/avatar/player";
import { loadPlaylist } from "@/lib/avatar/loader";
import { describeTokens, glossesToPlan, playOrder, type TokenView } from "@/lib/avatar/sentence";
import { RIG_TEST_CLIP } from "@/lib/avatar/rigTest";
import { shortcutHelp } from "@/lib/shortcuts";
import type { AvatarKind } from "./avatar/GlbHumanoid";
import { useShortcuts } from "./useShortcuts";

const AvatarViewer = dynamic(() => import("./avatar/AvatarViewer"), {
  ssr: false,
  loading: () => <p className="flex h-full items-center justify-center text-sm text-slate-400">Loading 3D scene…</p>,
});

interface Result {
  text: string;
  gloss: TextToGloss;
  views: TokenView[];
  plan: AvatarPlan | null;
  failed: string[];
}

export function EnglishToSignPanel({ backendUp }: { backendUp: boolean }) {
  const [player] = useState(() => new SequencePlayer());
  const snap = useSyncExternalStore(player.subscribe.bind(player), () => player.snapshot(), () => player.snapshot());
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<Result | null>(null);
  const [rigTest, setRigTest] = useState(false);
  const [registry, setRegistry] = useState<SignRegistry | null>(null);
  const [rate, setRate] = useState(1);
  const [ms, setMs] = useState<number | null>(null);
  const [stage, setStage] = useState<string | null>(null);
  const [kind, setKind] = useState<AvatarKind | null>(null);

  useEffect(() => () => player.dispose(), [player]);

  useEffect(() => {
    if (!backendUp) return;
    const ctl = new AbortController();
    apiGet<SignRegistry>("/api/avatar/registry", ctl.signal).then(setRegistry).catch(() => setRegistry(null));
    return () => ctl.abort();
  }, [backendUp]);

  const statusOf = (gloss: string) => registry?.signs.find((s) => s.gloss === gloss)?.status;

  useEffect(() => {
    player.setRate(rate);
  }, [player, rate]);

  async function translate() {
    setBusy(true);
    setError(null);
    setRigTest(false);
    setMs(null);
    player.load([]);
    const t0 = performance.now();
    try {
      setStage("Converting text to gloss");
      const gloss = await apiPost<TextToGloss>("/api/nlp/text-to-gloss", { text });
      if (gloss.tokens.length === 0) {
        setResult({ text, gloss, views: [], plan: null, failed: [] });
        return;
      }
      setStage("Looking up sign clips");
      const plan = await apiPost<AvatarPlan>("/api/avatar/plan", { gloss: glossesToPlan(gloss.tokens) });
      setStage(`Loading ${plan.steps.filter((x) => x.available).length} clip(s)`);
      const { clips, failed } = await loadPlaylist(plan.steps);
      const byGloss = new Map(clips.map((c) => [c.gloss.toUpperCase(), c]));
      const views = describeTokens(gloss.tokens, new Set(byGloss.keys()));
      player.load(playOrder(views).flatMap((g) => byGloss.get(g) ?? []));
      player.setNmm(gloss.nmm);
      setResult({ text, gloss, views, plan, failed });
      setMs(Math.round(performance.now() - t0));
    } catch (e) {
      setResult(null);
      setError(e instanceof Error ? e.message : "Translation failed.");
    } finally {
      setStage(null);
      setBusy(false);
    }
  }

  function runRigTest() {
    setResult(null);
    setRigTest(true);
    player.load([RIG_TEST_CLIP]);
    player.play();
  }

  const hasPlaylist = snap.total > 0;
  const playing = snap.status === "playing";
  useShortcuts({
    play: hasPlaylist ? () => (playing ? player.pause() : player.play()) : undefined,
    replay: hasPlaylist ? () => player.replay() : undefined,
  });
  const btn = "inline-flex items-center gap-2 rounded-lg bg-white/10 px-3 py-2 text-sm disabled:opacity-40";

  return (
    <section className="space-y-4" aria-label="English to sign">
      <div className="rounded-xl border border-white/10 bg-panel p-4">
        <h2 className="text-lg font-semibold">English to ISL Sign</h2>
        <form
          className="mt-3 flex flex-col gap-2 sm:flex-row"
          onSubmit={(e) => {
            e.preventDefault();
            void translate();
          }}
        >
          <label htmlFor="english-text" className="sr-only">
            English text
          </label>
          <input
            id="english-text"
            value={text}
            onChange={(e) => setText(e.target.value)}
            maxLength={500}
            placeholder="e.g. Hello, what is your name?"
            className="flex-1 rounded-lg border border-white/10 bg-ink px-3 py-2 text-sm"
          />
          <button
            type="submit"
            disabled={busy || !backendUp || !text.trim()}
            className="rounded-lg bg-accent px-4 py-2 text-sm font-medium text-ink disabled:opacity-50"
          >
            {busy ? "Translating…" : "Translate"}
          </button>
        </form>
        <div className="mt-2 flex flex-wrap items-center gap-1.5 text-xs text-slate-400">
          <span className="text-slate-500">Quick signs:</span>
          {["hello", "water", "doctor", "hospital", "book", "bed", "clean"].map((word) => (
            <button
              key={word}
              type="button"
              onClick={() => setText(word)}
              className="rounded bg-white/5 hover:bg-white/10 px-2 py-0.5 text-sky-300 border border-white/5 transition"
            >
              {word}
            </button>
          ))}
        </div>
        {busy && stage && (
          <p aria-live="polite" className="mt-2 flex items-center gap-2 text-xs text-sky-300">
            <span className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-sky-300 border-t-transparent" aria-hidden />
            {stage}…
          </p>
        )}
        {!backendUp && <p className="mt-2 text-xs text-amber-300">Backend unreachable: translation is unavailable.</p>}
        {error && (
          <p role="alert" className="mt-2 rounded-lg bg-rose-500/15 p-2 text-sm text-rose-200">
            {error}
          </p>
        )}

        {result && (
          <div className="mt-4 space-y-2 text-sm" aria-live="polite">
            <p className="text-xs text-slate-400">{result.gloss.note}</p>
            <p>
              <span className="text-slate-300">English:</span> “{result.text}”
            </p>
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-slate-300">Gloss:</span>
              {result.views.length === 0 && <span className="text-amber-300">No supported words found.</span>}
              {result.views.map((v, i) => {
                const verified = v.status === "clip" && statusOf(v.gloss) === "verified";
                const current = snap.status === "playing" && v.play.includes(snap.gloss ?? "");
                const tone =
                  v.status === "no_clip" ? "bg-amber-400/20 text-amber-200" : verified ? "bg-emerald-400/20 text-emerald-200" : "bg-sky-400/20 text-sky-200";
                return (
                  <span key={`${v.gloss}-${i}`} aria-current={current ? "true" : undefined} className={`rounded px-2 py-0.5 text-xs ${tone} ${current ? "ring-2 ring-accent" : ""}`}>
                    {v.label}
                    {v.status !== "no_clip" && !verified ? " (clip not signer-reviewed)" : ""}
                  </span>
                );
              })}
            </div>
            {result.gloss.nmm.length > 0 && (
              <p className="text-slate-300">
                Non-manual markers: {result.gloss.nmm.join(", ")}. Shown only as a small rule-based head movement (an approximation; no face is animated).
              </p>
            )}
            {result.views.some((v) => v.status === "no_clip") && (
              <p className="text-amber-300">
                No clip for: {result.views.filter((v) => v.status === "no_clip").map((v) => v.gloss).join(", ")}. These are skipped; no clip is faked.
              </p>
            )}
            {ms !== null && <p className="text-xs text-slate-500">Measured translate, plan and clip load: {ms} ms.</p>}
            {result.failed.length > 0 && <p className="text-rose-300">Clip failed to load or validate: {result.failed.join(", ")}.</p>}
          </div>
        )}
      </div>

      <div className="rounded-xl border border-white/10 bg-panel p-4">
        <div className="aspect-[4/3] overflow-hidden rounded-lg bg-black/60">
          <AvatarViewer player={player} onKind={setKind} />
        </div>
        <p aria-live="polite" className="mt-2 min-h-5 text-sm text-slate-300">
          {rigTest && "Rig self-test motion: not an ISL sign. "}
          {snap.status === "playing" && `Signing ${snap.gloss} (${snap.index + 1} of ${snap.total})${statusOf(snap.gloss ?? "") === "verified" ? "" : " - clip not signer-reviewed"}`}
          {snap.status === "paused" && `Paused at ${snap.gloss} (${snap.index + 1} of ${snap.total})${statusOf(snap.gloss ?? "") === "verified" ? "" : " - clip not signer-reviewed"}`}
          {snap.status === "finished" && "Finished."}
          {snap.status === "idle" && !hasPlaylist && "Nothing to play. The avatar only signs glosses that have an animation clip."}
          {snap.status === "idle" && hasPlaylist && "Ready."}
        </p>
        <div className="mt-2 flex flex-wrap items-center gap-2">
          <button className={btn} disabled={!hasPlaylist} onClick={() => (playing ? player.pause() : player.play())}>
            {playing ? <Pause size={16} aria-hidden /> : <Play size={16} aria-hidden />} {playing ? "Pause" : "Play"}
          </button>
          <button className={btn} disabled={!hasPlaylist} onClick={() => player.replay()}>
            <RotateCcw size={16} aria-hidden /> Replay sign
          </button>
          <button className={btn} disabled={!hasPlaylist} onClick={() => player.restart()}>
            <SkipBack size={16} aria-hidden /> Restart all
          </button>
          <button className={btn} disabled={!hasPlaylist || snap.status === "idle"} onClick={() => player.stop()}>
            <Square size={16} aria-hidden /> Stop
          </button>
          <label className="ml-auto flex items-center gap-2 text-xs text-slate-300">
            Speed
            <select value={rate} onChange={(e) => setRate(Number(e.target.value))} className="rounded bg-ink px-2 py-1">
              <option value={0.5}>0.5x</option>
              <option value={1}>1x</option>
              <option value={1.5}>1.5x</option>
            </select>
          </label>
        </div>
        <p className="mt-2 text-xs text-slate-500">Keyboard (when not typing): {shortcutHelp(["play", "replay"])}.</p>
        <p className="mt-2 text-xs text-slate-500">Avatar model: {kind === "glb" ? "Mixamo model from /avatar/signer.glb (terms not yet confirmed)" : kind === "procedural" ? "built in procedural humanoid (no signer.glb found or usable)" : "loading the 3D model…"}.</p>
        <button onClick={runRigTest} className="mt-3 text-xs text-slate-400 underline">
          Run rig self-test (a generic arm motion to check the avatar works; not a sign)
        </button>
      </div>

      <div className="rounded-xl border border-white/10 bg-panel p-4">
        <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-300">Supported vocabulary</h3>
        {!registry ? (
          <p className="mt-2 text-xs text-slate-400">Vocabulary status unavailable (backend unreachable or registry invalid).</p>
        ) : (
          <>
            <p className="mt-2 text-xs text-amber-300">
              {registry.totals.verified} verified, {registry.totals.clip_unreviewed} with an unreviewed clip, {registry.totals.no_clip} without
              any clip, of {registry.totals.signs} registered glosses. A sign is only verified after a visual check and ISL signer review.
            </p>
            {registry.unregistered_clips.length > 0 && (
              <p className="mt-1 text-xs text-rose-300">Clips not in the sign registry: {registry.unregistered_clips.join(", ")}</p>
            )}
            <ul className="mt-2 flex flex-wrap gap-2">
              {registry.signs.map((i) => (
                <li
                  key={i.gloss}
                  className={`rounded px-2 py-0.5 text-xs ${i.status === "verified" ? "bg-emerald-400/20 text-emerald-200" : i.status === "no_clip" ? "bg-white/5 text-slate-400" : "bg-amber-400/20 text-amber-200"}`}
                  title={i.problems.join("; ") || i.meaning}
                >
                  {i.gloss}
                  {i.status === "no_clip" ? " (no animation)" : i.status === "verified" ? "" : ` (${i.status.replace("_", " ")})`}
                </li>
              ))}
            </ul>
          </>
        )}
      </div>
    </section>
  );
}

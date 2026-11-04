"use client";
import { Pause, Play, RotateCcw, SkipBack, Square } from "lucide-react";
import { useEffect, useState, useSyncExternalStore } from "react";
import { apiGet, apiPost, type AvatarPlan, type SignRegistry, type TextToGloss } from "@/lib/api";
import { DEFAULT_SIGN_RATE, SequencePlayer } from "@/lib/avatar/player";
import { loadPlaylist } from "@/lib/avatar/loader";
import { describeTokens, glossesToPlan, playOrder, type TokenView } from "@/lib/avatar/sentence";
import { RIG_TEST_CLIP } from "@/lib/avatar/rigTest";
import { shortcutHelp } from "@/lib/shortcuts";
import type { AvatarKind } from "./avatar/GlbHumanoid";
import { AvatarStage, StageBadge, StageCaption } from "./ui/AvatarStage";
import { SourceSkeleton } from "./ui/SourceSkeleton";
import { SpeedControl } from "./ui/SpeedControl";
import { useShortcuts } from "./useShortcuts";

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
  const [rate, setRate] = useState(DEFAULT_SIGN_RATE);
  const [ms, setMs] = useState<number | null>(null);
  const [stage, setStage] = useState<string | null>(null);
  const [kind, setKind] = useState<AvatarKind | null>(null);
  const [showSource, setShowSource] = useState(false);

  useEffect(() => () => player.dispose(), [player]);

  // ?debug-player in the address exposes the player (window.__sbPlayer) so a sign can be stepped to an exact moment (screenshots, checks)
  useEffect(() => {
    if (new URLSearchParams(window.location.search).has("debug-player")) (window as unknown as { __sbPlayer?: SequencePlayer }).__sbPlayer = player;
  }, [player]);

  useEffect(() => {
    if (!backendUp) return;
    const ctl = new AbortController();
    apiGet<SignRegistry>("/api/avatar/registry", ctl.signal).then(setRegistry).catch(() => {
      if (!ctl.signal.aborted) setRegistry(null); // an aborted request is a superseded one, not a failure
    });
    return () => ctl.abort();
  }, [backendUp]);

  const statusOf = (gloss: string) => registry?.signs?.find((s) => s.gloss === gloss)?.status;

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
  const verifiedNow = statusOf(snap.gloss ?? "") === "verified";
  const reviewNote = verifiedNow ? "" : " · clip not signer-reviewed";
  const progress = snap.total ? (snap.index + (snap.status === "playing" || snap.status === "paused" ? 0.5 : 0)) / snap.total : 0;
  const avatarLabel = kind === "vrm" ? "Avatar: anime (VRM)" : kind === "glb" ? "Avatar: Mixamo model" : kind === "procedural" ? "Avatar: built-in figure" : "Avatar: loading";

  const captionNode =
    snap.status === "playing" || snap.status === "paused" ? (
      <StageCaption
        gloss={snap.gloss}
        sentence={result ? `“${result.text}”` : undefined}
        detail={`${snap.status === "paused" ? "Paused at" : "Signing"} ${snap.index + 1} of ${snap.total}${rigTest ? " · rig self-test motion, not an ISL sign" : reviewNote}`}
        progress={progress}
      />
    ) : snap.status === "finished" ? (
      <StageCaption sentence={result ? `“${result.text}”` : undefined} detail="Finished." progress={1} done />
    ) : hasPlaylist ? (
      <StageCaption sentence={result ? `“${result.text}”` : undefined} detail="Ready. Press Play to see it signed." progress={0} />
    ) : (
      <StageCaption detail="Nothing to play. The avatar only signs glosses that have an animation clip." />
    );

  return (
    <section className="grid gap-6 lg:grid-cols-[minmax(0,1.6fr)_minmax(0,1fr)]" aria-label="English to sign">
      <div className="space-y-4 lg:order-1">
        <AvatarStage
          player={player}
          onKind={setKind}
          badges={
            <>
              <StageBadge>{avatarLabel}</StageBadge>
              <StageBadge tone="warn">Clip not signer-reviewed</StageBadge>
            </>
          }
          caption={captionNode}
          overlay={showSource ? <SourceSkeleton player={player} /> : undefined}
        />
        <div className="flex flex-wrap items-center gap-3" role="group" aria-label="Playback">
          <button className="btn btn-primary" disabled={!hasPlaylist} onClick={() => (playing ? player.pause() : player.play())}>
            {playing ? <Pause size={18} aria-hidden /> : <Play size={18} aria-hidden />} {playing ? "Pause" : "Play"}
          </button>
          <button className="btn" disabled={!hasPlaylist} onClick={() => player.replay()}>
            <RotateCcw size={18} aria-hidden /> Replay sign
          </button>
          <button className="btn" disabled={!hasPlaylist} onClick={() => player.restart()}>
            <SkipBack size={18} aria-hidden /> Restart all
          </button>
          <button className="btn" disabled={!hasPlaylist || snap.status === "idle"} onClick={() => player.stop()}>
            <Square size={18} aria-hidden /> Stop
          </button>
          <button className="btn" aria-pressed={showSource} onClick={() => setShowSource((v) => !v)}>
            {showSource ? "Hide source skeleton" : "Show source skeleton"}
          </button>
          <div className="ml-auto">
            <SpeedControl rate={rate} onChange={setRate} />
          </div>
        </div>
        <p className="text-sm font-semibold text-ink2">Keyboard (when not typing): {shortcutHelp(["play", "replay"])}.</p>
        <p className="text-sm font-semibold text-ink2">
          Avatar model:{" "}
          {kind === "vrm"
            ? "anime model (VRM) from /avatar/signer.vrm; the face, blinking and head markers are rule-based approximations, not signer reviewed"
            : kind === "glb"
              ? "Mixamo model from /avatar/signer.glb (terms not yet confirmed)"
              : kind === "procedural"
                ? "built in procedural humanoid (no signer.vrm or signer.glb found or usable)"
                : "loading the 3D model…"}
          .
        </p>
        <button onClick={runRigTest} className="text-sm font-bold text-ink2 underline underline-offset-4 hover:text-ink">
          Run rig self-test (a generic arm motion to check the avatar works; not a sign)
        </button>
      </div>

      <div className="space-y-4 lg:order-2">
        <div className="card">
          <h2 className="card-title">English to ISL Sign</h2>
          <p className="mt-1 text-sm font-semibold text-ink2">Type a short sentence. Simplified rules, not validated by ISL signers.</p>
          <form
            className="mt-4 flex flex-col gap-3 sm:flex-row"
            onSubmit={(e) => {
              e.preventDefault();
              void translate();
            }}
          >
            <label htmlFor="english-text" className="sr-only">
              English text
            </label>
            <input id="english-text" value={text} onChange={(e) => setText(e.target.value)} maxLength={500} placeholder="e.g. Hello, what is your name?" className="input flex-1" />
            <button type="submit" disabled={busy || !backendUp || !text.trim()} className="btn btn-primary">
              {busy ? "Translating…" : "Translate"}
            </button>
          </form>
          <div className="mt-3 flex flex-wrap items-center gap-2 text-sm font-bold text-ink2">
            <span>Quick signs:</span>
            {["hello", "doctor", "hospital", "book", "bed", "clean"].map((word) => (
              <button key={word} type="button" onClick={() => setText(word)} className="chip min-h-11">
                {word}
              </button>
            ))}
          </div>
          {busy && stage && (
            <p aria-live="polite" className="mt-3 flex items-center gap-2 text-sm font-bold text-infofg">
              <span className="inline-block h-3.5 w-3.5 animate-spin rounded-full border-2 border-infofg border-t-transparent" aria-hidden />
              {stage}…
            </p>
          )}
          {!backendUp && <p className="notice notice-warn mt-3">Backend unreachable: translation is unavailable.</p>}
          {error && (
            <p role="alert" className="notice notice-bad mt-3">
              {error}
            </p>
          )}

          {result && (
            <div className="mt-5 space-y-3 text-sm" aria-live="polite">
              <p className="text-sm font-semibold text-ink2">{result.gloss.note}</p>
              <p className="text-base font-bold">
                <span className="text-ink2">English:</span> “{result.text}”
              </p>
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-bold text-ink2">Gloss:</span>
                {result.views.length === 0 && <span className="font-bold text-warnfg">No supported words found.</span>}
                {result.views.map((v, i) => {
                  const verified = v.status === "clip" && statusOf(v.gloss) === "verified";
                  const current = snap.status === "playing" && v.play.includes(snap.gloss ?? "");
                  const tone = v.status === "no_clip" ? "tag-warn" : verified ? "tag-good" : "tag-info";
                  return (
                    <span key={`${v.gloss}-${i}`} aria-current={current ? "true" : undefined} className={`tag ${tone} !px-3 !py-1 !text-sm ${current ? "ring-2 ring-lav ring-offset-2 ring-offset-surface" : ""}`}>
                      {v.label}
                      {v.status !== "no_clip" && !verified ? " (clip not signer-reviewed)" : ""}
                    </span>
                  );
                })}
              </div>
              {result.gloss.nmm.length > 0 && (
                <p className="font-semibold text-ink2">
                  Non-manual markers: {result.gloss.nmm.join(", ")}.{" "}
                  {kind === "vrm"
                    ? "Shown as a small rule-based head movement and a mild facial expression (approximations, not signer-validated)."
                    : "Shown only as a small rule-based head movement (an approximation; no face is animated)."}
                </p>
              )}
              {result.views.some((v) => v.status === "no_clip") && (
                <p className="notice notice-warn">
                  No clip for: {result.views.filter((v) => v.status === "no_clip").map((v) => v.gloss).join(", ")}. These are skipped; no clip is faked.
                </p>
              )}
              {ms !== null && <p className="text-sm font-semibold text-ink2">Measured translate, plan and clip load: {ms} ms.</p>}
              {result.failed.length > 0 && <p className="notice notice-bad">Clip failed to load or validate: {result.failed.join(", ")}.</p>}
            </div>
          )}
        </div>

        <div className="card">
          <h3 className="eyebrow">Supported vocabulary</h3>
          {!registry ? (
            <p className="mt-2 text-sm font-semibold text-ink2">Vocabulary status unavailable (backend unreachable or registry invalid).</p>
          ) : (
            <>
              <p className="notice notice-warn mt-3">
                {registry.totals?.verified ?? 0} verified, {registry.totals?.clip_unreviewed ?? 0} with an unreviewed clip, {registry.totals?.no_clip ?? 0} without
                any clip, of {registry.totals?.signs ?? (registry.signs?.length || 0)} registered glosses. A sign is only verified after a visual check and ISL signer review.
              </p>
              {Array.isArray(registry.unregistered_clips) && registry.unregistered_clips.length > 0 && (
                <p className="notice notice-bad mt-2">Clips not in the sign registry: {registry.unregistered_clips.join(", ")}</p>
              )}
              <details className="group mt-3">
                <summary className="btn btn-sm w-full cursor-pointer list-none justify-between">
                  <span>Show all {registry.signs?.length ?? 0} glosses</span>
                  <span aria-hidden className="transition group-open:rotate-180">
                    ▾
                  </span>
                </summary>
                <ul className="mt-3 flex max-h-72 flex-wrap gap-2 overflow-y-auto pr-1">
                  {(registry.signs ?? []).map((i) => (
                    <li
                      key={i.gloss}
                      className={`tag ${i.status === "verified" ? "tag-good" : i.status === "no_clip" ? "bg-surface2 text-ink2" : "tag-warn"}`}
                      title={(Array.isArray(i.problems) ? i.problems.join("; ") : "") || i.meaning}
                    >
                      {i.gloss}
                      {i.status === "no_clip" ? " (no animation)" : i.status === "verified" ? "" : ` (${String(i.status || "").replace("_", " ")})`}
                    </li>
                  ))}
                </ul>
              </details>
            </>
          )}
        </div>
      </div>
    </section>
  );
}

"use client";
import { cameraBoxStyle, FramingGuide } from "./CameraFrame";
import { Camera, CameraOff, Eraser, Pause, Play, RotateCcw, Send, Undo2 } from "lucide-react";
import { useEffect, useRef, useState, useSyncExternalStore } from "react";
import { apiPost, type AvatarPlan, type TextToGloss } from "@/lib/api";
import { DEFAULT_SIGN_RATE, SequencePlayer } from "@/lib/avatar/player";
import type { SignClip } from "@/lib/avatar/clip";
import { textToClips } from "@/lib/avatar/pipeline";
import { appendMessage, MAX_TYPED_LENGTH, signedMessage, signingSummary, typedMessage, type ChatMessage } from "@/lib/conversation";
import { shortcutHelp } from "@/lib/shortcuts";
import { CaptureHints } from "./CaptureHints";
import type { LandmarkCapture } from "./useLandmarkCapture";
import { useContinuousSigning } from "./useContinuousSigning";
import { AvatarStage, StageBadge, StageCaption } from "./ui/AvatarStage";
import { SourceSkeleton } from "./ui/SourceSkeleton";
import type { AvatarKind } from "./avatar/GlbHumanoid";
import { useShortcuts } from "./useShortcuts";

const AUTO_SEND_MS = 3000;
const btn = "btn btn-sm";

/**
 * One screen for both directions. The deaf user signs in front of the camera: recognized signs build a sentence that is sent as a message.
 * The hearing user types: the message is converted to gloss, the avatar signs it, and the text stays in the chat. Words without a clip
 * are listed under the message, never faked.
 */
export function ConversationPanel({ capture, backendUp }: { capture: LandmarkCapture; backendUp: boolean }) {
  const { state, error: cameraError, videoRef, canvasRef, start, stop } = capture;
  const running = state === "running";
  const [player] = useState(() => {
    const p = new SequencePlayer();
    p.setRate(DEFAULT_SIGN_RATE);
    return p;
  });
  const [showSource, setShowSource] = useState(false);
  const snap = useSyncExternalStore(player.subscribe.bind(player), () => player.snapshot(), () => player.snapshot());
  const live = useContinuousSigning(capture, true);
  const [log, setLog] = useState<ChatMessage[]>([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [typedError, setTypedError] = useState<string | null>(null);
  const [autoSend, setAutoSend] = useState(false);
  const nextId = useRef(1);
  const [last, setLast] = useState<{ clips: SignClip[]; nmm: string[]; text: string } | null>(null);
  const [avatarKind, setAvatarKind] = useState<AvatarKind | null>(null);
  const logEnd = useRef<HTMLDivElement>(null);

  useEffect(() => () => player.dispose(), [player]);
  useEffect(() => {
    logEnd.current?.scrollIntoView?.({ block: "nearest" });
  }, [log.length]);

  const sentence = live.english.trim();
  const canSendSigned = live.sequence.length > 0 && sentence !== "";

  function sendSigned() {
    const m = signedMessage(nextId.current, live.english, live.sequence, Date.now());
    if (!m) return;
    nextId.current += 1;
    setLog((l) => appendMessage(l, m));
    live.clear();
  }

  useEffect(() => {
    if (!autoSend || live.signing || !canSendSigned) return;
    const t = setTimeout(sendSigned, AUTO_SEND_MS);
    return () => clearTimeout(t);
    // sendSigned reads the latest sentence through the values listed here
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoSend, live.signing, canSendSigned, live.sequence.length, live.english]);

  async function sendTyped() {
    const input = text.trim();
    if (!input || busy) return;
    setBusy("Starting");
    setTypedError(null);
    try {
      const out = await textToClips(input, {
        textToGloss: (t) => apiPost<TextToGloss>("/api/nlp/text-to-gloss", { text: t }),
        plan: (g) => apiPost<AvatarPlan>("/api/avatar/plan", { gloss: g }),
        onStage: setBusy,
      });
      const m = typedMessage(nextId.current, input, out.gloss.gloss, out.views, out.clips.length, Date.now());
      if (!m) return;
      nextId.current += 1;
      setLog((l) => appendMessage(l, m));
      setText("");
      setLast({ clips: out.clips, nmm: out.gloss.nmm, text: input });
      player.load(out.clips);
      player.setNmm(out.gloss.nmm);
      if (out.clips.length) player.play();
    } catch (e) {
      setTypedError(e instanceof Error ? e.message : "Could not convert the message.");
    } finally {
      setBusy(null);
    }
  }

  function replayLast() {
    if (!last?.clips.length) return;
    player.load(last.clips);
    player.setNmm(last.nmm);
    player.play();
  }
  function playPause() {
    if (snap.status === "playing") player.pause();
    else if (snap.total) player.play();
    else replayLast();
  }

  useShortcuts({
    send: canSendSigned ? sendSigned : undefined,
    undo: live.sequence.length ? live.undo : undefined,
    clear: live.sequence.length || log.length ? live.clear : undefined,
    play: playPause,
    replay: replayLast,
  });

  const modelMissing = live.channel.kind === "model_not_trained";
  const channelDown = running && live.channel.kind === "unavailable";

  const reviewNote = " · clip not signer-reviewed";
  const progress = snap.total ? (snap.index + (snap.status === "playing" || snap.status === "paused" ? 0.5 : 0)) / snap.total : 0;
  const lastText = last?.text ? `“${last.text}”` : undefined;
  const captionNode =
    snap.status === "playing" || snap.status === "paused" ? (
      <StageCaption gloss={snap.gloss} sentence={lastText} detail={`${snap.status === "paused" ? "Paused at" : "Signing"} ${snap.index + 1} of ${snap.total}${reviewNote}`} progress={progress} />
    ) : snap.status === "finished" ? (
      <StageCaption sentence={lastText} detail="Finished." progress={1} done />
    ) : (
      <StageCaption detail="Type a message to see it signed." />
    );

  return (
    <section className="grid gap-6 lg:grid-cols-[minmax(0,1.5fr)_minmax(0,1fr)]" aria-label="Conversation">
      <div className="space-y-4 lg:sticky lg:top-4 lg:self-start">
        <h2 className="eyebrow">Avatar (signs typed messages)</h2>
        <AvatarStage
          player={player}
          onKind={setAvatarKind}
          badges={
            <>
              <StageBadge>{avatarKind === "vrm" ? "Avatar: anime (VRM)" : avatarKind === "glb" ? "Avatar: Mixamo model" : avatarKind === "procedural" ? "Avatar: built-in figure" : "Avatar: loading"}</StageBadge>
              <StageBadge tone="warn">Clip not signer-reviewed</StageBadge>
            </>
          }
          caption={captionNode}
          overlay={showSource ? <SourceSkeleton player={player} /> : undefined}
        />
        <div className="flex flex-wrap items-center gap-3" role="group" aria-label="Playback">
          <button className="btn btn-primary" onClick={playPause} disabled={!snap.total && !last}>
            {snap.status === "playing" ? <Pause size={18} aria-hidden /> : <Play size={18} aria-hidden />} {snap.status === "playing" ? "Pause" : "Play"}
          </button>
          <button className="btn" onClick={replayLast} disabled={!last?.clips.length}>
            <RotateCcw size={18} aria-hidden /> Replay
          </button>
          <button className="btn" aria-pressed={showSource} onClick={() => setShowSource((v) => !v)}>
            {showSource ? "Hide source skeleton" : "Show source skeleton"}
          </button>
        </div>
        <p className="text-sm font-semibold text-ink2">Keyboard (when not typing): {shortcutHelp(["send", "undo", "clear", "play", "replay"])}.</p>
      </div>

      <div className="space-y-4">
        <div className="card">
            <h2 className="card-title">Conversation</h2>
            <div role="log" aria-live="polite" aria-label="Messages" className="mt-3 max-h-80 min-h-40 space-y-2 overflow-y-auto rounded-2xl bg-surface2 p-3">
              {log.length === 0 && <p className="text-sm text-ink2">No messages yet. Sign to the camera, or type a message below.</p>}
              {log.map((m) => (
                <div key={m.id} className={`flex ${m.from === "signer" ? "justify-start" : "justify-end"}`}>
                  <div className={`max-w-[85%] rounded-2xl px-3 py-2 text-sm ${m.from === "signer" ? "bg-infobg text-infofg" : "bg-goodbg text-goodfg"}`}>
                    <p className="text-[11px] uppercase tracking-wide text-ink2">{m.from === "signer" ? "Signed" : "Typed, signed by the avatar"}</p>
                    <p className="mt-0.5 break-words text-base">{m.text}</p>
                    <p className="mt-1 break-words text-sm text-ink2">Gloss: {m.gloss.join(" ") || "none"}</p>
                    {m.from === "typist" && <p className={`text-sm ${m.notSigned.length ? "text-warnfg" : "text-ink2"}`}>{signingSummary(m)}</p>}
                  </div>
                </div>
              ))}
              <div ref={logEnd} />
            </div>

            <form
              className="mt-3 flex gap-2"
              onSubmit={(e) => {
                e.preventDefault();
                void sendTyped();
              }}
            >
              <label htmlFor="chat-text" className="sr-only">
                Message to sign
              </label>
              <input
                id="chat-text"
                value={text}
                onChange={(e) => setText(e.target.value)}
                maxLength={MAX_TYPED_LENGTH}
                placeholder="Type a message for the avatar to sign"
                className="input flex-1"
              />
              <button type="submit" disabled={!backendUp || !!busy || !text.trim()} className="btn btn-primary">
                <Send size={16} aria-hidden /> {busy ? `${busy}…` : "Send"}
              </button>
            </form>
            <div className="mt-2 flex flex-wrap items-center gap-1.5 text-sm text-ink2">
              <span className="text-ink2">Quick signs:</span>
              {["hello", "doctor", "hospital", "book", "bed", "clean"].map((word) => (
                <button
                  key={word}
                  type="button"
                  onClick={() => setText(word)}
                  className="chip min-h-11"
                >
                  {word}
                </button>
              ))}
            </div>
            {typedError && (
              <p role="alert" className="mt-2 notice notice-bad">
                {typedError}
              </p>
            )}
          </div>

        <div className="card">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h3 className="eyebrow">Signing (deaf user)</h3>
              <button onClick={running ? stop : start} disabled={state === "starting"} className={btn}>
                {running ? <CameraOff size={16} aria-hidden /> : <Camera size={16} aria-hidden />}
                {state === "starting" ? "Starting…" : running ? "Stop camera" : "Start camera"}
              </button>
            </div>
            <div className="relative mx-auto mt-3 max-w-3xl overflow-hidden rounded-3xl border border-edge/50 bg-cam text-camfg" style={cameraBoxStyle(capture.resolution)}>
              <video ref={videoRef} playsInline muted className="h-full w-full object-cover" aria-label="Webcam preview" />
              <canvas ref={canvasRef} width={capture.resolution?.width ?? 640} height={capture.resolution?.height ?? 480} className="pointer-events-none absolute inset-0 h-full w-full" />
              <FramingGuide capture={capture} />
              {!running && <p className="absolute inset-0 flex items-center justify-center p-4 text-center text-sm text-camfg">{state === "starting" ? "Waiting for camera…" : "Camera is off. Video stays in your browser; only landmarks are sent."}</p>}
            </div>
            <CaptureHints capture={capture} />
            {cameraError && (
              <p role="alert" className="mt-2 notice notice-bad">
                {cameraError}
              </p>
            )}
            {modelMissing && <p className="mt-2 notice notice-warn">Model not trained: signs cannot be recognized. Typed messages still work.</p>}
            {channelDown && <p className="mt-2 notice notice-warn">{live.channel.kind === "unavailable" ? live.channel.message : ""} The live recognition channel is down; is the backend running?</p>}
            {live.error && <p className="mt-2 text-sm text-badfg">{live.error}</p>}

            {live.ready && (
              <div className="mt-3 space-y-2" aria-live="polite">
                <p className={`text-sm ${live.signing ? "text-goodfg" : "text-ink2"}`}>{live.signing ? "Signing…" : "Resting. Sign now, then lower your hands between signs."}</p>
                <div className="flex flex-wrap gap-2">
                  {live.sequence.map((g, i) => (
                    <span key={`${g}-${i}`} className="tag tag-info !px-3 !py-1 !text-sm">
                      {g}
                    </span>
                  ))}
                  {live.sequence.length === 0 && <span className="text-sm text-ink2">No signs yet.</span>}
                </div>
                {sentence && <p className="text-base font-medium">{sentence}</p>}
                <div className="flex flex-wrap gap-2">
                  <button className="btn btn-primary" onClick={sendSigned} disabled={!canSendSigned}>
                    <Send size={16} aria-hidden /> Send signed sentence
                  </button>
                  <button className={btn} onClick={live.undo} disabled={!live.sequence.length}>
                    <Undo2 size={16} aria-hidden /> Undo last sign
                  </button>
                  <button className={btn} onClick={live.clear} disabled={!live.sequence.length}>
                    <Eraser size={16} aria-hidden /> Clear
                  </button>
                </div>
                <label className="flex items-center gap-2 text-sm text-ink2">
                  <input type="checkbox" checked={autoSend} onChange={(e) => setAutoSend(e.target.checked)} />
                  Send automatically after {AUTO_SEND_MS / 1000} s of rest
                </label>
                {live.log.length > 0 && (
                  <ul className="text-sm text-ink2" aria-label="Recent signs">
                    {live.log.map((e) => (
                      <li key={e.id} className={e.accepted ? "text-ink2" : "text-warnfg"}>
                        {e.text}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}
          </div>
      </div>
    </section>
  );
}

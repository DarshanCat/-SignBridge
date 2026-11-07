"use client";
import { Pause, Play, RotateCcw } from "lucide-react";
import { useEffect, useMemo, useState, useSyncExternalStore } from "react";
import { API_URL, apiGet, type AnimationRegistry } from "@/lib/api";
import { loadPlaylist } from "@/lib/avatar/loader";
import { DEFAULT_SIGN_RATE, SequencePlayer } from "@/lib/avatar/player";
import {
  CLARITY_LABELS, MAX_COMMENT, filterClips, isValidReviewer, nextUnreviewed, validateReview,
  type MineResponse, type ReviewRecord, type Verdict,
} from "@/lib/review";
import { AvatarStage, StageBadge, StageCaption } from "./ui/AvatarStage";
import { SourceSkeleton } from "./ui/SourceSkeleton";
import { SpeedControl } from "./ui/SpeedControl";

const ID_KEY = "signbridge.reviewerId";

function remembered(): string {
  try {
    return window.localStorage.getItem(ID_KEY) ?? "";
  } catch {
    return ""; // private window or blocked storage: the page works without it
  }
}

async function submitReview(body: object): Promise<ReviewRecord> {
  const res = await fetch(`${API_URL}/api/review/submit`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  const data = (await res.json().catch(() => null)) as { detail?: unknown } | null;
  if (!res.ok) throw new Error(typeof data?.detail === "string" ? data.detail : `The review could not be saved (HTTP ${res.status}).`);
  return data as unknown as ReviewRecord;
}

/**
 * Signer review: a signer watches each avatar clip, rates its clarity (1 to 5), marks it correct or wrong and may comment. The record is saved on this
 * computer under the reviewer's ID. This page is the only thing that creates a review; it changes no clip, no label and no flag by itself.
 */
export function ReviewPanel({ backendUp }: { backendUp: boolean }) {
  const [player] = useState(() => new SequencePlayer());
  const snap = useSyncExternalStore(player.subscribe.bind(player), () => player.snapshot(), () => player.snapshot());
  const [reviewerId, setReviewerId] = useState(remembered); // this tab is only rendered after a click, never on the server
  const [glosses, setGlosses] = useState<string[]>([]);
  const [urls, setUrls] = useState<Record<string, string>>({});
  const [mineRaw, setMine] = useState<ReviewRecord[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [onlyUnreviewed, setOnlyUnreviewed] = useState(false);
  const [clarity, setClarity] = useState<number | null>(null);
  const [verdict, setVerdict] = useState<Verdict | null>(null);
  const [comment, setComment] = useState("");
  const [rate, setRate] = useState(DEFAULT_SIGN_RATE);
  const [showSource, setShowSource] = useState(false);
  const [problems, setProblems] = useState<string[]>([]);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => () => player.dispose(), [player]);
  useEffect(() => player.setRate(rate), [player, rate]);

  useEffect(() => {
    if (!backendUp) return;
    const ctl = new AbortController();
    apiGet<AnimationRegistry>("/api/avatar/animations", ctl.signal)
      .then((r) => {
        setGlosses(r.animations.map((a) => a.gloss));
        setUrls(Object.fromEntries(r.animations.map((a) => [a.gloss, a.clip_url])));
      })
      .catch(() => {
        if (!ctl.signal.aborted) setError("The list of clips could not be loaded.");
      });
    return () => ctl.abort();
  }, [backendUp]);

  useEffect(() => {
    if (!backendUp || !isValidReviewer(reviewerId)) return;
    let live = true;
    apiGet<MineResponse>(`/api/review/mine?reviewer_id=${encodeURIComponent(reviewerId.trim())}`)
      .then((r) => live && setMine(r.reviews))
      .catch(() => live && setMine([]));
    return () => {
      live = false;
    };
  }, [backendUp, reviewerId]);
  const mine = useMemo(() => (isValidReviewer(reviewerId) ? mineRaw : []), [reviewerId, mineRaw]); // no valid ID: no marks are shown

  // choosing a sign loads its clip and plays it
  useEffect(() => {
    if (!selected || !urls[selected]) return;
    let live = true;
    void loadPlaylist([{ gloss: selected, available: true, clip_url: urls[selected] }]).then(({ clips }) => {
      if (!live) return;
      player.load(clips);
      player.play();
    });
    return () => {
      live = false;
    };
  }, [selected, urls, player]);

  const rows = useMemo(() => filterClips(glosses, mine, query, onlyUnreviewed), [glosses, mine, query, onlyUnreviewed]);
  const previous = mine.find((r) => r.gloss === selected) ?? null;

  function choose(gloss: string) {
    setSelected(gloss);
    setMessage(null);
    setProblems([]);
    const earlier = mine.find((r) => r.gloss === gloss);
    setClarity(earlier?.clarity ?? null);
    setVerdict(earlier?.verdict ?? null);
    setComment(earlier?.comment ?? "");
  }

  async function save() {
    const p = validateReview({ reviewerId, gloss: selected, clarity, verdict, comment });
    setProblems(p);
    setError(null);
    if (p.length) return;
    setBusy(true);
    try {
      await submitReview({ reviewer_id: reviewerId.trim(), gloss: selected, clarity, verdict, comment });
      try {
        window.localStorage.setItem(ID_KEY, reviewerId.trim());
      } catch {
        /* optional convenience */
      }
      const updated: ReviewRecord = {
        reviewer_id: reviewerId.trim().toUpperCase(), gloss: selected!, clarity: clarity!, verdict: verdict!, comment: comment.trim(),
        reviewed_at_utc: new Date().toISOString(), clip_sha256: null,
      };
      const after = [...mine.filter((r) => r.gloss !== selected), updated];
      setMine(after);
      const next = nextUnreviewed(glosses, after, selected);
      if (next) choose(next); // clears the form and the message for the next sign, so the confirmation is set after it
      setMessage(next ? `Saved. Next sign to review: ${next}.` : "Saved. You have reviewed every sign.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "The review could not be saved.");
    } finally {
      setBusy(false);
    }
  }

  const playing = snap.status === "playing";
  return (
    <section className="grid gap-6 lg:grid-cols-[minmax(0,1.5fr)_minmax(0,1fr)]" aria-label="Signer review">
      <div className="space-y-4">
        <AvatarStage
          player={player}
          badges={<StageBadge tone="warn">Clip not signer-reviewed</StageBadge>}
          caption={
            selected ? (
              <StageCaption gloss={selected} detail={previous ? `You rated it ${previous.clarity} of 5, ${previous.verdict}` : "Not reviewed by you yet"} />
            ) : (
              <StageCaption detail="Choose a sign from the list to watch it." />
            )
          }
          overlay={showSource ? <SourceSkeleton player={player} /> : undefined}
        />
        <div className="flex flex-wrap items-center gap-3" role="group" aria-label="Playback">
          <button className="btn btn-primary" disabled={!selected} onClick={() => (playing ? player.pause() : player.play())}>
            {playing ? <Pause size={18} aria-hidden /> : <Play size={18} aria-hidden />} {playing ? "Pause" : "Play"}
          </button>
          <button className="btn" disabled={!selected} onClick={() => player.replay()}>
            <RotateCcw size={18} aria-hidden /> Replay
          </button>
          <button className="btn" aria-pressed={showSource} onClick={() => setShowSource((v) => !v)}>
            {showSource ? "Hide source skeleton" : "Show source skeleton"}
          </button>
          <div className="ml-auto">
            <SpeedControl rate={rate} onChange={setRate} />
          </div>
        </div>
        <div className="card">
          <h2 className="card-title">Your review{selected ? `: ${selected}` : ""}</h2>
          <p className="mt-1 text-sm font-semibold text-ink2">
            Saved on this computer under your reviewer ID. A review changes no clip, label or flag; it is a record for the project team to read.
          </p>
          <form
            className="mt-4 space-y-4"
            onSubmit={(e) => {
              e.preventDefault();
              void save();
            }}
          >
            <label className="block text-sm font-bold text-ink2">
              Reviewer ID (letters and digits, for example R01; not your name)
              <input value={reviewerId} onChange={(e) => setReviewerId(e.target.value)} maxLength={32} className="input mt-1 block !w-48" autoComplete="off" spellCheck={false} />
            </label>
            <fieldset>
              <legend className="text-sm font-bold text-ink2">How clear is the signing? (1 to 5)</legend>
              <div className="mt-1 flex flex-wrap gap-2">
                {[1, 2, 3, 4, 5].map((n) => (
                  <label key={n} className={`chip min-h-11 cursor-pointer ${clarity === n ? "ring-2 ring-lav" : ""}`}>
                    <input type="radio" name="clarity" className="sr-only" checked={clarity === n} onChange={() => setClarity(n)} />
                    {n} {CLARITY_LABELS[n]}
                  </label>
                ))}
              </div>
            </fieldset>
            <fieldset>
              <legend className="text-sm font-bold text-ink2">Is it the right sign?</legend>
              <div className="mt-1 flex gap-2">
                {(["correct", "wrong"] as const).map((v) => (
                  <label key={v} className={`chip min-h-11 cursor-pointer ${verdict === v ? "ring-2 ring-lav" : ""}`}>
                    <input type="radio" name="verdict" className="sr-only" checked={verdict === v} onChange={() => setVerdict(v)} />
                    {v === "correct" ? "Correct" : "Wrong"}
                  </label>
                ))}
              </div>
            </fieldset>
            <label className="block text-sm font-bold text-ink2">
              Comment (optional, what should change?)
              <textarea value={comment} onChange={(e) => setComment(e.target.value)} rows={3} maxLength={MAX_COMMENT} className="input mt-1 block w-full" />
            </label>
            {problems.length > 0 && (
              <ul role="alert" className="notice notice-bad">
                {problems.map((p) => (
                  <li key={p}>{p}</li>
                ))}
              </ul>
            )}
            {error && <p role="alert" className="notice notice-bad">{error}</p>}
            {message && <p aria-live="polite" className="notice notice-good">{message}</p>}
            <button type="submit" className="btn btn-primary" disabled={busy || !backendUp || !selected}>
              {busy ? "Saving…" : previous ? "Save a new review" : "Save review"}
            </button>
          </form>
        </div>
      </div>

      <div className="card h-fit">
        <h2 className="card-title">Signs to review</h2>
        <p className="mt-1 text-sm font-semibold text-ink2" aria-live="polite">
          {isValidReviewer(reviewerId) ? `${mine.length} of ${glosses.length} reviewed by ${reviewerId.trim().toUpperCase()}` : "Enter your reviewer ID to see your progress."}
        </p>
        {!backendUp && <p className="notice notice-warn mt-3">Backend unreachable: the list and your reviews are unavailable.</p>}
        <div className="mt-3 flex flex-wrap items-center gap-3">
          <label className="flex-1 text-sm font-bold text-ink2">
            <span className="sr-only">Search signs</span>
            <input type="search" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search, for example doctor" className="input w-full" autoComplete="off" />
          </label>
          <label className="flex items-center gap-2 text-sm font-bold text-ink2">
            <input type="checkbox" checked={onlyUnreviewed} onChange={(e) => setOnlyUnreviewed(e.target.checked)} /> Not reviewed yet
          </label>
        </div>
        <ul className="mt-3 grid max-h-[28rem] grid-cols-2 gap-1.5 overflow-y-auto pr-1 text-sm font-semibold">
          {rows.map((r) => (
            <li key={r.gloss}>
              <button
                type="button"
                onClick={() => choose(r.gloss)}
                aria-current={selected === r.gloss ? "true" : undefined}
                className={`w-full rounded-lg px-2.5 py-1.5 text-left ${selected === r.gloss ? "bg-accent text-onaccent" : "bg-surface2 hover:bg-surface"}`}
              >
                {r.gloss}
                {r.reviewed ? ` · ${r.reviewed.clarity}/5 ${r.reviewed.verdict === "correct" ? "✓" : "✗"}` : ""}
              </button>
            </li>
          ))}
        </ul>
        {rows.length === 0 && glosses.length > 0 && <p className="mt-2 text-sm text-ink2">No sign matches.</p>}
      </div>
    </section>
  );
}

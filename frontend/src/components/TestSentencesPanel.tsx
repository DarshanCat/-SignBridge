"use client";
import { useState } from "react";
import { apiGet, apiPost, type AvatarPlan, type TextToGloss } from "@/lib/api";
import { glossesToPlan } from "@/lib/avatar/sentence";
import { sentenceRow, type ConversationVocabulary, type SentenceRow } from "@/lib/conversationVocab";

/** The 10 conversation test sentences: the gloss the text to gloss produces and which of its signs have no clip. Nothing is played or invented here. */
export function TestSentencesPanel({ backendUp }: { backendUp: boolean }) {
  const [rows, setRows] = useState<SentenceRow[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run() {
    setBusy(true);
    setError(null);
    try {
      const vocab = await apiGet<ConversationVocabulary>("/api/conversation/vocabulary");
      const out: SentenceRow[] = [];
      for (const text of vocab.test_sentences) {
        const gloss = await apiPost<TextToGloss>("/api/nlp/text-to-gloss", { text });
        const plan = gloss.tokens.length ? await apiPost<AvatarPlan>("/api/avatar/plan", { gloss: glossesToPlan(gloss.tokens) }) : null;
        const available = new Set((plan?.steps ?? []).filter((s) => s.available).map((s) => s.gloss));
        out.push(sentenceRow(text, gloss, available, vocab));
      }
      setRows(out);
    } catch (e) {
      setRows(null);
      setError(e instanceof Error ? e.message : "The test sentences could not be run.");
    } finally {
      setBusy(false);
    }
  }

  const withGaps = rows?.filter((r) => r.missing.length > 0).length ?? 0;
  return (
    <section aria-label="Conversation test sentences" className="card mt-4 !p-4 sm:!p-5">
      <h2 className="text-lg font-extrabold">Conversation test sentences</h2>
      <p className="mt-1 text-sm text-ink2">
        Ten everyday sentences, their gloss, and the signs that have no clip yet. A missing sign is skipped when the avatar signs the sentence; no clip is faked.
      </p>
      <button type="button" className="btn btn-primary mt-3" onClick={run} disabled={busy || !backendUp}>
        {busy ? "Running…" : rows ? "Run again" : "Run the 10 sentences"}
      </button>
      {!backendUp && <p className="mt-2 text-sm text-ink2">The backend is not reachable.</p>}
      {error && <p role="alert" className="mt-2 text-sm text-warnfg">{error}</p>}
      {rows && (
        <>
          <p className="mt-3 text-sm font-semibold text-ink2" aria-live="polite">
            {withGaps} of {rows.length} sentences have at least one sign without a clip.
          </p>
          <div className="mt-2 overflow-x-auto">
            <table className="w-full min-w-[34rem] border-collapse text-left text-sm">
              <thead>
                <tr className="border-b border-line text-ink2">
                  <th scope="col" className="py-1.5 pr-3">Sentence</th>
                  <th scope="col" className="py-1.5 pr-3">Gloss</th>
                  <th scope="col" className="py-1.5">Missing signs</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.text} className="border-b border-line/60 align-top">
                    <td className="py-1.5 pr-3">{r.text}</td>
                    <td className="py-1.5 pr-3 font-mono">{r.gloss}</td>
                    <td className="py-1.5">
                      {r.missing.length === 0 ? "none" : r.missing.map((m) => `${m.gloss}${m.toRecord ? " (to record)" : ""}`).join(", ")}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </section>
  );
}

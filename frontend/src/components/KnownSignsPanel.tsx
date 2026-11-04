"use client";
import { Search } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { apiGet } from "@/lib/api";
import { filterSigns, type KnownSigns } from "@/lib/conversationVocab";

/** "Signs I know": every class of the loaded model, searchable, so a user knows what the recognizer can be shown. */
export function KnownSignsPanel({ backendUp }: { backendUp: boolean }) {
  const [data, setData] = useState<KnownSigns | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");

  useEffect(() => {
    if (!backendUp) return;
    const ctl = new AbortController();
    apiGet<KnownSigns>("/api/model/signs", ctl.signal)
      .then((d) => {
        setData(d);
        setError(null);
      })
      .catch((e) => {
        if (!ctl.signal.aborted) setError(e instanceof Error ? e.message : "Could not load the list of signs.");
      });
    return () => ctl.abort();
  }, [backendUp]);

  const shown = useMemo(() => (data ? filterSigns(data.signs, query) : []), [data, query]);

  return (
    <section aria-label="Signs I know" className="card mt-4 !p-4 sm:!p-5">
      <h2 className="text-lg font-extrabold">Signs I know{data?.loaded ? ` (${data.count})` : ""}</h2>
      {!backendUp && <p className="mt-2 text-sm font-semibold text-ink2">The backend is not reachable, so the list of signs is unavailable.</p>}
      {error && <p role="alert" className="mt-2 text-sm text-warnfg">{error}</p>}
      {data && !data.loaded && <p className="mt-2 text-sm font-semibold text-ink2">No recognition model is loaded, so no sign can be recognized.</p>}
      {data?.loaded && (
        <>
          <p className="mt-1 text-sm text-ink2">
            These are the signs the current model can recognize. Anything else, or a sign it is unsure of, is shown as unrecognized. Authors&apos; predefined split, signer independence not verified.
          </p>
          <label className="mt-3 flex items-center gap-2 rounded-xl border border-line bg-surface px-3 py-2">
            <Search aria-hidden className="size-4 text-ink2" />
            <span className="sr-only">Search the signs I know</span>
            <input
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search, for example doctor"
              className="w-full bg-transparent text-base outline-none"
              autoComplete="off"
            />
          </label>
          <p className="mt-2 text-sm font-semibold text-ink2" aria-live="polite">
            {query.trim() ? `${shown.length} of ${data.count} signs` : `${data.count} signs`}
          </p>
          <ul className="mt-2 grid max-h-72 grid-cols-2 gap-1.5 overflow-y-auto pr-1 text-sm font-semibold sm:grid-cols-3 lg:grid-cols-4">
            {shown.map((s) => (
              <li key={s.label} className="rounded-lg bg-surface2 px-2.5 py-1.5">
                {s.label}
              </li>
            ))}
          </ul>
          {shown.length === 0 && <p className="mt-2 text-sm text-ink2">No sign matches &quot;{query}&quot;. The model cannot recognize it.</p>}
        </>
      )}
    </section>
  );
}

import type { StatusItem } from "@/lib/status";

const DOT: Record<StatusItem["level"], string> = {
  ok: "bg-goodfg",
  warn: "bg-warnfg",
  off: "bg-badfg",
  pending: "bg-ink2 animate-pulse",
};

/** System status as a strip of items under the content: each has a coloured dot AND its words, so colour is never the only signal. */
export function StatusPanel({ items }: { items: StatusItem[] }) {
  return (
    <section aria-label="System status" className="card !p-4 sm:!p-5">
      <h2 className="eyebrow mb-3">System status</h2>
      <ul className="grid gap-x-6 gap-y-3 sm:grid-cols-2 lg:grid-cols-5">
        {items.map((i) => (
          <li key={i.id} className="flex gap-3">
            <span aria-hidden className={`mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full ${DOT[i.level]}`} />
            <div>
              <p className="text-sm font-extrabold">{i.label}</p>
              <p className="text-xs font-semibold text-ink2">{i.detail}</p>
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}

import type { StatusItem } from "@/lib/status";

const DOT: Record<StatusItem["level"], string> = {
  ok: "bg-emerald-400",
  warn: "bg-amber-400",
  off: "bg-rose-400",
  pending: "bg-slate-400 animate-pulse",
};

export function StatusPanel({ items }: { items: StatusItem[] }) {
  return (
    <section aria-label="System status" className="rounded-xl border border-white/10 bg-panel p-4">
      <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-300">System status</h2>
      <ul className="space-y-3">
        {items.map((i) => (
          <li key={i.id} className="flex gap-3">
            <span aria-hidden className={`mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full ${DOT[i.level]}`} />
            <div>
              <p className="text-sm font-medium">{i.label}</p>
              <p className="text-xs text-slate-400">{i.detail}</p>
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}

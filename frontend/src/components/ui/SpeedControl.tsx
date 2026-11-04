"use client";

const RATES = [0.5, 1, 1.5] as const;

/** Playback speed as a segmented control (radio group): large targets, arrow keys move between options. */
export function SpeedControl({ rate, onChange }: { rate: number; onChange: (r: number) => void }) {
  return (
    <div role="radiogroup" aria-label="Playback speed" className="flex gap-1 rounded-2xl border-[1.5px] border-edge bg-surface p-1">
      {RATES.map((r) => {
        const on = r === rate;
        return (
          <button
            key={r}
            type="button"
            role="radio"
            aria-checked={on}
            tabIndex={on ? 0 : -1}
            onClick={() => onChange(r)}
            onKeyDown={(e) => {
              const i = RATES.indexOf(rate as (typeof RATES)[number]);
              if (e.key === "ArrowRight" || e.key === "ArrowDown") onChange(RATES[(i + 1) % RATES.length]);
              if (e.key === "ArrowLeft" || e.key === "ArrowUp") onChange(RATES[(i + RATES.length - 1) % RATES.length]);
            }}
            className={`min-h-11 min-w-[3.25rem] rounded-xl px-3 text-sm font-extrabold transition duration-200 ${on ? "bg-soft text-ink" : "text-ink2 hover:bg-surface2"}`}
          >
            {r}x
          </button>
        );
      })}
    </div>
  );
}

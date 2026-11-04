"use client";
import { useEffect, useRef } from "react";
import type { SequencePlayer } from "@/lib/avatar/player";
import { sourceFrameAtTime, type Side } from "@/lib/avatar/sourceLandmarks";

/** MediaPipe hand connections: the palm, then the four joints of each finger. */
const HAND_LINES: [number, number][] = [
  [0, 1], [1, 2], [2, 3], [3, 4],
  [0, 5], [5, 6], [6, 7], [7, 8],
  [5, 9], [9, 10], [10, 11], [11, 12],
  [9, 13], [13, 14], [14, 15], [15, 16],
  [13, 17], [17, 18], [18, 19], [19, 20], [0, 17],
];

const W = 220;
const H = 270;
const PX = 56; // pixels per shoulder width
const ORIGIN = { x: W / 2, y: 78 }; // the shoulder midpoint

const cssRgb = (name: string, alpha = 1): string => `rgb(${getComputedStyle(document.documentElement).getPropertyValue(`--${name}`).trim()} / ${alpha})`;

/**
 * The landmarks of the dataset sample behind the sign that is playing, drawn as a skeleton (picture aspect corrected, as the retarget uses them),
 * so a viewer can compare them with the avatar. It follows the avatar's own clock, so the two always show the same moment of the sign.
 */
export function SourceSkeleton({ player }: { player: SequencePlayer }) {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = ref.current;
    const ctx = canvas?.getContext("2d");
    if (!canvas || !ctx) return;
    const dpr = Math.min(2, window.devicePixelRatio || 1);
    canvas.width = W * dpr;
    canvas.height = H * dpr;
    ctx.scale(dpr, dpr);
    let raf = 0;
    const pt = (v: { x: number; y: number }): [number, number] => [ORIGIN.x + v.x * PX, ORIGIN.y - v.y * PX];
    const draw = () => {
      ctx.clearRect(0, 0, W, H);
      const cur = player.current();
      const lm = cur?.clip.landmarks;
      ctx.font = "600 13px Nunito Variable, system-ui, sans-serif";
      ctx.fillStyle = cssRgb("ink2");
      if (!cur || !lm) {
        ctx.fillText(cur ? "No source landmarks for this clip." : "Press Play to see the source.", 12, H / 2);
        raf = requestAnimationFrame(draw);
        return;
      }
      const f = sourceFrameAtTime(lm, cur.time);
      const colors: Record<Side, string> = { l: cssRgb("accent"), r: cssRgb("lav") };
      // head: eyes, nose and mouth around the middle of the face
      ctx.fillStyle = cssRgb("ink2", 0.8);
      for (const p of [f.nose, f.mouth, f.eyes]) {
        const [x, y] = pt(p);
        ctx.beginPath();
        ctx.arc(x, y, 3, 0, 7);
        ctx.fill();
      }
      const [hx, hy] = pt(f.nose);
      ctx.strokeStyle = cssRgb("ink2", 0.45);
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.ellipse(hx, hy + 4, 0.55 * PX, 0.75 * PX, 0, 0, 7);
      ctx.stroke();
      // shoulders, arms
      ctx.lineWidth = 3;
      ctx.lineCap = "round";
      ctx.strokeStyle = cssRgb("ink2", 0.7);
      ctx.beginPath();
      ctx.moveTo(...pt(f.shoulder.l));
      ctx.lineTo(...pt(f.shoulder.r));
      ctx.stroke();
      for (const s of ["l", "r"] as Side[]) {
        ctx.strokeStyle = colors[s];
        ctx.beginPath();
        ctx.moveTo(...pt(f.shoulder[s]));
        ctx.lineTo(...pt(f.elbow[s]));
        ctx.lineTo(...pt(f.wrist[s]));
        ctx.stroke();
        const hand = f.hand[s];
        if (!hand) continue;
        ctx.lineWidth = 1.6;
        for (const [a, b] of HAND_LINES) {
          ctx.beginPath();
          ctx.moveTo(...pt(hand[a]));
          ctx.lineTo(...pt(hand[b]));
          ctx.stroke();
        }
        ctx.fillStyle = colors[s];
        for (const p of hand) {
          const [x, y] = pt(p);
          ctx.beginPath();
          ctx.arc(x, y, 1.6, 0, 7);
          ctx.fill();
        }
        ctx.lineWidth = 3;
      }
      raf = requestAnimationFrame(draw);
    };
    raf = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(raf);
  }, [player]);

  return (
    <div className="glass rounded-2xl p-2" style={{ width: W + 16 }}>
      <p className="px-1 pb-1 text-xs font-extrabold text-ink2">Source landmarks (dataset sample)</p>
      <canvas ref={ref} style={{ width: W, height: H }} role="img" aria-label="Skeleton of the source landmarks of the sign that is playing" />
    </div>
  );
}

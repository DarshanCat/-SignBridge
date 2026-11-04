import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

const css = readFileSync(join(process.cwd(), "src", "app", "globals.css"), "utf-8").replace(/\r\n/g, "\n");

function block(start: string): string {
  const i = css.indexOf(start);
  expect(i, start).toBeGreaterThanOrEqual(0);
  const j = css.indexOf("{", i);
  let depth = 0;
  for (let k = j; k < css.length; k++) {
    if (css[k] === "{") depth++;
    else if (css[k] === "}" && --depth === 0) return css.slice(j + 1, k);
  }
  throw new Error("unbalanced braces after " + start);
}

type RGB = [number, number, number];
function tokens(body: string): Record<string, RGB> {
  const out: Record<string, RGB> = {};
  for (const m of body.matchAll(/--([a-z0-9-]+):\s*(\d+) (\d+) (\d+);/g)) out[m[1]] = [Number(m[2]), Number(m[3]), Number(m[4])];
  return out;
}

const light = tokens(block(":root {"));
const darkExplicit = tokens(block(':root[data-theme="dark"]'));
const darkMedia = tokens(block(':root:not([data-theme="light"])'));
const dark = { ...light, ...darkExplicit };

function luminance([r, g, b]: RGB): number {
  const f = (v: number) => {
    const c = v / 255;
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  };
  return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b);
}
const ratio = (a: RGB, b: RGB) => {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
};

/** [foreground, background, minimum ratio]: text needs 4.5, control borders and focus rings 3 (WCAG 2.1 AA). */
const PAIRS: [string, string, number][] = [
  ["ink", "canvas", 4.5], ["ink", "surface", 4.5], ["ink", "surface2", 4.5], ["ink2", "canvas", 4.5], ["ink2", "surface", 4.5], ["ink2", "surface2", 4.5], ["ink2", "field", 4.5],
  ["onaccent", "accent", 4.5], ["accent", "surface", 4.5], ["accent", "canvas", 4.5], ["ink", "soft", 4.5],
  ["edge", "surface", 3], ["edge", "canvas", 3], ["edge", "field", 3], ["lav", "surface", 3], ["lav", "canvas", 3], ["lav", "surface2", 3],
  ["good-fg", "good-bg", 4.5], ["warn-fg", "warn-bg", 4.5], ["bad-fg", "bad-bg", 4.5], ["info-fg", "info-bg", 4.5],
  ["good-fg", "surface", 4.5], ["warn-fg", "surface", 4.5], ["bad-fg", "surface", 4.5], ["info-fg", "surface", 4.5],
  ["camfg", "cam", 4.5],
];

describe("design tokens", () => {
  it("the dark theme is the same whether it comes from the system setting or from the toggle", () => {
    for (const [k, v] of Object.entries(darkMedia)) expect(darkExplicit[k], k).toEqual(v);
    expect(Object.keys(darkExplicit).sort()).toEqual(Object.keys(darkMedia).sort());
  });

  it("every token of the light theme is overridden in the dark theme except the ones that are meant to be fixed", () => {
    const fixed = new Set(["cam", "camfg"]);
    for (const k of Object.keys(light)) if (!fixed.has(k)) expect(darkExplicit[k], k).toBeDefined();
  });

  for (const [theme, t] of [["light", light], ["dark", dark]] as const) {
    it(`${theme}: every text, border and focus pair meets WCAG AA`, () => {
      const failures = PAIRS.filter(([fg, bg, min]) => ratio(t[fg], t[bg]) < min).map(([fg, bg, min]) => `${fg} on ${bg}: ${ratio(t[fg], t[bg]).toFixed(2)} < ${min}`);
      expect(failures).toEqual([]);
    });
  }

  it("honours the reduced motion setting and has a visible focus style", () => {
    expect(css).toMatch(/@media \(prefers-reduced-motion: reduce\)/);
    expect(css).toMatch(/animation-duration: 0\.001ms !important/);
    expect(css).toMatch(/:focus-visible\s*{[^}]*outline: 3px solid/);
  });
});

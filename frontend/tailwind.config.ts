import type { Config } from "tailwindcss";

const token = (name: string) => `rgb(var(--${name}) / <alpha-value>)`;

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        canvas: token("canvas"),
        surface: token("surface"),
        surface2: token("surface2"),
        field: token("field"),
        line: token("line"),
        edge: token("edge"),
        ink: token("ink"),
        ink2: token("ink2"),
        accent: token("accent"),
        onaccent: token("onaccent"),
        soft: token("soft"),
        lav: token("lav"),
        goodfg: token("good-fg"),
        goodbg: token("good-bg"),
        warnfg: token("warn-fg"),
        warnbg: token("warn-bg"),
        badfg: token("bad-fg"),
        badbg: token("bad-bg"),
        infofg: token("info-fg"),
        infobg: token("info-bg"),
        cam: "rgb(var(--cam) / <alpha-value>)",
        camfg: "rgb(var(--camfg) / <alpha-value>)",
      },
      fontFamily: {
        sans: ['"Nunito Variable"', "system-ui", "sans-serif"],
        display: ['"Zen Maru Gothic"', '"Nunito Variable"', "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};
export default config;

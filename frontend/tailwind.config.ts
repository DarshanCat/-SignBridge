import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: { ink: "#0b1020", panel: "#121a33", accent: "#5eead4" },
    },
  },
  plugins: [],
};
export default config;

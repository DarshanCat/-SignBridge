import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    include: ["src/**/*.test.{ts,tsx}"],
    exclude: ["**/node_modules/**", ".next/**", "dist/**", "build/**", "out/**", "coverage/**"],
  },
});

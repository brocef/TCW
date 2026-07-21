import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: ["web/client/src/test-setup.ts"],
    include: ["web/**/*.test.{ts,tsx}"]
  }
});

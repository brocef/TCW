import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "web/e2e",
  timeout: 30_000,
  use: { baseURL: "http://127.0.0.1:8765", trace: "retain-on-failure" },
  reporter: "list"
});

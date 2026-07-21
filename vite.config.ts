import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  root: "web/client",
  publicDir: "../../tcw/serve/static",
  plugins: [react()],
  build: {
    outDir: "../../web-dist/client",
    emptyOutDir: true,
    sourcemap: false,
    manifest: true
  }
});

import { cp, mkdir, rm } from "node:fs/promises"
import { build } from "esbuild"
import { execFileSync } from "node:child_process"

await rm("web-dist", { recursive: true, force: true })
execFileSync("node_modules/.bin/vite", ["build"], { stdio: "inherit" })
await build({
    entryPoints: ["web/server/src/server.ts"],
    outfile: "web-dist/server.cjs",
    bundle: true,
    platform: "node",
    format: "cjs",
    target: "node22",
    sourcemap: false,
})
await rm("tcw/serve/dist", { recursive: true, force: true })
await mkdir("tcw/serve/dist", { recursive: true })
await cp("web-dist/client", "tcw/serve/dist/client", { recursive: true })
await cp("web-dist/server.cjs", "tcw/serve/dist/server.cjs")

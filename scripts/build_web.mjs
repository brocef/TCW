import { cp, mkdir, rm } from "node:fs/promises"
import { execFileSync } from "node:child_process"

// Builds the client only: `tcw serve` serves it from Python, so nothing in
// the package runs under Node.
await rm("web-dist", { recursive: true, force: true })
execFileSync("node_modules/.bin/vite", ["build"], { stdio: "inherit" })
await rm("tcw/serve/dist", { recursive: true, force: true })
await mkdir("tcw/serve/dist", { recursive: true })
await cp("web-dist/client", "tcw/serve/dist/client", { recursive: true })

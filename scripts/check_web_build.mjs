import { execFileSync } from "node:child_process"

execFileSync(process.execPath, ["scripts/build_web.mjs"], { stdio: "inherit" })
execFileSync("git", ["diff", "--exit-code", "--", "tcw/serve/dist"], {
    stdio: "inherit",
})

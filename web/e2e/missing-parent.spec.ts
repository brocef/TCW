import { expect, test } from "@playwright/test"
import { spawn, spawnSync, type ChildProcess } from "node:child_process"
import { appendFile, mkdir, mkdtemp, rm } from "node:fs/promises"
import { tmpdir } from "node:os"
import { join } from "node:path"

// A filesystem project whose parent is not on this machine (TCW-109): the
// parent may set the tags, so the project summary answers them as
// `{"unavailable": <why>}`, and the page must stay usable.
const PORT = 8895
const baseUrl = `http://127.0.0.1:${PORT}`
let server: ChildProcess
let serverError = ""
let fixture = ""

test.describe.configure({ mode: "serial" })

test.beforeAll(async () => {
    fixture = await mkdtemp(join(tmpdir(), "tcw-playwright-parent-"))
    const app = join(fixture, "app")
    await mkdir(app)
    spawnSync("git", ["init", "-q"], { cwd: app, stdio: "inherit" })
    const initialized = spawnSync("tcw", ["init", "--id", "app"], {
        cwd: app,
        encoding: "utf8",
    })
    if (initialized.status !== 0) throw new Error(initialized.stderr)
    // No folder next to `app` or enclosing it declares `core`.
    await appendFile(join(app, ".tcw", "tcw-config.yaml"), "parents: [core]\n")
    server = spawn("tcw", ["serve", "--no-open", "--port", String(PORT)], {
        cwd: app,
        stdio: ["ignore", "pipe", "pipe"],
    })
    server.stderr?.on("data", (chunk: Buffer) => {
        serverError += chunk.toString()
    })
    const deadline = Date.now() + 15_000
    while (Date.now() < deadline) {
        if (server.exitCode !== null)
            throw new Error(
                `tcw serve exited before readiness: ${serverError.trim()}`
            )
        try {
            const response = await fetch(`${baseUrl}/api/work`)
            if (response.ok) return
        } catch {
            // The listener is not ready yet.
        }
        await new Promise((resolve) => setTimeout(resolve, 100))
    }
    throw new Error("tcw serve did not become ready")
})

test.afterAll(async () => {
    if (server && server.exitCode === null) {
        server.kill("SIGTERM")
        await new Promise<void>((resolve) =>
            server.once("exit", () => resolve())
        )
    }
    if (fixture) await rm(fixture, { recursive: true, force: true })
})

const reason =
    /could not be read: 'app' inherits its configuration \(work\.tags\) from project 'core', which is not on this machine/

test("the summary answers the tags as unavailable", async ({ request }) => {
    const response = await request.get(`${baseUrl}/api/project`)
    expect(response.ok()).toBe(true)
    const body = await response.json()
    expect(body.tags.unavailable).toContain("(work.tags)")
})

test("an item is created and edited, with the reason where the tags would be", async ({
    page,
}) => {
    const errors: string[] = []
    page.on("pageerror", (error) => errors.push(error.message))
    await page.goto(`${baseUrl}/work`)
    await page.getByRole("button", { name: "+ New item" }).click()
    await expect(page.getByText(reason)).toBeVisible()
    await expect(page.getByRole("combobox", { name: "Tags" })).toHaveCount(0)
    await page.getByRole("textbox", { name: "Title" }).fill("Made here")
    await page.getByRole("button", { name: "Save" }).click()
    await expect(page.getByRole("heading", { name: "Made here" })).toBeVisible()

    await page.getByRole("button", { name: "Edit", exact: true }).click()
    await expect(page.getByText(reason)).toBeVisible()
    await page.getByLabel("Priority").click()
    await page.getByRole("option", { name: "high", exact: true }).click()
    await page.getByRole("button", { name: "Save" }).click()
    await expect(page.locator(".fields")).toContainText("high")
    expect(errors).toEqual([])
})

test("the Tags filter says the tags could not be read, and why", async ({
    page,
}) => {
    await page.goto(`${baseUrl}/work`)
    await expect(page.getByRole("treeitem")).toHaveCount(1)
    await page.getByRole("button", { name: /^Tags/ }).click()
    await expect(page.getByText(reason)).toBeVisible()
    await expect(page.getByText("none available")).toHaveCount(0)
})

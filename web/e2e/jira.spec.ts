import { expect, test } from "@playwright/test"
import { spawn, type ChildProcess } from "node:child_process"
import { mkdtemp, readFile, readdir, rm, writeFile } from "node:fs/promises"
import { tmpdir } from "node:os"
import { join, resolve } from "node:path"

// A Jira-mode project served against TCW-71's fake Jira by
// `tests/serve/jira_launcher.py`: no socket to Jira is opened. The fake logs
// each request it answers to `requests.log`, and fails every request while
// the `unreachable` marker file exists.
const PORT = 8892
const baseUrl = `http://127.0.0.1:${PORT}`
const SITE = "https://acme.atlassian.net"
const repo = resolve(__dirname, "..", "..")
let server: ChildProcess
let serverError = ""
let fixture = ""

test.describe.configure({ mode: "serial" })

async function requests(): Promise<string[]> {
    try {
        return (await readFile(join(fixture, "requests.log"), "utf8"))
            .split("\n")
            .filter(Boolean)
    } catch {
        return []
    }
}

async function specFolder(): Promise<string> {
    const work = join(fixture, "project", "docs", "work")
    for (const name of await readdir(work))
        if (name.endsWith("-board")) return name
    throw new Error("the fixture has no item with a spec")
}

test.beforeAll(async () => {
    fixture = await mkdtemp(join(tmpdir(), "tcw-playwright-jira-"))
    server = spawn(
        process.env.TCW_PYTHON ?? "python",
        ["-m", "tests.serve.jira_launcher", fixture, "--port", String(PORT)],
        {
            cwd: repo,
            env: {
                ...process.env,
                TCW_TEST_JIRA_EMAIL: "dev@example.test",
                TCW_TEST_JIRA_TOKEN: "token",
            },
            stdio: ["ignore", "pipe", "pipe"],
        }
    )
    server.stderr?.on("data", (chunk: Buffer) => {
        serverError += chunk.toString()
    })
    const deadline = Date.now() + 30_000
    while (Date.now() < deadline) {
        if (server.exitCode !== null)
            throw new Error(`the launcher exited: ${serverError.trim()}`)
        try {
            const response = await fetch(`${baseUrl}/api/project`)
            if (response.ok) return
        } catch {
            // The listener is not ready yet.
        }
        await new Promise((done) => setTimeout(done, 100))
    }
    throw new Error("the launcher did not become ready")
})

test.afterAll(async () => {
    if (server && server.exitCode === null) {
        server.kill("SIGTERM")
        await new Promise<void>((done) => server.once("exit", () => done()))
    }
    if (fixture) await rm(fixture, { recursive: true, force: true })
})

test("the board is one search, with assignees by name", async ({ page }) => {
    const before = (await requests()).length
    await page.goto(`${baseUrl}/work`)
    await expect(page.getByRole("treeitem")).toHaveCount(2)
    await expect(page.getByText("Ann Author")).toBeVisible()
    await expect(page.getByText("acct-ann")).toHaveCount(0)
    const made = (await requests()).slice(before)
    expect(made.filter((line) => line.includes("/search"))).toHaveLength(1)
    expect(
        made.filter((line) => /\/user(\?|$)/.test(line.split(" ")[1] ?? ""))
    ).toHaveLength(0)
})

test("the record Jira keeps is read-only, each part opening Jira", async ({
    page,
}) => {
    await page.goto(`${baseUrl}/work/${await specFolder()}`)
    const open = page.getByRole("link", { name: "Open in Jira" }).first()
    await expect(open).toHaveAttribute("href", new RegExp(`^${SITE}/browse/`))
    await expect(page.getByRole("region", { name: "Request" })).toContainText(
        "Load the board with one search."
    )
    const comments = page.getByRole("region", { name: "Comments" })
    await expect(comments).toContainText("First comment.")
    await expect(comments).toContainText("Second comment.")
    await expect(comments.getByRole("textbox")).toHaveCount(0)
    // No Edit on the properties; a stage file's own Edit stays.
    await expect(page.locator(".detail-head .edit-btn")).toHaveCount(0)
    // The stage Jira keeps says so, and links there. The tabs open on the
    // item's own stage (spec), so the request's tab is chosen first.
    await page.getByRole("tab", { name: "Request" }).click()
    const panel = page.getByRole("tabpanel")
    await expect(panel).toContainText(
        "This project's backend keeps the request record."
    )
    await expect(
        panel.getByRole("link", { name: "Open in Jira" })
    ).toHaveAttribute("href", new RegExp(`^${SITE}/browse/`))
})

test("adopting an inbox ticket opens its new item", async ({ page }) => {
    await page.goto(`${baseUrl}/work`)
    await page.getByRole("button", { name: "Tickets" }).click()
    const tickets = page.getByRole("region", { name: "Tickets" })
    await expect(tickets).toContainText("Triage me")
    await tickets.getByRole("button", { name: "Adopt" }).first().click()
    await expect(page.getByRole("heading", { name: "Triage me" })).toBeVisible()
    await expect(page).toHaveURL(/\/work\/TCW-\d+-/)
})

test("when Jira cannot be reached the board says so and files stay editable", async ({
    page,
}) => {
    const marker = join(fixture, "unreachable")
    await writeFile(marker, "")
    try {
        await page.goto(`${baseUrl}/work`)
        const banner = page.locator(".fallback-banner")
        await expect(banner).toContainText("could not reach the tracker")
        await expect(
            banner.getByRole("button", { name: "Retry" })
        ).toBeVisible()

        await page.goto(`${baseUrl}/work/${await specFolder()}`)
        await page.getByRole("tab", { name: "Spec" }).click()
        await page
            .getByRole("tabpanel")
            .getByRole("button", { name: "Edit" })
            .click()
        await page
            .getByLabel("Markdown", { exact: true })
            .fill("# Spec\n\nEdited while Jira was down.\n")
        await page.getByRole("button", { name: "Save" }).click()
        await expect(page.getByRole("tabpanel")).toContainText(
            "Edited while Jira was down."
        )
    } finally {
        await rm(marker, { force: true })
    }
    await page.goto(`${baseUrl}/work`)
    await expect(page.locator(".fallback-banner")).toHaveCount(0)
})

import { expect, test, type Page } from "@playwright/test"
import { spawn, spawnSync, type ChildProcess } from "node:child_process"
import { mkdtemp } from "node:fs/promises"
import { tmpdir } from "node:os"
import { join } from "node:path"

const PUBLIC_PORT = 8891
const baseUrl = `http://127.0.0.1:${PUBLIC_PORT}`
let server: ChildProcess
let serverError = ""
let nodeRoot = ""

test.describe.configure({ mode: "serial" })

// Screenshots must not encode the wall clock. Every view renders a live
// "Modified at <date>, <time>" from the fixture's real creation time, so
// baselines captured at one minute fail at another. Masking alone is not
// enough — the mask rectangle tracks the element's width, which itself changes
// with the text ("6:14 PM" vs "10:14 PM"). Overwriting the text with a constant
// fixes both the glyphs and the width, and keeps the baselines readable.
// Assigning textContent is CSSOM, not an injected stylesheet, so it does not
// trip the app's `default-src 'self'` CSP the way addStyleTag does.
async function stableScreenshot(page: Page, name: string) {
    await page.evaluate(() => {
        document.querySelectorAll("time.modified-at").forEach((element) => {
            element.textContent = "Modified at Jan 1, 2026, 12:00 AM"
        })
    })
    await expect(page).toHaveScreenshot(name, { animations: "disabled" })
}

test.beforeAll(async () => {
    nodeRoot = await mkdtemp(join(tmpdir(), "tcw-playwright-"))
    spawnSync("git", ["init", "-q"], { cwd: nodeRoot, stdio: "inherit" })
    const initialized = spawnSync("tcw", ["init", "--id", "playwright-node"], {
        cwd: nodeRoot,
        encoding: "utf8",
    })
    if (initialized.status !== 0) throw new Error(initialized.stderr)
    server = spawn(
        "tcw",
        ["serve", "--no-open", "--port", String(PUBLIC_PORT)],
        {
            cwd: nodeRoot,
            stdio: ["ignore", "pipe", "pipe"],
        }
    )
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
    if (!server || server.exitCode !== null) return
    server.kill("SIGTERM")
    await new Promise<void>((resolve) => server.once("exit", () => resolve()))
})

test("loads the React shell and navigates every axis", async ({ page }) => {
    await page.goto(baseUrl)
    await expect(page).toHaveTitle("TCW")
    await expect(page.getByRole("tree", { name: "Objects" })).toBeVisible()
    await expect(page.locator(".list .rt-ScrollAreaViewport")).toHaveCount(0)
    expect(
        await page
            .getByRole("tree", { name: "Objects" })
            .evaluate((element) => getComputedStyle(element).overflowY)
    ).toBe("auto")
    // The work board is empty until TCW-77 rebuilds the work routes.
    await expect(page.getByRole("treeitem")).toHaveCount(0)

    await page.getByRole("button", { name: "Taxonomy" }).click()
    await expect(page).toHaveURL(`${baseUrl}/taxonomy`)
    await page.getByRole("button", { name: "Capabilities" }).click()
    await expect(page).toHaveURL(`${baseUrl}/capabilities`)
    await page.getByRole("button", { name: "Work" }).click()
    await expect(page).toHaveURL(`${baseUrl}/work`)
})

test("applies and persists light, dark, and live system preferences before React paint", async ({
    page,
    context,
}) => {
    await page.emulateMedia({ colorScheme: "dark" })
    await page.goto(baseUrl, { waitUntil: "domcontentloaded" })
    await expect
        .poll(() => page.evaluate(() => document.documentElement.className))
        .toContain("dark")
    await expect(page.getByRole("tree", { name: "Objects" })).toBeVisible()
    await stableScreenshot(page, "shell-system-dark.png")

    await page.getByRole("button", { name: "Settings" }).click()
    await page.getByRole("radio", { name: "Light" }).click()
    await expect(page.locator("html")).toHaveClass(/light/)
    await page.reload()
    await expect(page.locator("html")).toHaveClass(/light/)
    await expect(page.getByRole("tree", { name: "Objects" })).toBeVisible()
    await stableScreenshot(page, "shell-explicit-light.png")

    await page.getByRole("button", { name: "Settings" }).click()
    await page.getByRole("radio", { name: "System" }).click()
    await expect(page.locator("html")).toHaveClass(/dark/)
    await page.emulateMedia({ colorScheme: "light" })
    await expect(page.locator("html")).toHaveClass(/light/)

    const sibling = await context.newPage()
    await sibling.goto(baseUrl)
    await sibling.evaluate(() => localStorage.setItem("tcw.theme", "dark"))
    await expect(page.locator("html")).toHaveClass(/dark/)
    await sibling.close()
    await page.getByRole("button", { name: "Settings" }).click()
    await page.getByRole("radio", { name: "System" }).click({ force: true })
    await page.keyboard.press("Escape")

    await page.setViewportSize({ width: 720, height: 900 })
    await page.getByRole("button", { name: "Settings" }).focus()
    await page.keyboard.press("Enter")
    await expect(page.getByRole("radio", { name: "System" })).toBeVisible()
    await page.keyboard.press("Escape")
    await expect(page.getByRole("radio", { name: "System" })).toBeHidden()
    await page.getByRole("button", { name: "Settings" }).click()
    await stableScreenshot(page, "settings-responsive.png")
    await page.keyboard.press("Escape")
})

test("keeps API and SPA routing separate", async ({ request }) => {
    const unknownApi = await request.get(`${baseUrl}/api/not-a-route`)
    expect(unknownApi.status()).toBe(404)
    const deepLink = await request.get(`${baseUrl}/work/browser-parity-fixture`)
    expect(deepLink.status()).toBe(200)
    expect(await deepLink.text()).toContain('<div id="root"></div>')
})

test("creates and edits Taxonomy and Capability objects", async ({ page }) => {
    await page.goto(`${baseUrl}/taxonomy`)
    await page.getByRole("button", { name: "+ Create Taxonomy" }).click()
    await page.getByLabel("Name").fill("React Vocabulary")
    await page.getByLabel("Slug").fill("react-vocabulary")
    await page
        .getByLabel("Markdown", { exact: true })
        .fill("Taxonomy from React.")
    await page.getByRole("button", { name: "Save" }).click()
    await expect(
        page.getByText("React Vocabulary", { exact: true })
    ).toBeVisible()
    const taxonomyWidths = await page
        .locator(".list, .tree-row .item")
        .evaluateAll((elements) =>
            elements
                .slice(0, 2)
                .map((element) => element.getBoundingClientRect().width)
        )
    expect(taxonomyWidths[1]).toBeGreaterThan(taxonomyWidths[0] * 0.8)
    await page.getByText("React Vocabulary", { exact: true }).click()
    await expect(
        page.locator(".item-taxonomy .modified-at").first()
    ).toContainText("Modified at")
    await expect(page.locator(".detail-head .modified-at")).toContainText(
        "Modified at"
    )
    await page.getByRole("button", { name: "Edit", exact: true }).click()
    await page.getByLabel("Name").fill("React Vocabulary Edited")
    await page.getByRole("button", { name: "Save" }).click()
    await expect(
        page.getByRole("heading", { name: "React Vocabulary Edited" })
    ).toBeVisible()

    await page.getByRole("button", { name: "Capabilities" }).click()
    await page.getByRole("button", { name: "+ Create Capabilities" }).click()
    await page.getByLabel("Path").fill("react/native-client")
    await page.getByLabel("Name").fill("Native client")
    await page.getByLabel("Status").click()
    await page.getByRole("option", { name: "Supported" }).click()
    await page
        .getByLabel("Markdown", { exact: true })
        .fill("Capability from React.")
    await page.getByRole("button", { name: "Save" }).click()
    await expect(page.getByText("Native client", { exact: true })).toBeVisible()
    const capabilityWidths = await page
        .locator(".list, .tree-row .item")
        .evaluateAll((elements) =>
            elements
                .slice(0, 2)
                .map((element) => element.getBoundingClientRect().width)
        )
    expect(capabilityWidths[1]).toBeGreaterThan(capabilityWidths[0] * 0.8)
    const capabilityGap = await page
        .locator(".tree-row")
        .evaluateAll((rows) => {
            const parent = rows[0].getBoundingClientRect()
            const child = rows[1].getBoundingClientRect()
            return child.top - parent.bottom
        })
    expect(capabilityGap).toBeGreaterThan(6.5)
    expect(capabilityGap).toBeLessThan(8)
    await page.getByText("Native client", { exact: true }).click()
    await expect(
        page.locator(".item-capabilities .modified-at").first()
    ).toContainText("Modified at")
    await expect(page.locator(".detail-head .modified-at")).toContainText(
        "Modified at"
    )
    await page.getByRole("button", { name: "Edit", exact: true }).click()
    await page.getByLabel("Priority").click()
    await page.getByRole("option", { name: "P1" }).click()
    await page.getByRole("button", { name: "Save" }).click()
    await expect(page.locator(".fields")).toContainText("P1")
})

test("searches references and surfaces targeted validation warnings", async ({
    page,
    request,
}) => {
    for (let index = 0; index < 24; index += 1) {
        const result = await request.post(`${baseUrl}/api/taxonomy`, {
            data: {
                name: `Useful scrolling feature ${index}`,
                slug: `use-scrolling-feature-${index}`,
                kind: "Feature",
                vocabulary: ["react-vocabulary"],
            },
        })
        expect(result.ok()).toBeTruthy()
    }
    const feature = await request.post(`${baseUrl}/api/taxonomy`, {
        data: {
            name: "Useful feature",
            slug: "use-feature",
            kind: "Feature",
            vocabulary: ["react-vocabulary"],
        },
    })
    expect(feature.ok()).toBeTruthy()
    await page.goto(`${baseUrl}/capabilities/react/native-client`)
    await page.getByRole("button", { name: "Edit", exact: true }).click()
    const featureInput = page.getByRole("combobox", { name: "Feature" })
    await featureInput.fill("use")
    await expect(page.locator(".reference-results strong").first()).toHaveText(
        /use/i
    )
    const dropdown = page.locator(".reference-results")
    await expect(dropdown).toBeVisible()
    const dropdownStyle = await dropdown.evaluate((element) => {
        const style = getComputedStyle(element)
        return {
            background: style.backgroundColor,
            position: style.position,
            zIndex: Number(style.zIndex),
            scrolls: element.scrollHeight > element.clientHeight,
        }
    })
    expect(dropdownStyle.background).not.toBe("rgba(0, 0, 0, 0)")
    expect(dropdownStyle.position).toBe("absolute")
    expect(dropdownStyle.zIndex).toBeGreaterThan(0)
    expect(dropdownStyle.scrolls).toBeTruthy()
    await dropdown.evaluate((element) =>
        element.scrollTo(0, element.scrollHeight)
    )
    expect(
        await dropdown.evaluate(
            (element) => getComputedStyle(element).backgroundColor
        )
    ).toBe(dropdownStyle.background)
    await featureInput.press("Enter")
    await expect(featureInput).toHaveValue("use-feature")
    await page
        .getByRole("combobox", { name: "Superseded by" })
        .fill("missing-capability")
    // A reference that resolves to nothing is refused at write time, and the
    // form keeps the draft so it can be corrected.
    await page.getByRole("button", { name: "Save" }).click()
    await expect(page.getByRole("alert")).toContainText("Validation errors")
    await expect(page.getByRole("alert")).toContainText("missing-capability")
    await page.getByRole("combobox", { name: "Superseded by" }).fill("")
    await page.getByRole("button", { name: "Save" }).click()
    await expect(page.getByRole("alert")).toHaveCount(0)
    await expect(page.locator(".toast")).toHaveText("Saved")
    const saved = await (
        await request.get(`${baseUrl}/api/capabilities/react%2Fnative-client`)
    ).json()
    expect(saved.capability.fields.Feature).toBe("use-feature")
})

test("applies axis-specific facets and browser history navigation", async ({
    page,
}) => {
    // The Work facets are gone with the work routes until TCW-77.
    await page.goto(`${baseUrl}/work`)
    await page.getByRole("button", { name: "Taxonomy" }).click()
    await page.getByRole("button", { name: "Kind" }).click()
    await page.getByRole("checkbox", { name: "Vocabulary" }).click()
    await expect(
        page.getByText("React Vocabulary Edited", { exact: true })
    ).toBeVisible()
    await page.getByRole("button", { name: "Capabilities" }).click()
    await page.goBack()
    await expect(page).toHaveURL(`${baseUrl}/taxonomy`)
    await page.goForward()
    await expect(page).toHaveURL(`${baseUrl}/capabilities`)
})

import { expect, test } from "@playwright/test"
import { spawn, spawnSync, type ChildProcess } from "node:child_process"
import { mkdtemp } from "node:fs/promises"
import { tmpdir } from "node:os"
import { join } from "node:path"

const PUBLIC_PORT = 8891
const baseUrl = `http://127.0.0.1:${PUBLIC_PORT}`
let server: ChildProcess
let serverError = ""

test.describe.configure({ mode: "serial" })

test.beforeAll(async () => {
    const nodeRoot = await mkdtemp(join(tmpdir(), "tcw-playwright-"))
    spawnSync("git", ["init", "-q"], { cwd: nodeRoot, stdio: "inherit" })
    const initialized = spawnSync("tcw", ["init", "--id", "playwright-node"], {
        cwd: nodeRoot,
        encoding: "utf8",
    })
    if (initialized.status !== 0) throw new Error(initialized.stderr)
    const registeredTag = spawnSync("tcw", ["work", "tags", "add", "browser"], {
        cwd: nodeRoot,
        encoding: "utf8",
    })
    if (registeredTag.status !== 0) throw new Error(registeredTag.stderr)
    const created = spawnSync(
        "tcw",
        [
            "work",
            "new",
            "Browser parity fixture",
            "--effort",
            "low",
            "--complexity",
            "low",
            "--tag",
            "browser",
        ],
        { cwd: nodeRoot, encoding: "utf8" }
    )
    if (created.status !== 0) throw new Error(created.stderr)
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
    await expect(
        page.getByText("Browser parity fixture", { exact: true })
    ).toBeVisible()

    const workItem = page.getByRole("treeitem", {
        name: /Browser parity fixture/,
    })
    await workItem.hover()
    await page.getByRole("button", { name: "Copy slug to clipboard" }).hover()
    await expect(page.getByRole("tooltip")).toHaveText("Copy slug")
    const tooltipSize = await page
        .getByRole("tooltip")
        .evaluate((element) => element.getBoundingClientRect())
    expect(tooltipSize.width).toBeGreaterThan(tooltipSize.height)

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
    await expect(page).toHaveScreenshot("shell-system-dark.png", {
        animations: "disabled",
    })

    await page.getByRole("button", { name: "Settings" }).click()
    await page.getByRole("radio", { name: "Light" }).click()
    await expect(page.locator("html")).toHaveClass(/light/)
    await page.reload()
    await expect(page.locator("html")).toHaveClass(/light/)
    await expect(page).toHaveScreenshot("shell-explicit-light.png", {
        animations: "disabled",
    })

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
    await expect(page).toHaveScreenshot("settings-responsive.png", {
        animations: "disabled",
    })
    await page.keyboard.press("Escape")
})

test("filters work without losing the established tree interaction", async ({
    page,
}) => {
    await page.goto(`${baseUrl}/work`)
    const filter = page.getByPlaceholder("Filter")
    await filter.fill("Browser parity")
    await expect(
        page.getByText("Browser parity fixture", { exact: true })
    ).toBeVisible()
    await filter.fill("no such work item")
    await expect(
        page.getByText("Browser parity fixture", { exact: true })
    ).toBeHidden()
    await expect(
        page.getByRole("button", { name: "Clear filter" })
    ).toBeVisible()
    await page.getByRole("button", { name: "Clear filter" }).click()
    await expect(filter).toHaveValue("")
    await expect(
        page.getByRole("button", { name: "Clear filter" })
    ).toHaveCount(0)
})

test("keeps API and SPA routing separate", async ({ request }) => {
    const unknownApi = await request.get(`${baseUrl}/api/not-a-route`)
    expect(unknownApi.status()).toBe(404)
    const deepLink = await request.get(`${baseUrl}/work/browser-parity-fixture`)
    expect(deepLink.status()).toBe(200)
    expect(await deepLink.text()).toContain('<div id="root"></div>')
})

test("creates and edits Work with live Markdown and dirty navigation protection", async ({
    page,
}) => {
    await page.goto(`${baseUrl}/work`)
    await page.getByRole("button", { name: "+ Create Work" }).click()
    await page.getByLabel("Title").fill("React-created work")
    await page
        .getByLabel("Markdown", { exact: true })
        .fill("# Native preview\n\nReact owns this draft.")
    await expect(
        page
            .locator(".md-preview")
            .getByRole("heading", { name: "Native preview" })
    ).toBeVisible()

    page.once("dialog", async (dialog) => dialog.dismiss())
    await page.getByRole("button", { name: "Taxonomy" }).click()
    await expect(page).toHaveURL(`${baseUrl}/work`)
    await page.getByRole("button", { name: "Save" }).click()
    await expect(
        page.getByText("React-created work", { exact: true })
    ).toBeVisible()

    await page.getByText("React-created work", { exact: true }).click()
    await page.locator(".edit-btn").click()
    await page.getByLabel("Title").fill("React-edited work")
    await page.getByRole("button", { name: "Save" }).click()
    await expect(
        page.getByRole("heading", { name: "React-edited work" })
    ).toBeVisible()
})

test("shows validation errors without dropping a Work draft", async ({
    page,
}) => {
    await page.goto(`${baseUrl}/work`)
    await page.getByRole("button", { name: "+ Create Work" }).click()
    await page.getByLabel("Markdown", { exact: true }).fill("draft stays here")
    await page.getByRole("button", { name: "Save" }).click()
    await expect(page.getByText("Title is required")).toBeVisible()
    await expect(page.getByLabel("Markdown", { exact: true })).toHaveValue(
        "draft stays here"
    )
    await expect(page).toHaveScreenshot("validation-editor.png", {
        animations: "disabled",
    })
    page.once("dialog", async (dialog) => dialog.accept())
    await page.getByRole("button", { name: "Cancel" }).click()
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
    await page.getByRole("button", { name: "Save" }).click()
    await expect(page.getByRole("alert")).toContainText(
        "Saved with validation issues"
    )
    await expect(page.getByRole("alert")).toContainText("missing-capability")
    const saved = await (
        await request.get(`${baseUrl}/api/capabilities/react%2Fnative-client`)
    ).json()
    expect(saved.capability.fields.Feature).toBe("use-feature")
    await page.getByRole("button", { name: "Edit", exact: true }).click()
    await page.getByRole("combobox", { name: "Superseded by" }).fill("")
    await page.getByRole("button", { name: "Save" }).click()
    await expect(page.getByRole("alert")).toHaveCount(0)
    await expect(page.locator(".toast")).toHaveText("Saved")
})

test("applies axis-specific facets and browser history navigation", async ({
    page,
}) => {
    await page.goto(`${baseUrl}/work`)
    await page.getByRole("button", { name: "Status (2)" }).click()
    await expect(page.getByRole("checkbox", { name: "Backlog" })).toBeChecked()
    await expect(page.getByRole("checkbox", { name: "Active" })).toBeChecked()
    await expect(
        page.getByRole("checkbox", { name: "Completed" })
    ).not.toBeChecked()
    await expect(page).toHaveScreenshot("status-filter-popover.png", {
        animations: "disabled",
    })
    await page.keyboard.press("Escape")
    const sort = page.getByRole("combobox", { name: "Sort work items" })
    await expect(sort).toContainText("Name")
    await page.getByRole("button", { name: "Sort descending" }).click()
    await expect(
        page.getByRole("button", { name: "Sort ascending" })
    ).toBeVisible()
    await sort.click()
    await page.getByRole("option", { name: "Modified" }).click()
    await expect(sort).toContainText("Modified")
    await page.getByRole("button", { name: "Tags" }).click()
    await page.getByRole("checkbox", { name: "browser" }).click()
    await expect(page).toHaveScreenshot("filters-popover.png", {
        animations: "disabled",
    })
    await expect(
        page.getByText("Browser parity fixture", { exact: true })
    ).toBeVisible()
    await expect(
        page.getByText("React-edited work", { exact: true })
    ).toBeHidden()

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

test("edits lifecycle artifacts and preserves a draft across a stale write", async ({
    page,
    request,
}) => {
    const work = await request.get(`${baseUrl}/api/work`)
    const fixture = (
        (await work.json()) as Array<{ slug: string; title: string }>
    ).find((item) => item.title === "Browser parity fixture")!
    for (const name of ["spec", "plan"]) {
        const response = await request.put(
            `${baseUrl}/api/work/${fixture.slug}/artifacts/${name}`,
            {
                data: {
                    name,
                    content: `# ${name}\n`,
                    mediaType: "text/markdown",
                },
            }
        )
        expect(response.ok()).toBeTruthy()
    }
    const sidecar = await request.put(
        `${baseUrl}/api/work/${fixture.slug}/sidecars/capabilities.yaml`,
        {
            data: {
                name: "capabilities.yaml",
                content: "changed: []\n",
                mediaType: "application/yaml",
            },
        }
    )
    expect(sidecar.ok()).toBeTruthy()

    await page.goto(`${baseUrl}/work/${fixture.slug}`)
    await expect(
        page.getByRole("heading", { name: "Browser parity fixture", level: 2 })
    ).toBeVisible()
    await page.getByRole("button", { name: "Edit spec" }).click()
    await page
        .getByLabel("Markdown", { exact: true })
        .fill("# Updated specification\n")
    await page.getByRole("button", { name: "Save" }).click()
    const savedSpec = await request.get(
        `${baseUrl}/api/work/${fixture.slug}/artifacts/spec`
    )
    expect((await savedSpec.json()).content).toContain("Updated specification")

    await page.locator(".sidecar-edit-btn").click()
    await page.getByLabel("Markdown", { exact: true }).fill("changed:\n- web\n")
    await page.getByRole("button", { name: "Save" }).click()
    const savedSidecar = await request.get(
        `${baseUrl}/api/work/${fixture.slug}/sidecars/capabilities.yaml`
    )
    expect((await savedSidecar.json()).content).toContain("- web")

    await page.locator(".edit-btn").click()
    await page.getByLabel("Title").fill("Local stale draft")
    const detail = await (
        await request.get(`${baseUrl}/api/work/${fixture.slug}`)
    ).json()
    const external = await request.patch(
        `${baseUrl}/api/work/${fixture.slug}`,
        {
            data: { revision: detail.coreRevision, fields: { priority: 77 } },
        }
    )
    expect(external.ok()).toBeTruthy()
    await page.getByRole("button", { name: "Save" }).click()
    await expect(page.getByText("Stale write detected")).toBeVisible()
    await expect(page.getByLabel("Title")).toHaveValue("Local stale draft")
    await expect(page).toHaveScreenshot("stale-write-conflict.png", {
        animations: "disabled",
    })
    page.once("dialog", async (dialog) => dialog.accept())
    await page.getByRole("button", { name: "Refresh from server" }).click()
    await expect(page.locator(".fields")).toContainText("77")
})

test("runs Work start and complete lifecycle controls", async ({
    page,
    request,
}) => {
    const work = await request.get(`${baseUrl}/api/work`)
    const fixture = (
        (await work.json()) as Array<{ slug: string; title: string }>
    ).find((item) => item.title === "Browser parity fixture")!
    await page.goto(`${baseUrl}/work/${fixture.slug}`)
    await page.getByRole("button", { name: "Start", exact: true }).click()
    await page
        .locator(".modal-box")
        .getByRole("button", { name: "Start", exact: true })
        .click()
    await expect(
        page.getByRole("button", { name: "Complete", exact: true })
    ).toBeVisible()

    const outcome = await request.put(
        `${baseUrl}/api/work/${fixture.slug}/artifacts/outcome`,
        {
            data: {
                name: "outcome",
                content: "# Outcome\n\nVerified.\n",
                mediaType: "text/markdown",
            },
        }
    )
    expect(outcome.ok()).toBeTruthy()
    await page.locator(".action-btn.complete").click()
    await expect(
        page
            .locator(".modal-box")
            .getByRole("heading", { name: "Complete Work Item" })
    ).toBeVisible()
    await expect(page).toHaveScreenshot("lifecycle-dialog.png", {
        animations: "disabled",
    })
    await page.getByLabel("Resolution").click()
    await page.getByRole("option", { name: "done" }).click()
    for (const checkbox of await page
        .getByRole("dialog")
        .getByRole("checkbox")
        .all())
        await checkbox.click()
    await page
        .locator(".modal-box")
        .getByRole("button", { name: "Complete", exact: true })
        .click()
    await expect(
        page.getByText("completed", { exact: true }).first()
    ).toBeVisible()
})

test("drops a backlog Work item through the confirmation modal", async ({
    page,
}) => {
    await page.goto(`${baseUrl}/work`)
    await page.getByText("React-edited work", { exact: true }).click()
    await page.getByRole("button", { name: "Drop" }).click()
    await page
        .locator(".modal-box")
        .getByRole("button", { name: "Drop" })
        .click()
    await expect(
        page.getByText("React-edited work", { exact: true })
    ).toHaveCount(0)
})

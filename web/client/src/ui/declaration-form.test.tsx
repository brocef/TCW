import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { ThemeProvider } from "../theme"
import { fakeFetch } from "../test-fixtures"
import { DeclarationSection } from "./declaration-form"

const references = {
    work: [],
    taxonomy: [],
    capabilities: [{ path: "web/editing", name: "Editing" }],
}

function renderSection(editable = true, onSaved = vi.fn()) {
    render(
        <ThemeProvider>
            <DeclarationSection
                folder="x"
                references={references}
                editable={editable}
                onSaved={onSaved}
                onDirty={() => undefined}
            />
        </ThemeProvider>
    )
    return onSaved
}

test("the six lists save in one request, and the form says comments go", async () => {
    const fetch = fakeFetch([
        [
            /^GET /,
            200,
            {
                revision: "r1",
                present: true,
                problem: null,
                capabilities: { new: ["web/new"], changed: [], removed: [] },
                taxonomy: { new: [], changed: [], removed: [] },
            },
        ],
        [/^PUT /, 200, { revision: "r2" }],
    ])
    globalThis.fetch = fetch as unknown as typeof globalThis.fetch
    const onSaved = renderSection()
    expect(await screen.findByText("web/new")).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: "Edit" }))
    expect(
        screen.getByText(
            "Comments in this file are not kept when the form saves it."
        )
    ).toBeInTheDocument()
    expect(screen.getAllByRole("combobox")).toHaveLength(6)
    const changed = screen.getByRole("combobox", {
        name: "Capabilities: changed",
    })
    fireEvent.change(changed, { target: { value: "web/editing" } })
    fireEvent.keyDown(changed, { key: "Escape" })
    fireEvent.keyDown(changed, { key: "Enter" })
    fireEvent.click(screen.getByRole("button", { name: "Save" }))
    await waitFor(() => expect(onSaved).toHaveBeenCalled())
    const put = fetch.calls.find((call) => call.method === "PUT")!
    expect(put.path).toBe("/api/work/x/declaration")
    expect(put.body).toEqual({
        capabilities: {
            new: ["web/new"],
            changed: ["web/editing"],
            removed: [],
        },
        taxonomy: { new: [], changed: [], removed: [] },
        revision: "r1",
    })
})

test("a file the parser rejects opens as text with the parser's message", async () => {
    const fetch = fakeFetch([
        [
            /^GET /,
            200,
            {
                revision: "r1",
                present: true,
                problem: "capabilities.yaml: unknown key 'nope'",
                content: "nope: 1\n",
            },
        ],
        [/^PUT /, 200, { revision: "r2" }],
    ])
    globalThis.fetch = fetch as unknown as typeof globalThis.fetch
    const onSaved = renderSection()
    expect(await screen.findByText(/unknown key 'nope'/)).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: "Edit" }))
    fireEvent.change(screen.getByRole("textbox", { name: "Markdown" }), {
        target: { value: "new: [web/x]\n" },
    })
    fireEvent.click(screen.getByRole("button", { name: "Save" }))
    await waitFor(() => expect(onSaved).toHaveBeenCalled())
    expect(fetch.calls.find((call) => call.method === "PUT")).toMatchObject({
        path: "/api/work/x/files/capabilities.yaml",
        body: { content: "new: [web/x]\n", revision: "r1" },
    })
})

test("a page that offers no editing shows the lists alone", async () => {
    globalThis.fetch = fakeFetch([
        [
            /^GET /,
            200,
            {
                revision: null,
                present: false,
                problem: null,
                capabilities: { new: [], changed: [], removed: [] },
                taxonomy: { new: [], changed: [], removed: [] },
            },
        ],
    ]) as unknown as typeof globalThis.fetch
    renderSection(false)
    expect(await screen.findByText("Nothing declared.")).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "Create" })).toBeNull()
})

const lists = (revision: string, newPaths: string[]) => ({
    revision,
    present: true,
    problem: null,
    capabilities: { new: newPaths, changed: [], removed: [] },
    taxonomy: { new: [], changed: [], removed: [] },
})

test("refreshing after a stale save replaces the draft, so the next save does not overwrite", async () => {
    // The file on disk: r1 at first, then another writer makes it r2.
    let onDisk = lists("r1", ["web/first"])
    const puts: Array<Record<string, unknown>> = []
    globalThis.fetch = vi.fn(async (_input: unknown, init?: RequestInit) => {
        if (init?.method === "PUT") {
            const body = JSON.parse(String(init.body))
            puts.push(body)
            if (body.revision !== onDisk.revision)
                return {
                    ok: false,
                    status: 409,
                    statusText: "409",
                    json: async () => ({
                        error: "changed",
                        code: "stale-revision",
                    }),
                }
            return {
                ok: true,
                status: 200,
                statusText: "200",
                json: async () => ({}),
            }
        }
        return {
            ok: true,
            status: 200,
            statusText: "200",
            json: async () => onDisk,
        }
    }) as unknown as typeof globalThis.fetch
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(true)
    try {
        renderSection()
        expect(await screen.findByText("web/first")).toBeInTheDocument()
        fireEvent.click(screen.getByRole("button", { name: "Edit" }))
        // Meanwhile another writer changes the file.
        onDisk = lists("r2", ["web/theirs"])
        const added = screen.getByRole("combobox", {
            name: "Capabilities: new",
        })
        fireEvent.change(added, { target: { value: "web/mine" } })
        fireEvent.keyDown(added, { key: "Enter" })
        fireEvent.click(screen.getByRole("button", { name: "Save" }))
        expect(await screen.findByText("Stale write detected")).toBeVisible()
        fireEvent.click(
            screen.getByRole("button", { name: "Refresh from server" })
        )
        expect(confirm).toHaveBeenCalled()
        // The form now holds the file as it is, and no conflict.
        expect(await screen.findByText("web/theirs")).toBeInTheDocument()
        expect(screen.queryByText("Stale write detected")).toBeNull()
        expect(screen.queryByText("web/mine")).toBeNull()
        fireEvent.click(screen.getByRole("button", { name: "Save" }))
        await waitFor(() => expect(puts).toHaveLength(2))
        expect(puts[1]).toMatchObject({
            revision: "r2",
            capabilities: { new: ["web/theirs"] },
        })
    } finally {
        confirm.mockRestore()
    }
})

test("a list holding text it will not keep holds back the save, and says why", async () => {
    const fetch = fakeFetch([
        [/^GET /, 200, lists("r1", [])],
        [/^PUT /, 200, { revision: "r2" }],
    ])
    globalThis.fetch = fetch as unknown as typeof globalThis.fetch
    const onSaved = renderSection()
    fireEvent.click(await screen.findByRole("button", { name: "Edit" }))
    const changed = screen.getByRole("combobox", {
        name: "Capabilities: changed",
    })
    fireEvent.change(changed, { target: { value: "no/such/path" } })
    fireEvent.click(screen.getByRole("button", { name: "Save" }))
    expect(
        await screen.findByText(
            /Capabilities: changed: no\/such\/path is not one of the suggestions/
        )
    ).toBeInTheDocument()
    expect(changed).toHaveValue("no/such/path")
    expect(fetch.calls.some((call) => call.method === "PUT")).toBe(false)
    expect(onSaved).not.toHaveBeenCalled()
})

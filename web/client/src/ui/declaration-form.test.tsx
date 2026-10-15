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

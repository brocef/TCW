import {
    fireEvent,
    render,
    screen,
    waitFor,
    within,
} from "@testing-library/react"
import { vi } from "vitest"
import { MemoryRouter, useLocation, useNavigate } from "react-router"
import { ThemeProvider } from "../theme"
import { fakeFetch, project, workDetail, workItem } from "../test-fixtures"
import type { TProject } from "../model/types"
import { App } from "./app"

function Where() {
    const navigate = useNavigate()
    return (
        <>
            <output data-testid="where">{useLocation().pathname}</output>
            <button type="button" onClick={() => void navigate(-1)}>
                Browser back
            </button>
        </>
    )
}

function renderApp(path = "/work") {
    return render(
        <ThemeProvider>
            <MemoryRouter initialEntries={[path]}>
                <App />
                <Where />
            </MemoryRouter>
        </ThemeProvider>
    )
}

const NO_DECLARATION = [
    /declaration$/,
    200,
    {
        revision: null,
        present: false,
        problem: null,
        capabilities: { new: [], changed: [], removed: [] },
        taxonomy: { new: [], changed: [], removed: [] },
    },
] as [RegExp, number, unknown]

function serve(
    overrides: Partial<TProject> = {},
    extra: Array<[string | RegExp, number, unknown]> = []
) {
    const fetch = fakeFetch([
        NO_DECLARATION,
        ...extra,
        ["/api/project$", 200, project(overrides)],
        [
            "/api/work",
            200,
            {
                items: [workItem("2026-10-01-a", { title: "Alpha" })],
                people: {},
                fallback: false,
            },
        ],
        ["/api/taxonomy$", 200, []],
        ["/api/capabilities$", 200, []],
        ["/api/resolve", 200, {}],
    ])
    globalThis.fetch = fetch as unknown as typeof globalThis.fetch
    return fetch
}

test("renders the established three-axis shell", async () => {
    serve()
    renderApp()
    expect(screen.getByRole("button", { name: "Taxonomy" })).toBeInTheDocument()
    expect(
        screen.getByRole("button", { name: "Capabilities" })
    ).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Work" })).toBeInTheDocument()
    expect(screen.getByRole("tree", { name: "Objects" })).toBeInTheDocument()
    expect(await screen.findByText("Alpha")).toBeInTheDocument()
})

test.each(["Taxonomy", "Capabilities"])(
    "renders the %s create button above its object list",
    async (axis) => {
        serve()
        renderApp()
        fireEvent.click(screen.getByRole("button", { name: axis }))
        const createButton = await screen.findByRole("button", {
            name: `+ Create ${axis}`,
        })
        const tree = screen.getByRole("tree", { name: "Objects" })
        expect(createButton.compareDocumentPosition(tree)).toBe(
            Node.DOCUMENT_POSITION_FOLLOWING
        )
    }
)

test("places the accessible Settings control immediately after Work", () => {
    serve()
    renderApp()
    const work = screen.getByRole("button", { name: "Work" })
    const settings = screen.getByRole("button", { name: "Settings" })
    expect(work.compareDocumentPosition(settings)).toBe(
        Node.DOCUMENT_POSITION_FOLLOWING
    )
})

test("applies and persists an appearance choice without leaving the shell", async () => {
    serve()
    localStorage.clear()
    renderApp()
    fireEvent.click(screen.getByRole("button", { name: "Settings" }))
    fireEvent.click(await screen.findByRole("radio", { name: "Dark" }))
    expect(localStorage.getItem("tcw.theme")).toBe("dark")
    expect(document.documentElement).toHaveClass("dark")
    expect(screen.getByRole("tree", { name: "Objects" })).toBeInTheDocument()
})

test("shows and applies the accessible filter clear action", () => {
    serve()
    renderApp()
    const filter = screen.getByPlaceholderText("Filter")
    expect(
        screen.queryByRole("button", { name: "Clear filter" })
    ).not.toBeInTheDocument()
    fireEvent.change(filter, { target: { value: "needle" } })
    const clear = screen.getByRole("button", { name: "Clear filter" })
    fireEvent.click(clear)
    expect(filter).toHaveValue("")
    expect(clear).not.toBeInTheDocument()
})

const boardPaths = (fetch: ReturnType<typeof serve>) =>
    fetch.calls
        .map((call) => call.path)
        .filter((path) => /^\/api\/work(\?|$)/.test(path))

test("the board loads with the default query, and a terminal stage loads all", async () => {
    const fetch = serve()
    renderApp()
    await screen.findByText("Alpha")
    expect(boardPaths(fetch)).toEqual(["/api/work"])
    fireEvent.click(screen.getByRole("button", { name: /^Stage/ }))
    fireEvent.click(await screen.findByRole("checkbox", { name: "done" }))
    await waitFor(() => expect(boardPaths(fetch)).toContain("/api/work?all=1"))
})

test("ticking a tag asks the backend for the items carrying it", async () => {
    const fetch = serve()
    renderApp()
    await screen.findByText("Alpha")
    fireEvent.click(screen.getByRole("button", { name: /^Tags/ }))
    fireEvent.click(await screen.findByRole("checkbox", { name: "ui" }))
    await waitFor(() => expect(boardPaths(fetch)).toContain("/api/work?tag=ui"))
})

test("the stage filter offers no stage only when the backend owns records", async () => {
    serve()
    const { unmount } = renderApp()
    await screen.findByText("Alpha")
    fireEvent.click(screen.getByRole("button", { name: /^Stage/ }))
    await screen.findByRole("checkbox", { name: "ask" })
    expect(screen.queryByRole("checkbox", { name: "(no stage)" })).toBeNull()
    unmount()
    serve({ recordOwner: "backend" })
    renderApp()
    await screen.findByText("Alpha")
    fireEvent.click(screen.getByRole("button", { name: /^Stage/ }))
    expect(
        await screen.findByRole("checkbox", { name: "(no stage)" })
    ).toBeInTheDocument()
})

test("a fallback board lists folders under a banner with Retry", async () => {
    const fetch = serve({}, [
        [
            "/api/work",
            200,
            {
                items: [
                    {
                        "full-id": "p.work/2026-10-01-a",
                        owner: "p",
                        path: "/w/2026-10-01-a",
                    },
                ],
                people: {},
                fallback: true,
                unavailable: "Jira is unreachable",
            },
        ],
    ])
    renderApp()
    expect(
        await screen.findByText(
            /The board could not be read: Jira is unreachable/
        )
    ).toBeInTheDocument()
    expect(screen.getByText("stage unavailable")).toBeInTheDocument()
    const before = boardPaths(fetch).length
    fireEvent.click(screen.getByRole("button", { name: "Retry" }))
    await waitFor(() => expect(boardPaths(fetch).length).toBe(before + 1))
})

test("an axis the project does not keep says so", async () => {
    serve({ axes: { work: true, taxonomy: false, capabilities: true } })
    renderApp("/taxonomy")
    expect(
        await screen.findByText("This project keeps no taxonomy.")
    ).toBeInTheDocument()
})

test("a URL naming a Jira key is replaced by the item's folder", async () => {
    serve({}, [
        ["/api/work/X-1$", 200, workDetail("X-1-thing")],
        ["/api/work/X-1-thing$", 200, workDetail("X-1-thing")],
    ])
    renderApp("/work/X-1")
    await waitFor(() =>
        expect(screen.getByTestId("where")).toHaveTextContent("/work/X-1-thing")
    )
    expect(
        await screen.findByRole("heading", { name: "X-1-thing" })
    ).toBeInTheDocument()
})

test("an item is read by its folder and shown read-only", async () => {
    serve({}, [["/api/work/2026-10-01-a$", 200, workDetail("2026-10-01-a")]])
    renderApp()
    fireEvent.click(await screen.findByRole("treeitem", { name: /Alpha/ }))
    expect(await screen.findByText(/^Stage:/)).toBeInTheDocument()
    expect(screen.getByTestId("where")).toHaveTextContent("/work/2026-10-01-a")
})

test("in filesystem mode the item's properties, blocks and comments are editable", async () => {
    serve({}, [["/api/work/2026-10-01-a$", 200, workDetail("2026-10-01-a")]])
    renderApp("/work/2026-10-01-a")
    expect(
        await screen.findByRole("button", { name: "Edit" })
    ).toBeInTheDocument()
    expect(
        screen.getByRole("textbox", { name: "New comment" })
    ).toBeInTheDocument()
    expect(
        screen.getByRole("combobox", { name: "Blocks (add)" })
    ).toBeInTheDocument()
    expect(
        screen.getByRole("button", { name: "+ New item" })
    ).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "Tickets" })).toBeNull()
})

test("when the backend owns the record only the files are editable", async () => {
    serve({ recordOwner: "backend" }, [
        ["/api/work/2026-10-01-a$", 200, workDetail("2026-10-01-a")],
    ])
    renderApp("/work/2026-10-01-a")
    expect(await screen.findByText(/^Stage:/)).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "Edit" })).toBeNull()
    expect(screen.queryByRole("textbox", { name: "New comment" })).toBeNull()
    expect(screen.queryByRole("combobox", { name: "Blocks (add)" })).toBeNull()
    expect(
        within(screen.getByRole("tabpanel")).getByRole("button", {
            name: "Create",
        })
    ).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Tickets" })).toBeInTheDocument()
})

test("Create asks where the new document goes, then edits it", async () => {
    const fetch = serve({}, [
        ["/api/work/2026-10-01-a$", 200, workDetail("2026-10-01-a")],
        [
            /^POST \/api\/work\/2026-10-01-a\/files$/,
            200,
            { path: "ask/ask.md", template: "" },
        ],
    ])
    renderApp("/work/2026-10-01-a")
    fireEvent.click(
        within(await screen.findByRole("tabpanel")).getByRole("button", {
            name: "Create",
        })
    )
    expect(
        await screen.findByRole("heading", { name: "Create ask/ask.md" })
    ).toBeInTheDocument()
    expect(fetch.calls.find((call) => call.method === "POST")?.body).toEqual({
        stage: "ask",
        kind: "document",
    })
})

test("coming back from a stage file's editor shows that stage's tab", async () => {
    serve({}, [
        ["/api/work/2026-10-01-a$", 200, workDetail("2026-10-01-a")],
        [
            /^POST \/api\/work\/2026-10-01-a\/files$/,
            200,
            { path: "lessons/lessons.md", template: "" },
        ],
    ])
    renderApp("/work/2026-10-01-a")
    // The item is at `ask`; the file edited is another stage's.
    fireEvent.mouseDown(await screen.findByRole("tab", { name: "Lessons" }))
    fireEvent.click(
        within(screen.getByRole("tabpanel")).getByRole("button", {
            name: "Create",
        })
    )
    expect(
        await screen.findByRole("heading", {
            name: "Create lessons/lessons.md",
        })
    ).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: "Cancel" }))
    expect(await screen.findByRole("tab", { name: "Lessons" })).toHaveAttribute(
        "aria-selected",
        "true"
    )
})

const allPaths = (fetch: ReturnType<typeof serve>) =>
    fetch.calls
        .map((call) => call.path)
        .filter((path) => path.includes("all=1"))

test("unsaved comment text is asked about before a form replaces the page", async () => {
    const fetch = serve({}, [
        ["/api/work/2026-10-01-a$", 200, workDetail("2026-10-01-a")],
        [
            /^POST \/api\/work\/2026-10-01-a\/files$/,
            200,
            { path: "ask/ask.md", template: "" },
        ],
    ])
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(false)
    try {
        renderApp("/work/2026-10-01-a")
        fireEvent.change(
            await screen.findByRole("textbox", { name: "New comment" }),
            { target: { value: "Half a thought" } }
        )
        // Create on a stage file, and Edit on the properties, both ask.
        fireEvent.click(
            within(screen.getByRole("tabpanel")).getByRole("button", {
                name: "Create",
            })
        )
        fireEvent.click(screen.getByRole("button", { name: "Edit" }))
        expect(confirm).toHaveBeenCalledTimes(2)
        expect(fetch.calls.some((call) => call.method === "POST")).toBe(false)
        expect(
            screen.getByRole("textbox", { name: "New comment" })
        ).toHaveValue("Half a thought")
        // Agreeing to leave opens the form.
        confirm.mockReturnValue(true)
        fireEvent.click(screen.getByRole("button", { name: "Edit" }))
        expect(
            await screen.findByRole("combobox", { name: "Parent" })
        ).toBeInTheDocument()
    } finally {
        confirm.mockRestore()
    }
})

test("a saved new item opens its page without asking about unsaved changes", async () => {
    serve({}, [
        [/^POST \/api\/work$/, 201, { "full-id": "p.work/2026-10-02-new" }],
        ["/api/work/2026-10-02-new$", 200, workDetail("2026-10-02-new")],
    ])
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(false)
    try {
        renderApp("/work")
        fireEvent.click(
            await screen.findByRole("button", { name: "+ New item" })
        )
        fireEvent.change(screen.getByRole("textbox", { name: "Title" }), {
            target: { value: "New" },
        })
        fireEvent.click(screen.getByRole("button", { name: "Save" }))
        await waitFor(() =>
            expect(screen.getByTestId("where")).toHaveTextContent(
                "/work/2026-10-02-new"
            )
        )
        expect(confirm).not.toHaveBeenCalled()
    } finally {
        confirm.mockRestore()
    }
})

test("staying put when the filter asks keeps the filter and the unsaved work", async () => {
    serve({}, [["/api/work/2026-10-01-a$", 200, workDetail("2026-10-01-a")]])
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(false)
    try {
        renderApp("/work/2026-10-01-a")
        fireEvent.change(
            await screen.findByRole("textbox", { name: "New comment" }),
            { target: { value: "Half a thought" } }
        )
        const filter = screen.getByPlaceholderText("Filter")
        fireEvent.change(filter, { target: { value: "z" } })
        expect(confirm).toHaveBeenCalledTimes(1)
        expect(filter).toHaveValue("")
        expect(screen.getByTestId("where")).toHaveTextContent(
            "/work/2026-10-01-a"
        )
        // The comment is still unsaved work: the next way off the page asks.
        fireEvent.click(screen.getByRole("button", { name: "Edit" }))
        expect(confirm).toHaveBeenCalledTimes(2)
        expect(
            screen.getByRole("textbox", { name: "New comment" })
        ).toHaveValue("Half a thought")
    } finally {
        confirm.mockRestore()
    }
})

test("what an adopt hook failed with does not follow the browser back", async () => {
    serve({ recordOwner: "backend" }, [
        [
            "/api/tickets$",
            200,
            {
                tickets: [
                    {
                        key: "X-1",
                        summary: "Please",
                        status: "Inbox",
                        created: "2026-10-01",
                        reporter: "Ann",
                        url: "https://tracker.example/browse/X-1",
                        description: null,
                    },
                ],
                query: "q",
            },
        ],
        [
            /^POST \/api\/tickets/,
            201,
            {
                "full-id": "p.work/X-1-please",
                code: 6,
                problem: "request post hook failed",
            },
        ],
        ["/api/work/X-1-please$", 200, workDetail("X-1-please")],
    ])
    renderApp("/work")
    fireEvent.click(await screen.findByRole("button", { name: "Tickets" }))
    fireEvent.click(await screen.findByRole("button", { name: "Adopt" }))
    expect(
        await screen.findByText("request post hook failed")
    ).toBeInTheDocument()
    await waitFor(() =>
        expect(screen.getByTestId("where")).toHaveTextContent(
            "/work/X-1-please"
        )
    )
    fireEvent.click(screen.getByRole("button", { name: "Browser back" }))
    await waitFor(() =>
        expect(screen.getByTestId("where")).toHaveTextContent(/^\/work$/)
    )
    expect(
        screen.queryByText("request post hook failed")
    ).not.toBeInTheDocument()
})

test("an unsaved declaration draft is asked about before a stage file opens", async () => {
    serve({}, [
        ["/api/work/2026-10-01-a$", 200, workDetail("2026-10-01-a")],
        [
            /^POST \/api\/work\/2026-10-01-a\/files$/,
            200,
            { path: "ask/ask.md", template: "" },
        ],
    ])
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(false)
    try {
        renderApp("/work/2026-10-01-a")
        const section = await screen.findByRole("region", {
            name: "Declaration",
        })
        fireEvent.click(
            await within(section).findByRole("button", { name: "Create" })
        )
        const added = within(section).getByRole("combobox", {
            name: "Capabilities: new",
        })
        fireEvent.change(added, { target: { value: "web/x" } })
        fireEvent.keyDown(added, { key: "Enter" })
        fireEvent.click(
            within(screen.getByRole("tabpanel")).getByRole("button", {
                name: "Create",
            })
        )
        expect(confirm).toHaveBeenCalledTimes(1)
        expect(within(section).getByText("web/x")).toBeInTheDocument()
    } finally {
        confirm.mockRestore()
    }
})

test("every item is read once for an item page, not again on a board reload", async () => {
    const fetch = serve({}, [
        ["/api/work/2026-10-01-a$", 200, workDetail("2026-10-01-a")],
    ])
    renderApp("/work/2026-10-01-a")
    await screen.findByRole("textbox", { name: "New comment" })
    await waitFor(() => expect(allPaths(fetch)).toHaveLength(1))
    fireEvent.click(screen.getByRole("button", { name: /^Tags/ }))
    fireEvent.click(await screen.findByRole("checkbox", { name: "ui" }))
    await waitFor(() => expect(boardPaths(fetch)).toContain("/api/work?tag=ui"))
    expect(allPaths(fetch)).toHaveLength(1)
})

test("the tickets view reads no list of every item, and an adopt's failed hook is shown", async () => {
    const fetch = serve({ recordOwner: "backend" }, [
        [
            "/api/tickets$",
            200,
            {
                tickets: [
                    {
                        key: "X-1",
                        summary: "Please",
                        status: "Inbox",
                        created: "",
                        reporter: "",
                        url: "https://t.example/browse/X-1",
                        description: null,
                    },
                ],
                query: "q",
            },
        ],
        [
            /^POST \/api\/tickets\/X-1\/adopt$/,
            201,
            {
                "full-id": "p.work/X-1-please",
                code: 6,
                problem:
                    "adopted X-1 as p.work/X-1-please, but request post hook failed: exit 1",
            },
        ],
        ["/api/work/X-1-please$", 200, workDetail("X-1-please")],
    ])
    renderApp()
    await screen.findByText("Alpha")
    fireEvent.click(screen.getByRole("button", { name: "Tickets" }))
    fireEvent.click(await screen.findByRole("button", { name: "Adopt" }))
    expect(
        await screen.findByText(/but request post hook failed: exit 1/)
    ).toBeInTheDocument()
    await waitFor(() =>
        expect(screen.getByTestId("where")).toHaveTextContent(
            "/work/X-1-please"
        )
    )
    expect(
        screen.getByText(/but request post hook failed: exit 1/)
    ).toBeVisible()
    // Neither the tickets view nor a page whose record the backend keeps
    // offers items, so the full list is never read.
    expect(allPaths(fetch)).toHaveLength(0)
})

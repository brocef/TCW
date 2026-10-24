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
import {
    capability,
    fakeFetch,
    project,
    term,
    workDetail,
    workItem,
} from "../test-fixtures"
import type { TProject } from "../model/types"
import { App } from "./app"

// Radix's Select scrolls its chosen option into view, which jsdom lacks.
window.HTMLElement.prototype.scrollIntoView = vi.fn()

function Where() {
    const navigate = useNavigate()
    return (
        <>
            <output data-testid="where">{useLocation().pathname}</output>
            <output data-testid="search">{useLocation().search}</output>
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
        ["/api/taxonomy$", 200, { terms: [] }],
        ["/api/capabilities$", 200, { capabilities: [] }],
        ["/api/taxonomy?scope=up$", 200, { terms: [] }],
        ["/api/capabilities?scope=up$", 200, { capabilities: [] }],
        // A list asked for under any other scope (TCW-113 Step 15).
        [/^GET \/api\/taxonomy\?/, 200, { terms: [] }],
        [/^GET \/api\/capabilities\?/, 200, { capabilities: [] }],
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

// What an item blocks is computed from the other items, so it is listed
// and never added from this page.
const blocking = workDetail("2026-10-01-a", {
    item: workItem("2026-10-01-a", { blocks: ["p.work/after"] }),
})

test("in filesystem mode the item's properties and comments are editable", async () => {
    serve({}, [["/api/work/2026-10-01-a$", 200, blocking]])
    renderApp("/work/2026-10-01-a")
    expect(
        await screen.findByRole("button", { name: "Edit" })
    ).toBeInTheDocument()
    expect(
        screen.getByRole("textbox", { name: "New comment" })
    ).toBeInTheDocument()
    expect(screen.queryByRole("combobox", { name: "Blocks (add)" })).toBeNull()
    expect(screen.getByRole("link", { name: "after" })).toBeInTheDocument()
    expect(
        screen.getByRole("button", { name: "+ New item" })
    ).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "Tickets" })).toBeNull()
})

test("when the backend owns the record only the files are editable", async () => {
    serve({ recordOwner: "backend" }, [
        ["/api/work/2026-10-01-a$", 200, blocking],
    ])
    renderApp("/work/2026-10-01-a")
    expect(await screen.findByText(/^Stage:/)).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "Edit" })).toBeNull()
    expect(screen.queryByRole("textbox", { name: "New comment" })).toBeNull()
    expect(screen.queryByRole("combobox", { name: "Blocks (add)" })).toBeNull()
    expect(screen.getByRole("link", { name: "after" })).toBeInTheDocument()
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

describe("tags a parent that is not here may set", () => {
    const why =
        "'p' inherits its configuration (work.tags) from project 'core', which is not on this machine"
    const withheld = { tags: { unavailable: why } }

    test("the Tags filter says the tags could not be read, and why", async () => {
        serve(withheld)
        renderApp()
        await screen.findByText("Alpha")
        fireEvent.click(screen.getByRole("button", { name: /^Tags/ }))
        expect(
            await screen.findByText(`could not be read: ${why}`)
        ).toBeInTheDocument()
        expect(screen.queryByText("none available")).toBeNull()
    })

    test("+ New item and Edit open their forms, with the reason for the tags", async () => {
        serve(withheld, [
            ["/api/work/2026-10-01-a$", 200, workDetail("2026-10-01-a")],
        ])
        renderApp("/work/2026-10-01-a")
        fireEvent.click(await screen.findByRole("button", { name: "Edit" }))
        expect(
            await screen.findByRole("heading", { name: /^Edit / })
        ).toBeInTheDocument()
        expect(
            screen.getByText((text) => text.endsWith(`read: ${why}`))
        ).toBeInTheDocument()
        fireEvent.click(screen.getByRole("button", { name: "Cancel" }))
        fireEvent.click(screen.getByRole("button", { name: "+ New item" }))
        expect(
            await screen.findByRole("textbox", { name: "Title" })
        ).toBeInTheDocument()
        expect(
            screen.getByText((text) => text.endsWith(`read: ${why}`))
        ).toBeInTheDocument()
    })
})

// -- the capability editor edits the declared description (TCW-112 AC 44) ----

function serveCapability(declaredDescription: string | null, body: string) {
    const record = capability("x", {
        name: "X",
        status: "Supported",
        fields: { Status: "Supported" },
        body,
        overrides: "core.capabilities/x",
    })
    const detail = {
        capability: record,
        coreRevision: "r1",
        declaredDescription,
    }
    return serve({}, [
        [/^GET \/api\/capabilities\/x$/, 200, detail],
        [/^PATCH \/api\/capabilities\/x$/, 200, detail],
        ["/api/capabilities$", 200, { capabilities: [record] }],
    ])
}

async function openEditor() {
    renderApp("/capabilities/x")
    fireEvent.click(await screen.findByRole("button", { name: "Edit" }))
    return screen.getByPlaceholderText("Write Markdown...")
}

function patches(fetch: ReturnType<typeof serve>) {
    return fetch.calls.filter((call) => call.method === "PATCH")
}

test("the body field holds the declared description, with a note, and a field-only save sends no body", async () => {
    const fetch = serveCapability("Mine.", "Attached.\n\nMine.")
    expect(await openEditor()).toHaveValue("Mine.")
    expect(
        screen.getByText(
            /also holds attached documents or an inherited description/
        )
    ).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: "Save" }))
    await waitFor(() => expect(patches(fetch)).toHaveLength(1))
    expect(patches(fetch)[0].body).not.toHaveProperty("body")
})

test("a detail declaring no description opens an empty body field", async () => {
    serveCapability(null, "Core body")
    expect(await openEditor()).toHaveValue("")
})

test("a save after editing the body sends the field's text as body", async () => {
    const fetch = serveCapability("Mine.", "Mine.")
    fireEvent.change(await openEditor(), { target: { value: "Changed." } })
    fireEvent.click(screen.getByRole("button", { name: "Save" }))
    await waitFor(() => expect(patches(fetch)).toHaveLength(1))
    expect(patches(fetch)[0].body).toMatchObject({ body: "Changed." })
})

test("a detail whose body is its declared description shows no note", async () => {
    serveCapability("Mine.", "Mine.")
    await openEditor()
    expect(
        screen.queryByText(
            /also holds attached documents or an inherited description/
        )
    ).toBeNull()
})

// -- the pickers ask for the served project's view (TCW-113 plan choice 15) --

test("the Subject picker offers an inherited term the list does not show", async () => {
    const record = capability("x", {
        name: "X",
        status: "Supported",
        fields: { Status: "Supported" },
        body: "",
    })
    const detail = { capability: record, coreRevision: "r1" }
    const inherited = term(
        "money",
        { name: "Money", kind: "Vocabulary" },
        "core"
    )
    const fetch = serve({}, [
        [/^GET \/api\/capabilities\/x$/, 200, detail],
        ["/api/capabilities$", 200, { capabilities: [record] }],
        ["/api/taxonomy?scope=up$", 200, { terms: [inherited] }],
    ])
    renderApp("/capabilities/x")
    fireEvent.click(await screen.findByRole("button", { name: "Edit" }))
    const subject = await screen.findByRole("combobox", { name: "Subject" })
    fireEvent.focus(subject)
    fireEvent.change(subject, { target: { value: "Mon" } })
    // Each option's name and identifier, the typed text highlighted apart.
    await waitFor(() =>
        expect(
            Array.from(document.querySelectorAll('[role="option"]')).map(
                (option) => option.textContent
            )
        ).toEqual(["Moneycore.taxonomy/money"])
    )
    const lists = fetch.calls.map((call) => call.path)
    expect(lists).toContain("/api/taxonomy")
    expect(lists).toContain("/api/taxonomy?scope=up")
})

// -- the scope control and the project filter (TCW-113 Design 6.6) ----------

const FAMILY = {
    own: ["p"],
    up: ["core", "p"],
    down: ["p", "desktop"],
    all: ["core", "p", "desktop"],
}

const listPaths = (fetch: ReturnType<typeof serve>) =>
    fetch.calls
        .map((call) => call.path)
        .filter((path) =>
            /^\/api\/(work|taxonomy|capabilities)(\?|$)/.test(path)
        )

test("choosing down asks for the three lists with scope=down and puts it in the URL", async () => {
    const fetch = serve({ scopes: FAMILY })
    renderApp()
    await screen.findByText("Alpha")
    fireEvent.click(screen.getByRole("combobox", { name: "Scope" }))
    fireEvent.click(await screen.findByRole("option", { name: /^down/ }))
    await waitFor(() =>
        expect(screen.getByTestId("search")).toHaveTextContent("?scope=down")
    )
    await waitFor(() => {
        const paths = listPaths(fetch)
        expect(paths).toContain("/api/work?scope=down")
        expect(paths).toContain("/api/taxonomy?scope=down")
        expect(paths).toContain("/api/capabilities?scope=down")
    })
    // Navigating keeps the scope in the URL.
    fireEvent.click(screen.getByRole("button", { name: "Taxonomy" }))
    await waitFor(() =>
        expect(screen.getByTestId("where")).toHaveTextContent("/taxonomy")
    )
    expect(screen.getByTestId("search")).toHaveTextContent("?scope=down")
})

test("a link naming a scope and a project asks with both", async () => {
    const fetch = serve({ scopes: FAMILY })
    renderApp("/work?scope=down&project=desktop")
    await waitFor(() => {
        const paths = listPaths(fetch)
        expect(paths).toContain("/api/work?scope=down&project=desktop")
        expect(paths).toContain("/api/taxonomy?scope=down&project=desktop")
        expect(paths).toContain("/api/capabilities?scope=down&project=desktop")
    })
    expect(screen.getByRole("combobox", { name: "Project" })).toHaveTextContent(
        "desktop"
    )
})

test("the scope control is not shown for a project with no family", async () => {
    serve()
    renderApp()
    await screen.findByText("Alpha")
    expect(screen.queryByRole("combobox", { name: "Scope" })).toBeNull()
})

test.each(["own", "down"])(
    "under %s the pickers offer the inherited term and no descendant's",
    async (scope) => {
        const record = capability("x", {
            name: "X",
            status: "Supported",
            fields: { Status: "Supported" },
            body: "",
        })
        const inherited = term(
            "money",
            { name: "Money", kind: "Vocabulary" },
            "core"
        )
        const below = term(
            "monitor",
            { name: "Monitor", kind: "Vocabulary" },
            "desktop"
        )
        const fetch = serve({ scopes: FAMILY }, [
            [
                /^GET \/api\/capabilities\/x(\?|$)/,
                200,
                { capability: record, coreRevision: "r1" },
            ],
            ["/api/capabilities$", 200, { capabilities: [record] }],
            ["/api/capabilities?scope=down$", 200, { capabilities: [record] }],
            ["/api/taxonomy?scope=up$", 200, { terms: [inherited] }],
            ["/api/taxonomy?scope=down$", 200, { terms: [below] }],
            [
                /^GET \/api\/work\?all=1$/,
                200,
                { items: [], people: {}, fallback: false },
            ],
        ])
        renderApp(
            scope === "own" ? "/capabilities/x" : "/capabilities/x?scope=down"
        )
        fireEvent.click(await screen.findByRole("button", { name: "Edit" }))
        const subject = await screen.findByRole("combobox", { name: "Subject" })
        fireEvent.focus(subject)
        fireEvent.change(subject, { target: { value: "Mon" } })
        await waitFor(() =>
            expect(
                Array.from(document.querySelectorAll('[role="option"]')).map(
                    (option) => option.textContent
                )
            ).toEqual(["Moneycore.taxonomy/money"])
        )
        const paths = fetch.calls.map((call) => call.path)
        expect(paths).toContain("/api/taxonomy?scope=up")
        expect(paths).toContain("/api/capabilities?scope=up")
        // Every item, for the item pickers, is asked for with no scope.
        for (const path of paths.filter((path) => path.includes("all=1")))
            expect(path).toBe("/api/work?all=1")
    }
)

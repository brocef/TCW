import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { MemoryRouter, useLocation } from "react-router"
import { ThemeProvider } from "../theme"
import { fakeFetch, project, workDetail, workItem } from "../test-fixtures"
import type { TProject } from "../model/types"
import { App } from "./app"

function Where() {
    return <output data-testid="where">{useLocation().pathname}</output>
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

function serve(
    overrides: Partial<TProject> = {},
    extra: Array<[string | RegExp, number, unknown]> = []
) {
    const fetch = fakeFetch([
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
                items: [{ slug: "p/2026-10-01-a", path: "/w/2026-10-01-a" }],
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

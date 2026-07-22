import { fireEvent, render, screen } from "@testing-library/react"
import { MemoryRouter } from "react-router"
import { ThemeProvider } from "../theme"
import { App } from "./app"

function renderApp() {
    return render(
        <ThemeProvider>
            <MemoryRouter>
                <App />
            </MemoryRouter>
        </ThemeProvider>
    )
}

test("renders the established three-axis shell", () => {
    globalThis.fetch = vi
        .fn()
        .mockResolvedValue({ ok: true, json: async () => [] })
    renderApp()
    expect(screen.getByRole("button", { name: "Taxonomy" })).toBeInTheDocument()
    expect(
        screen.getByRole("button", { name: "Capabilities" })
    ).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Work" })).toBeInTheDocument()
    expect(screen.getByRole("tree", { name: "Objects" })).toBeInTheDocument()
})

test.each(["Taxonomy", "Capabilities", "Work"])(
    "renders the %s create button above its object list",
    (axis) => {
        globalThis.fetch = vi
            .fn()
            .mockResolvedValue({ ok: true, json: async () => [] })
        renderApp()
        if (axis !== "Work")
            fireEvent.click(screen.getByRole("button", { name: axis }))

        const tree = screen.getByRole("tree", { name: "Objects" })
        const createButton = screen.getByRole("button", {
            name: `+ Create ${axis}`,
        })
        expect(createButton.compareDocumentPosition(tree)).toBe(
            Node.DOCUMENT_POSITION_FOLLOWING
        )
    }
)

test("places the accessible Settings control immediately after Work", () => {
    globalThis.fetch = vi
        .fn()
        .mockResolvedValue({ ok: true, json: async () => [] })
    renderApp()
    const work = screen.getByRole("button", { name: "Work" })
    const settings = screen.getByRole("button", { name: "Settings" })
    expect(work.compareDocumentPosition(settings)).toBe(
        Node.DOCUMENT_POSITION_FOLLOWING
    )
})

test("applies and persists an appearance choice without leaving the shell", async () => {
    globalThis.fetch = vi
        .fn()
        .mockResolvedValue({ ok: true, json: async () => [] })
    localStorage.clear()
    renderApp()
    fireEvent.click(screen.getByRole("button", { name: "Settings" }))
    fireEvent.click(await screen.findByRole("radio", { name: "Dark" }))
    expect(localStorage.getItem("tcw.theme")).toBe("dark")
    expect(document.documentElement).toHaveClass("dark")
    expect(screen.getByRole("tree", { name: "Objects" })).toBeInTheDocument()
})

test("shows and applies the accessible filter clear action", async () => {
    globalThis.fetch = vi.fn().mockImplementation(async (input) => ({
        ok: true,
        json: async () =>
            String(input).endsWith("/api/work/tags") ? { tags: [] } : [],
    }))
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

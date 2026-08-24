import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { ThemeProvider } from "../theme"
import type { CapabilityItem, TaxonomyItem, WorkItem } from "../model/types"
import { ItemMeta, Markdown, Tree } from "./shared-components"

const modified = "2026-07-22T18:30:00Z"

test("uses the same child grid and standardized status surface at every depth", () => {
    const child = {
        name: "child",
        path: "parent/child",
        item: {
            slug: "child",
            title: "Child",
            status: "active",
            modified,
        } as WorkItem,
        children: [],
    }
    const nodes = [
        {
            name: "parent",
            path: "parent",
            item: {
                slug: "parent",
                title: "Parent",
                status: "backlog",
                modified,
            } as WorkItem,
            children: [child],
        },
    ]
    const { container } = render(
        <ThemeProvider>
            <Tree
                nodes={nodes}
                axis="work"
                selected="child"
                expanded={new Set(["parent"])}
                visible={() => true}
                onToggle={() => undefined}
                onSelect={() => undefined}
            />
        </ThemeProvider>
    )

    expect(container.querySelectorAll(".tree-children")).toHaveLength(2)
    expect(screen.getByRole("treeitem", { name: /Parent/ })).toHaveClass(
        "item-work",
        "st-backlog"
    )
    expect(screen.getByRole("treeitem", { name: /Child/ })).toHaveClass(
        "item-work",
        "st-active",
        "active"
    )
    expect(screen.getAllByText(/backlog|active/)).toHaveLength(2)
    const toggle = screen.getByRole("button", { name: "Collapse parent" })
    expect(toggle).toHaveAttribute("aria-expanded", "true")
    fireEvent.click(toggle)
})

test("renders modified subtext for every tree axis", () => {
    const { container } = render(
        <ThemeProvider>
            <ItemMeta
                axis="work"
                item={{ slug: "work", status: "active", modified } as WorkItem}
            />
            <ItemMeta
                axis="taxonomy"
                item={
                    { slug: "term", kind: "Feature", modified } as TaxonomyItem
                }
            />
            <ItemMeta
                axis="capabilities"
                item={
                    {
                        path: "web",
                        status: "Supported",
                        modified,
                    } as CapabilityItem
                }
            />
        </ThemeProvider>
    )

    expect(screen.getAllByText(/^Modified at /)).toHaveLength(3)
    for (const timestamp of container.querySelectorAll("time.modified-at"))
        expect(timestamp).toHaveAttribute("datetime", modified)
})

const URI = "tcw://W/orchestrator/2026-01-01-x"
const OFF_BOARD = "Project orchestrator is not included in this board"

function renderResolved(resolved: unknown, source?: string) {
    globalThis.fetch = vi.fn().mockImplementation(async () => ({
        ok: true,
        json: async () => ({ [URI]: resolved }),
    }))
    return render(
        <Markdown source={source ?? `See [the epic](${URI}).`} resolveLinks />
    )
}

test("marks an unhosted reference as off-board and names its project", async () => {
    const { container } = renderResolved({
        ok: false,
        reason: "unhosted-project",
        project: "orchestrator",
    })
    const anchor = await screen.findByText("the epic")
    await waitFor(() => expect(anchor).toHaveClass("tcw-unhosted"))
    expect(anchor).not.toHaveClass("tcw-inert")
    expect(anchor).not.toHaveAttribute("data-nav-key")
    const badge = container.querySelector(".tcw-project-badge")
    expect(badge).toBe(anchor.nextElementSibling)
    expect(badge).toHaveTextContent(/^orchestrator$/)
})

test("states why an unhosted reference is not a link, beyond the tooltip", async () => {
    const { container } = renderResolved({
        ok: false,
        reason: "unhosted-project",
        project: "orchestrator",
    })
    const anchor = await screen.findByText("the epic")
    await waitFor(() => expect(anchor).toHaveAttribute("aria-describedby"))
    // Assert the wiring, not just the sentence: `title` alone would satisfy an
    // accessible-description query, so this test has to fail if the note or the
    // reference to it is dropped.
    const noteId = anchor.getAttribute("aria-describedby")!
    const note = container.querySelector(`#${noteId}`)
    expect(note).not.toBeNull()
    expect(note).toHaveTextContent(OFF_BOARD)
    expect(anchor).toHaveAttribute("title", OFF_BOARD)
})

test("leaves an unopenable reference unclickable, address still readable", async () => {
    renderResolved({
        ok: false,
        reason: "unhosted-project",
        project: "orchestrator",
    })
    const anchor = await screen.findByText("the epic")
    await waitFor(() => expect(anchor).toHaveClass("tcw-unhosted"))
    // The click handler navigates only on data-nav-key; a surviving tcw:// href
    // would hand the click to the browser instead of doing nothing.
    expect(anchor).not.toHaveAttribute("href")
    expect(anchor).toHaveAttribute("data-tcw-ref", URI)
})

test("authored markup cannot suppress the off-board note", async () => {
    // `marked` passes authored HTML through, so a document can already contain
    // an element carrying the badge class, or an id we would otherwise mint.
    // Neither may cost the reference its accessible description.
    const { container } = renderResolved(
        {
            ok: false,
            reason: "unhosted-project",
            project: "orchestrator",
        },
        `<span id="tcw-off-board-0">x</span>\n\nSee [the epic](${URI})<span class="tcw-project-badge">not ours</span>.`
    )
    const anchor = await screen.findByText("the epic")
    await waitFor(() => expect(anchor).toHaveAttribute("aria-describedby"))
    const noteId = anchor.getAttribute("aria-describedby")!
    const note = container.querySelector(`#${noteId}`)
    expect(note).toHaveTextContent(OFF_BOARD)
    expect(note).not.toHaveTextContent("x")
    expect(anchor.nextElementSibling).toHaveTextContent(/^orchestrator$/)
})

test("shows an unresolved reference inert, with the reason it failed", async () => {
    const { container } = renderResolved({
        ok: false,
        reason: "unresolved",
        detail: "no such work item: x",
    })
    const anchor = await screen.findByText("the epic")
    await waitFor(() => expect(anchor).toHaveClass("tcw-inert"))
    expect(anchor).not.toHaveClass("tcw-unhosted")
    expect(anchor).toHaveAttribute("title", "no such work item: x")
    expect(container.querySelector(".tcw-project-badge")).toBeNull()
})

test("rewrites a resolvable reference into in-app navigation", async () => {
    renderResolved({ ok: true, axis: "work", key: "2026-01-01-x" })
    const anchor = await screen.findByText("the epic")
    await waitFor(() =>
        expect(anchor).toHaveAttribute("data-nav-key", "2026-01-01-x")
    )
    expect(anchor).toHaveAttribute("data-nav-axis", "work")
    expect(anchor).not.toHaveClass("tcw-inert")
    expect(anchor).not.toHaveClass("tcw-unhosted")
})

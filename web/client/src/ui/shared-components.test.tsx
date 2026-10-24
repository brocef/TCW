import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { ThemeProvider } from "../theme"
import { capability, term, workItem } from "../test-fixtures"
import { useState } from "react"
import { LinkContext } from "./link-context"
import { ProjectIdContext } from "./project-context"
import { ItemMeta, Markdown, MarkdownEditor, Tree } from "./shared-components"

const modified = "2026-07-22T18:30:00Z"

test("uses the same child grid and the row class at every depth", () => {
    const child = {
        name: "child",
        path: "p/child",
        item: workItem("child", { title: "Child", stage: "build" }),
        children: [],
    }
    const nodes = [
        {
            name: "parent",
            path: "p/parent",
            item: workItem("parent", { title: "Parent", stage: "ask" }),
            children: [child],
        },
    ]
    // Served from `p`, whose items are routed by folder (TCW-113 Design 6.3).
    const { container } = render(
        <ThemeProvider>
            <ProjectIdContext.Provider value="p">
                <Tree
                    nodes={nodes}
                    axis="work"
                    selected="child"
                    expanded={new Set(["p/parent"])}
                    visible={() => true}
                    rowClass={(item) =>
                        `st-${item.stage === "ask" ? "flow" : "side"}`
                    }
                    onToggle={() => undefined}
                    onSelect={() => undefined}
                />
            </ProjectIdContext.Provider>
        </ThemeProvider>
    )

    expect(container.querySelectorAll(".tree-children")).toHaveLength(2)
    expect(screen.getByRole("treeitem", { name: /Parent/ })).toHaveClass(
        "item-work",
        "st-flow"
    )
    expect(screen.getByRole("treeitem", { name: /Child/ })).toHaveClass(
        "item-work",
        "st-side",
        "active"
    )
    expect(screen.getByText("ask")).toBeInTheDocument()
    expect(screen.getByText("build")).toBeInTheDocument()
    const toggle = screen.getByRole("button", { name: "Collapse parent" })
    expect(toggle).toHaveAttribute("aria-expanded", "true")
    fireEvent.click(toggle)
})

test("copies a work row's full identifier", () => {
    const writeText = vi.fn().mockResolvedValue(undefined)
    Object.assign(navigator, { clipboard: { writeText } })
    render(
        <ThemeProvider>
            <Tree
                nodes={[
                    {
                        name: "x",
                        path: "p.work/x",
                        item: workItem("x"),
                        children: [],
                    },
                ]}
                axis="work"
                selected={null}
                expanded={new Set()}
                visible={() => true}
                onToggle={() => undefined}
                onSelect={() => undefined}
            />
        </ThemeProvider>
    )
    fireEvent.click(
        screen.getByRole("button", {
            name: "Copy full identifier to clipboard",
        })
    )
    expect(writeText).toHaveBeenCalledWith("p.work/x")
})

test("a work row shows its stage and creation date; records their modified time", () => {
    const created = "2026-10-01T09:00:00+00:00"
    const { container } = render(
        <ThemeProvider>
            <ItemMeta
                axis="work"
                item={workItem("x", {
                    created,
                    assignee: "acc-1",
                    priority: "high",
                })}
                people={{ "acc-1": "Ann" }}
            />
            <ItemMeta
                axis="taxonomy"
                item={term("term", { kind: "Feature", modified })}
            />
            <ItemMeta
                axis="capabilities"
                item={capability("web", { status: "Supported", modified })}
            />
        </ThemeProvider>
    )

    expect(screen.getAllByText(/^Created /)).toHaveLength(1)
    expect(screen.getAllByText(/^Modified at /)).toHaveLength(2)
    expect(container.querySelector("time")).toHaveAttribute("datetime", created)
    expect(screen.getByText(/priority high · Ann/)).toBeInTheDocument()
})

test("a row the backend could not read says its stage is unavailable", () => {
    render(
        <ThemeProvider>
            <ItemMeta axis="work" item={workItem("x", { unread: true })} />
        </ThemeProvider>
    )
    expect(screen.getByText("stage unavailable")).toBeInTheDocument()
})

const URI = "tcw://orchestrator/W/2026-01-01-x"
const OFF_BOARD = "In project orchestrator; open it there"

function renderResolved(resolved: unknown, source?: string) {
    globalThis.fetch = vi.fn().mockImplementation(async () => ({
        ok: true,
        json: async () => ({ [URI]: resolved }),
    }))
    return render(
        <Markdown source={source ?? `See [the epic](${URI}).`} resolveLinks />
    )
}

test("labels another project's reference and names its project", async () => {
    const { container } = renderResolved({
        ok: false,
        reason: "other-project",
        project: "orchestrator",
    })
    const anchor = await screen.findByText("the epic")
    await waitFor(() => expect(anchor).toHaveClass("tcw-other-project"))
    expect(anchor).not.toHaveClass("tcw-inert")
    expect(anchor).not.toHaveAttribute("data-nav-key")
    const badge = container.querySelector(".tcw-project-badge")
    expect(badge).toBe(anchor.nextElementSibling)
    expect(badge).toHaveTextContent(/^orchestrator$/)
})

test("states why another project's reference is not a link, beyond the tooltip", async () => {
    const { container } = renderResolved({
        ok: false,
        reason: "other-project",
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
        reason: "other-project",
        project: "orchestrator",
    })
    const anchor = await screen.findByText("the epic")
    await waitFor(() => expect(anchor).toHaveClass("tcw-other-project"))
    // The click handler navigates only on data-nav-key; a surviving tcw:// href
    // would hand the click to the browser instead of doing nothing.
    expect(anchor).not.toHaveAttribute("href")
    expect(anchor).toHaveAttribute("data-tcw-ref", URI)
})

test("authored markup cannot suppress the other-project note", async () => {
    // `marked` passes authored HTML through, so a document can already contain
    // an element carrying the badge class, or an id we would otherwise mint.
    // Neither may cost the reference its accessible description.
    const { container } = renderResolved(
        {
            ok: false,
            reason: "other-project",
            project: "orchestrator",
        },
        `<span id="tcw-other-project-0">x</span>\n\nSee [the epic](${URI})<span class="tcw-project-badge">not ours</span>.`
    )
    const anchor = await screen.findByText("the epic")
    await waitFor(() => expect(anchor).toHaveAttribute("aria-describedby"))
    const noteId = anchor.getAttribute("aria-describedby")!
    // Ids are minted from zero against the document, so this one is forced: the
    // authored element holds -0, therefore the note must be -1. Asserting the
    // exact value is what makes this test fail if collision-avoidance is dropped
    // — asserting only "the note has the right text" would not, since a stale
    // module counter could hand out a free id by luck.
    expect(noteId).toBe("tcw-other-project-1")
    const note = container.querySelector(`#${noteId}`)
    expect(note).toHaveTextContent(OFF_BOARD)
    expect(screen.getByText("x")).toHaveAttribute("id", "tcw-other-project-0")
    expect(anchor.nextElementSibling).toHaveTextContent(/^orchestrator$/)
})

test("authored markup adjacent to a reference is never removed", async () => {
    // An earlier guard removed a marked sibling and the element after it, which
    // authored markup could forge into deleting content that was never ours.
    const { container } = renderResolved(
        {
            ok: false,
            reason: "other-project",
            project: "orchestrator",
        },
        `See [the epic](${URI})<span data-tcw-badge></span><em>keep me</em>.`
    )
    const anchor = await screen.findByText("the epic")
    await waitFor(() => expect(anchor).toHaveClass("tcw-other-project"))
    expect(screen.getByText("keep me")).toBeInTheDocument()
    expect(container.querySelector("[data-tcw-badge]")).not.toBeNull()
})

test("shows an unresolved reference inert, with the reason it failed", async () => {
    const { container } = renderResolved({
        ok: false,
        reason: "unresolved",
        detail: "no such work item: x",
    })
    const anchor = await screen.findByText("the epic")
    await waitFor(() => expect(anchor).toHaveClass("tcw-inert"))
    expect(anchor).not.toHaveClass("tcw-other-project")
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
    expect(anchor).not.toHaveClass("tcw-other-project")
})

test("a superseded response never touches the document that replaced it", async () => {
    // Source A's request is still in flight when source B renders, and A's answer
    // arrives FIRST. Without the cleanup guard, A re-queries B's anchors, finds no
    // entry for B's uri, marks it unresolved and strips its href — and B's own
    // answer, arriving after, finds nothing left to repair.
    const URI_A = "tcw://other.work/2026-01-01-a"
    const gate: Record<string, () => void> = {}
    const waits: Record<string, Promise<void>> = {}
    for (const key of ["a", "b"])
        waits[key] = new Promise<void>((resolve) => {
            gate[key] = resolve
        })
    globalThis.fetch = vi.fn().mockImplementation(async (_url, init) => {
        const { uris } = JSON.parse((init as RequestInit).body as string)
        const forA = uris.includes(URI_A)
        await waits[forA ? "a" : "b"]
        return {
            ok: true,
            json: async () =>
                forA
                    ? {
                          [URI_A]: {
                              ok: true,
                              axis: "work",
                              key: "2026-01-01-a",
                          },
                      }
                    : {
                          [URI]: {
                              ok: false,
                              reason: "other-project",
                              project: "orchestrator",
                          },
                      },
        }
    })
    const { rerender } = render(
        <Markdown source={`See [other](${URI_A}).`} resolveLinks />
    )
    rerender(<Markdown source={`See [the epic](${URI}).`} resolveLinks />)
    const anchor = await screen.findByText("the epic")

    gate.a() // the stale answer lands first
    await new Promise((resolve) => setTimeout(resolve, 20))
    expect(anchor).not.toHaveClass("tcw-inert")
    expect(anchor).toHaveAttribute("href", URI)

    gate.b() // the current answer still applies
    await waitFor(() => expect(anchor).toHaveClass("tcw-other-project"))
    expect(anchor).toHaveAttribute("data-tcw-ref", URI)
})

test("typing tcw:// in the editor offers objects and inserts a work item's folder form", async () => {
    let text = ""
    function Editor() {
        const [value, setValue] = useState("")
        return (
            <LinkContext.Provider
                value={[
                    {
                        identifier: "tcw://p.work/2026-10-01-x",
                        displayName: "The X item",
                    },
                    {
                        identifier: "tcw://p.capabilities/web",
                        displayName: "Web",
                    },
                ]}
            >
                <MarkdownEditor
                    value={value}
                    onChange={(next) => {
                        text = next
                        setValue(next)
                    }}
                />
            </LinkContext.Provider>
        )
    }
    globalThis.fetch = vi
        .fn()
        .mockResolvedValue({ ok: true, json: async () => ({}) })
    render(
        <ThemeProvider>
            <Editor />
        </ThemeProvider>
    )
    const area = screen.getByRole("textbox", { name: "Markdown" })
    fireEvent.change(area, {
        target: { value: "See tcw://x", selectionStart: 11 },
    })
    const listbox = screen.getByRole("listbox", { name: "Links" })
    expect(listbox).toHaveTextContent("The X item")
    fireEvent.keyDown(area, { key: "Enter" })
    expect(text).toBe("See tcw://p.work/2026-10-01-x")
    expect(screen.queryByRole("listbox", { name: "Links" })).toBeNull()
})

function LinkEditor({ onText }: { onText: (text: string) => void }) {
    const [value, setValue] = useState("")
    return (
        <LinkContext.Provider
            value={[
                {
                    identifier: "tcw://p.work/2026-10-01-x",
                    displayName: "The X item",
                },
                { identifier: "tcw://p.capabilities/web", displayName: "Web" },
            ]}
        >
            <MarkdownEditor
                value={value}
                onChange={(next) => {
                    onText(next)
                    setValue(next)
                }}
            />
        </LinkContext.Provider>
    )
}

test("the link list closes when the caret leaves the link, and Enter is not taken", () => {
    let text = ""
    globalThis.fetch = vi
        .fn()
        .mockResolvedValue({ ok: true, json: async () => ({}) })
    render(
        <ThemeProvider>
            <LinkEditor onText={(next) => (text = next)} />
        </ThemeProvider>
    )
    const area = screen.getByRole("textbox", {
        name: "Markdown",
    }) as HTMLTextAreaElement
    fireEvent.change(area, {
        target: { value: "See tcw://x", selectionStart: 11 },
    })
    expect(screen.getByRole("listbox", { name: "Links" })).toBeInTheDocument()
    // Home, an arrow key or a click puts the caret before the link.
    area.setSelectionRange(3, 3)
    fireEvent.keyUp(area, { key: "Home" })
    expect(screen.queryByRole("listbox", { name: "Links" })).toBeNull()
    // Enter there is the editor's own: nothing replaces any text.
    expect(fireEvent.keyDown(area, { key: "Enter" })).toBe(true)
    expect(text).toBe("See tcw://x")
    // Back at the end of the link, the list returns.
    area.setSelectionRange(11, 11)
    fireEvent.click(area)
    expect(screen.getByRole("listbox", { name: "Links" })).toBeInTheDocument()
    // A caret inside the link, with more of it after, offers nothing.
    area.setSelectionRange(9, 9)
    fireEvent.select(area)
    expect(screen.queryByRole("listbox", { name: "Links" })).toBeNull()
})

test("a link typed in full ends the line on the first Enter", () => {
    let text = ""
    globalThis.fetch = vi
        .fn()
        .mockResolvedValue({ ok: true, json: async () => ({}) })
    render(
        <ThemeProvider>
            <LinkEditor onText={(next) => (text = next)} />
        </ThemeProvider>
    )
    const area = screen.getByRole("textbox", { name: "Markdown" })
    fireEvent.change(area, {
        target: { value: "See tcw://p.capabilities/web", selectionStart: 28 },
    })
    expect(screen.getByRole("listbox", { name: "Links" })).toBeInTheDocument()
    // Not prevented: the browser inserts the line break.
    expect(fireEvent.keyDown(area, { key: "Enter" })).toBe(true)
    expect(text).toBe("See tcw://p.capabilities/web")
    expect(screen.queryByRole("listbox", { name: "Links" })).toBeNull()
})

// -- another project's rows, and a row's statuses (TCW-113 Design 6.7, 6.9) ---

function meta(
    axis: "work" | "capabilities",
    item: Parameters<typeof ItemMeta>[0]["item"]
) {
    return render(
        <ThemeProvider>
            <ProjectIdContext.Provider value="shared">
                <ItemMeta axis={axis} item={item} />
            </ProjectIdContext.Provider>
        </ThemeProvider>
    )
}

test("a board row of another project's item carries the badge", () => {
    meta(
        "work",
        workItem("x", { "full-id": "desktop.work/x", owner: "desktop" })
    )
    expect(screen.getByText("owned by desktop")).toBeInTheDocument()
})

test("a board row of the project's own item carries none", () => {
    meta("work", workItem("x", { "full-id": "shared.work/x", owner: "shared" }))
    expect(screen.queryByText(/owned by/)).toBeNull()
})

test("a tree row of another project's capability carries the badge", () => {
    meta("capabilities", capability("abc", { status: "Supported" }, "desktop"))
    expect(screen.getByText("owned by desktop")).toBeInTheDocument()
})

test("a capability row under down shows each status counted", () => {
    meta(
        "capabilities",
        capability(
            "abc",
            {
                status: "Missing",
                statuses: [
                    { project: "shared", status: "Missing", inherited: false },
                    {
                        project: "desktop",
                        status: "Supported",
                        inherited: false,
                    },
                    { project: "server", status: "Omitted", inherited: false },
                ],
            },
            "shared"
        )
    )
    expect(
        screen.getByText("Missing(1), Supported(1), Omitted(1)", {
            exact: false,
        })
    ).toBeInTheDocument()
})

test("a capability row with no statuses shows its status alone", () => {
    meta("capabilities", capability("abc", { status: "Supported" }, "desktop"))
    expect(screen.queryByText(/\(1\)/)).toBeNull()
    expect(screen.getByText("Supported", { exact: false })).toBeInTheDocument()
})

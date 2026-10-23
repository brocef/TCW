import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { vi } from "vitest"
import { ThemeProvider } from "../theme"
import { fakeFetch, project, workItem } from "../test-fixtures"
import type { TProject } from "../model/types"
import {
    BlocksForm,
    CommentBox,
    FileEditor,
    NewItemForm,
    PropertiesForm,
    TicketsView,
} from "./work-forms"

window.HTMLElement.prototype.scrollIntoView = vi.fn()

const references = {
    projectId: "p",
    work: [workItem("a"), workItem("b")],
    taxonomy: [],
    capabilities: [],
    people: {},
    user: "ann",
}

function wrap(node: React.ReactNode) {
    return render(<ThemeProvider>{node}</ThemeProvider>)
}

async function choose(label: string, option: string) {
    fireEvent.click(screen.getByRole("combobox", { name: label }))
    fireEvent.click(await screen.findByRole("option", { name: option }))
}

describe("the file editor", () => {
    test("a new verdict round writes the chosen verdict and creates the file", async () => {
        const fetch = fakeFetch([[/^PUT /, 200, { revision: "r2" }]])
        globalThis.fetch = fetch as unknown as typeof globalThis.fetch
        const onSaved = vi.fn()
        wrap(
            <FileEditor
                session={{
                    folder: "x",
                    stage: "judge",
                    path: "judge/round-1.md",
                    revision: null,
                    content: "---\njudges: 1\nverdict:\n---\n",
                    verdict: true,
                }}
                onSaved={onSaved}
                onCancel={() => undefined}
                onDirty={() => undefined}
            />
        )
        expect(
            screen.getByRole("heading", { name: "Create judge/round-1.md" })
        ).toBeInTheDocument()
        await choose("Verdict", "accepted")
        expect(screen.getByRole("textbox", { name: "Markdown" })).toHaveValue(
            "---\njudges: 1\nverdict: accepted\n---\n"
        )
        fireEvent.click(screen.getByRole("button", { name: "Save" }))
        await waitFor(() => expect(onSaved).toHaveBeenCalled())
        expect(fetch.calls[0]).toEqual({
            path: "/api/work/x/files/judge/round-1.md",
            method: "PUT",
            body: {
                content: "---\njudges: 1\nverdict: accepted\n---\n",
                revision: null,
            },
        })
    })

    test("a stale save keeps the draft and offers to load the file again", async () => {
        globalThis.fetch = fakeFetch([
            [/^PUT /, 409, { error: "changed", code: "stale-revision" }],
        ]) as unknown as typeof globalThis.fetch
        wrap(
            <FileEditor
                session={{
                    folder: "x",
                    stage: "ask",
                    path: "ask/ask.md",
                    revision: "r1",
                    content: "old",
                    verdict: false,
                }}
                onSaved={() => undefined}
                onCancel={() => undefined}
                onDirty={() => undefined}
            />
        )
        expect(screen.queryByRole("combobox", { name: "Verdict" })).toBeNull()
        fireEvent.change(screen.getByRole("textbox", { name: "Markdown" }), {
            target: { value: "mine" },
        })
        fireEvent.click(screen.getByRole("button", { name: "Save" }))
        expect(
            await screen.findByText("Stale write detected")
        ).toBeInTheDocument()
        expect(screen.getByRole("textbox", { name: "Markdown" })).toHaveValue(
            "mine"
        )
    })
})

describe("the properties form", () => {
    test("sends only what changed, with the values it loaded", async () => {
        const fetch = fakeFetch([[/^PATCH /, 200, { item: {} }]])
        globalThis.fetch = fetch as unknown as typeof globalThis.fetch
        const onSaved = vi.fn()
        wrap(
            <PropertiesForm
                project={project()}
                item={workItem("x", { priority: "medium", tags: ["ui"] })}
                folder="x"
                references={references}
                onSaved={onSaved}
                onCancel={() => undefined}
                onDirty={() => undefined}
                onReload={() => undefined}
            />
        )
        await choose("Priority", "high")
        fireEvent.click(screen.getByRole("button", { name: "Remove ui" }))
        fireEvent.click(screen.getByRole("button", { name: "Save" }))
        await waitFor(() => expect(onSaved).toHaveBeenCalled())
        expect(fetch.calls[0].body).toEqual({
            changes: {
                priority: "high",
                tags: { add: [], remove: ["ui"] },
            },
            expected: { priority: "medium", tags: ["ui"] },
        })
    })

    test("a stale answer names the property and keeps the draft", async () => {
        globalThis.fetch = fakeFetch([
            [
                /^PATCH /,
                409,
                {
                    error: "priority changed since the page loaded it",
                    code: "stale-revision",
                },
            ],
        ]) as unknown as typeof globalThis.fetch
        const onReload = vi.fn()
        wrap(
            <PropertiesForm
                project={project()}
                item={workItem("x")}
                folder="x"
                references={references}
                onSaved={() => undefined}
                onCancel={() => undefined}
                onDirty={() => undefined}
                onReload={onReload}
            />
        )
        await choose("Priority", "low")
        fireEvent.click(screen.getByRole("button", { name: "Save" }))
        expect(
            await screen.findByText(/priority changed since the page loaded it/)
        ).toBeInTheDocument()
        fireEvent.click(
            screen.getByRole("button", { name: "Load the item again" })
        )
        expect(onReload).toHaveBeenCalled()
    })

    test("saying nothing changed sends nothing", () => {
        const fetch = fakeFetch([])
        globalThis.fetch = fetch as unknown as typeof globalThis.fetch
        wrap(
            <PropertiesForm
                project={project()}
                item={workItem("x")}
                folder="x"
                references={references}
                onSaved={() => undefined}
                onCancel={() => undefined}
                onDirty={() => undefined}
                onReload={() => undefined}
            />
        )
        fireEvent.click(screen.getByRole("button", { name: "Save" }))
        expect(screen.getByText("Nothing has changed.")).toBeInTheDocument()
        expect(fetch.calls).toHaveLength(0)
    })
})

test("blocks are added one request per link, stopping at the first refusal", async () => {
    const sent: string[] = []
    const fetch = vi.fn(async (_input: unknown, init?: RequestInit) => {
        const { target } = JSON.parse(String(init?.body))
        sent.push(target)
        const refused = target.startsWith("q.work/")
        return {
            ok: !refused,
            status: refused ? 409 : 200,
            statusText: "",
            json: async () =>
                refused
                    ? { error: "q is upstream", code: "refused" }
                    : { target },
        }
    })
    globalThis.fetch = fetch as unknown as typeof globalThis.fetch
    const onSaved = vi.fn()
    wrap(
        <BlocksForm
            project={project()}
            item={workItem("x")}
            folder="x"
            references={references}
            onSaved={onSaved}
            onDirty={() => undefined}
        />
    )
    const input = screen.getByRole("combobox", { name: "Blocks (add)" })
    for (const target of ["p.work/a", "q.work/2026-01-01-z", "p.work/b"]) {
        fireEvent.change(input, { target: { value: target } })
        fireEvent.keyDown(input, { key: "Escape" })
        fireEvent.keyDown(input, { key: "Enter" })
    }
    fireEvent.click(screen.getByRole("button", { name: "Add" }))
    expect(
        await screen.findByText(
            "Added p.work/a. q.work/2026-01-01-z was not added: q is upstream"
        )
    ).toBeInTheDocument()
    expect(sent).toEqual(["p.work/a", "q.work/2026-01-01-z"])
    expect(onSaved).toHaveBeenCalledWith("Added p.work/a", null)
})

test("a comment is added through the comments route", async () => {
    const fetch = fakeFetch([[/^POST .*comments/, 201, { folder: "x" }]])
    globalThis.fetch = fetch as unknown as typeof globalThis.fetch
    const onSaved = vi.fn()
    const onDirty = vi.fn()
    wrap(<CommentBox folder="x" onSaved={onSaved} onDirty={onDirty} />)
    fireEvent.change(screen.getByRole("textbox", { name: "New comment" }), {
        target: { value: "Looks good" },
    })
    // Typed and not added is unsaved work the page must ask about.
    expect(onDirty).toHaveBeenLastCalledWith(true)
    fireEvent.click(screen.getByRole("button", { name: "Add comment" }))
    await waitFor(() => expect(onSaved).toHaveBeenCalled())
    expect(onDirty).toHaveBeenLastCalledWith(false)
    expect(fetch.calls[0]).toMatchObject({
        path: "/api/work/x/comments",
        method: "POST",
        body: { text: "Looks good" },
    })
})

describe("the new item form", () => {
    function renderForm(
        overrides: Partial<TProject> = {},
        onCreated = vi.fn()
    ) {
        wrap(
            <NewItemForm
                project={project(overrides)}
                references={references}
                onCreated={onCreated}
                onCancel={() => undefined}
                onDirty={() => undefined}
            />
        )
        return onCreated
    }

    test("in this project, unticking the first stage leaves it in the inbox stage", async () => {
        const fetch = fakeFetch([
            [/^POST /, 201, { "full-id": "p.work/2026-10-15-new" }],
        ])
        globalThis.fetch = fetch as unknown as typeof globalThis.fetch
        const onCreated = renderForm()
        fireEvent.change(screen.getByRole("textbox", { name: "Title" }), {
            target: { value: "New" },
        })
        await choose("Effort", "low")
        fireEvent.click(screen.getByRole("checkbox"))
        fireEvent.click(screen.getByRole("button", { name: "Save" }))
        await waitFor(() =>
            expect(onCreated).toHaveBeenCalledWith(
                "2026-10-15-new",
                "Created p.work/2026-10-15-new"
            )
        )
        expect(fetch.calls[0].body).toEqual({
            title: "New",
            properties: { effort: "low" },
            stage: "intake",
        })
    })

    test("another project leaves only title, request text and priority", async () => {
        const fetch = fakeFetch([
            [/^POST /, 201, { "full-id": "q.work/2026-10-15-new" }],
        ])
        globalThis.fetch = fetch as unknown as typeof globalThis.fetch
        const onCreated = renderForm()
        await choose("Project", "q")
        expect(screen.queryByRole("combobox", { name: "Effort" })).toBeNull()
        expect(screen.queryByRole("combobox", { name: "Tags" })).toBeNull()
        expect(screen.queryByRole("checkbox")).toBeNull()
        fireEvent.change(screen.getByRole("textbox", { name: "Title" }), {
            target: { value: "Theirs" },
        })
        await choose("Priority", "high")
        fireEvent.click(screen.getByRole("button", { name: "Save" }))
        await waitFor(() =>
            expect(onCreated).toHaveBeenCalledWith(
                null,
                "Created q.work/2026-10-15-new"
            )
        )
        expect(fetch.calls[0].body).toEqual({
            title: "Theirs",
            properties: { priority: "high" },
            project: "q",
        })
    })

    test("in Jira mode only the fields the create screen has are offered", () => {
        renderForm({
            recordOwner: "backend",
            inboxItems: false,
            createFields: ["priority"],
        })
        expect(
            screen.getByRole("combobox", { name: "Priority" })
        ).toBeInTheDocument()
        expect(screen.queryByRole("combobox", { name: "Effort" })).toBeNull()
        expect(
            screen.queryByRole("combobox", { name: "Complexity" })
        ).toBeNull()
        expect(screen.queryByRole("checkbox")).toBeNull()
    })

    test("in Jira mode another project's parent is kept with a warning, a blocker is not", async () => {
        const fetch = fakeFetch([
            [/^POST /, 201, { "full-id": "p.work/TCW-9-new" }],
        ])
        globalThis.fetch = fetch as unknown as typeof globalThis.fetch
        const onCreated = renderForm({
            recordOwner: "backend",
            inboxItems: false,
            createFields: [],
        })
        fireEvent.change(screen.getByRole("textbox", { name: "Title" }), {
            target: { value: "New" },
        })
        const parent = screen.getByRole("combobox", { name: "Parent" })
        fireEvent.change(parent, { target: { value: "other.work/TCW-1-x" } })
        fireEvent.keyDown(parent, { key: "Enter" })
        expect(
            await screen.findByText(/other\.work\/TCW-1-x is in project other/)
        ).toBeInTheDocument()
        const blockers = screen.getByRole("combobox", { name: "Blocked by" })
        fireEvent.change(blockers, { target: { value: "other.work/TCW-1-x" } })
        fireEvent.click(screen.getByRole("button", { name: "Save" }))
        expect(
            await screen.findByText(
                /^Blocked by: other\.work\/TCW-1-x is not one/
            )
        ).toBeInTheDocument()
        expect(fetch.calls).toHaveLength(0)
        fireEvent.change(blockers, { target: { value: "" } })
        fireEvent.click(screen.getByRole("button", { name: "Save" }))
        await waitFor(() => expect(onCreated).toHaveBeenCalled())
        expect(fetch.calls[0].body).toMatchObject({
            title: "New",
            properties: { parent: "other.work/TCW-1-x" },
        })
    })

    test("a ticket made without an item is named, so it can be adopted", async () => {
        globalThis.fetch = fakeFetch([
            [
                /^POST /,
                409,
                {
                    error: "no single transition reaches the request status.",
                    code: "refused",
                    ticket: "X-7",
                },
            ],
        ]) as unknown as typeof globalThis.fetch
        renderForm()
        fireEvent.change(screen.getByRole("textbox", { name: "Title" }), {
            target: { value: "New" },
        })
        fireEvent.click(screen.getByRole("button", { name: "Save" }))
        expect(
            await screen.findByText(
                /Ticket X-7 was made; adopt it from Tickets/
            )
        ).toBeInTheDocument()
    })
})

describe("the tickets view", () => {
    const ticket = {
        key: "X-1",
        summary: "Please",
        status: "Inbox",
        created: "2026-10-01",
        reporter: "Ann",
        url: "https://tracker.example/browse/X-1",
        description: null,
    }

    test("adopting opens the new item", async () => {
        globalThis.fetch = fakeFetch([
            ["/api/tickets$", 200, { tickets: [ticket], query: "q" }],
            [/^POST /, 201, { "full-id": "p.work/X-1-please", code: 0 }],
        ]) as unknown as typeof globalThis.fetch
        const onAdopted = vi.fn()
        wrap(<TicketsView onAdopted={onAdopted} />)
        fireEvent.click(await screen.findByRole("button", { name: "Adopt" }))
        await waitFor(() =>
            expect(onAdopted).toHaveBeenCalledWith(
                "X-1-please",
                "Adopted X-1",
                null
            )
        )
    })

    test("an item adopted whose post hook failed opens, carrying what failed", async () => {
        globalThis.fetch = fakeFetch([
            ["/api/tickets$", 200, { tickets: [ticket], query: "q" }],
            [
                /^POST /,
                201,
                {
                    "full-id": "p.work/X-1-please",
                    code: 6,
                    problem:
                        "adopted X-1 as p/X-1-please, but request post hook failed",
                },
            ],
        ]) as unknown as typeof globalThis.fetch
        const onAdopted = vi.fn()
        wrap(<TicketsView onAdopted={onAdopted} />)
        fireEvent.click(await screen.findByRole("button", { name: "Adopt" }))
        await waitFor(() =>
            expect(onAdopted).toHaveBeenCalledWith(
                "X-1-please",
                "Adopted X-1",
                "adopted X-1 as p/X-1-please, but request post hook failed"
            )
        )
    })

    test("a refused adopt says why and the ticket stays listed", async () => {
        globalThis.fetch = fakeFetch([
            ["/api/tickets$", 200, { tickets: [ticket], query: "q" }],
            [
                /^POST /,
                409,
                { error: "transitions offered: Start, Close", code: "refused" },
            ],
        ]) as unknown as typeof globalThis.fetch
        wrap(<TicketsView onAdopted={() => undefined} />)
        fireEvent.click(await screen.findByRole("button", { name: "Adopt" }))
        expect(
            await screen.findByText("transitions offered: Start, Close")
        ).toBeInTheDocument()
        expect(screen.getByRole("link", { name: "X-1" })).toBeInTheDocument()
    })
})

describe("text a field will not keep holds back a save", () => {
    test("the properties form keeps the refused text and sends nothing", async () => {
        const fetch = fakeFetch([[/^PATCH /, 200, { item: {} }]])
        globalThis.fetch = fetch as unknown as typeof globalThis.fetch
        const onSaved = vi.fn()
        wrap(
            <PropertiesForm
                project={project()}
                item={workItem("x", { priority: "medium" })}
                folder="x"
                references={references}
                onSaved={onSaved}
                onCancel={() => undefined}
                onDirty={() => undefined}
                onReload={() => undefined}
            />
        )
        await choose("Priority", "high")
        const parent = screen.getByRole("combobox", { name: "Parent" })
        fireEvent.change(parent, { target: { value: "no such item" } })
        fireEvent.blur(parent)
        fireEvent.click(screen.getByRole("button", { name: "Save" }))
        expect(
            await screen.findAllByText(
                /no such item is not one of the suggestions/
            )
        ).not.toHaveLength(0)
        expect(screen.getByText(/^Parent: no such item/)).toBeInTheDocument()
        expect(parent).toHaveValue("no such item")
        expect(fetch.calls).toHaveLength(0)
        expect(onSaved).not.toHaveBeenCalled()
    })

    test("the new item form keeps a refused tag and creates nothing", async () => {
        const fetch = fakeFetch([
            [/^POST /, 201, { "full-id": "p.work/2026-10-15-new" }],
        ])
        globalThis.fetch = fetch as unknown as typeof globalThis.fetch
        const onCreated = vi.fn()
        wrap(
            <NewItemForm
                project={project()}
                references={references}
                onCreated={onCreated}
                onCancel={() => undefined}
                onDirty={() => undefined}
            />
        )
        fireEvent.change(screen.getByRole("textbox", { name: "Title" }), {
            target: { value: "New" },
        })
        fireEvent.change(screen.getByRole("combobox", { name: "Tags" }), {
            target: { value: "unregistered" },
        })
        fireEvent.click(screen.getByRole("button", { name: "Save" }))
        expect(
            await screen.findByText(/^Tags: unregistered is not one/)
        ).toBeInTheDocument()
        expect(fetch.calls).toHaveLength(0)
        expect(onCreated).not.toHaveBeenCalled()
    })

    test("the blocks form keeps refused text and adds nothing", async () => {
        const fetch = fakeFetch([[/^POST /, 200, {}]])
        globalThis.fetch = fetch as unknown as typeof globalThis.fetch
        wrap(
            <BlocksForm
                project={project()}
                item={workItem("x")}
                folder="x"
                references={references}
                onSaved={() => undefined}
                onDirty={() => undefined}
            />
        )
        const input = screen.getByRole("combobox", { name: "Blocks (add)" })
        fireEvent.change(input, { target: { value: "p.work/a" } })
        fireEvent.keyDown(input, { key: "Enter" })
        fireEvent.change(input, { target: { value: "not a slug" } })
        fireEvent.click(screen.getByRole("button", { name: "Add" }))
        expect(
            await screen.findByText(/Blocks \(add\): not a slug is not one/)
        ).toBeInTheDocument()
        expect(fetch.calls).toHaveLength(0)
    })
})

test("a save that gets no answer says the server could not be reached", async () => {
    globalThis.fetch = vi.fn(async () => {
        throw new TypeError("Failed to fetch")
    }) as unknown as typeof globalThis.fetch
    const onSaved = vi.fn()
    wrap(
        <FileEditor
            session={{
                folder: "x",
                stage: "spec",
                path: "spec/spec.md",
                revision: "r1",
                content: "old",
                verdict: false,
            }}
            onSaved={onSaved}
            onCancel={() => undefined}
            onDirty={() => undefined}
        />
    )
    fireEvent.click(screen.getByRole("button", { name: "Save" }))
    expect(
        await screen.findByText(/Could not reach the tcw serve process/)
    ).toBeInTheDocument()
    expect(onSaved).not.toHaveBeenCalled()
    expect(screen.getByRole("button", { name: "Save" })).toBeEnabled()
})

test("loading the file again after a conflict keeps the draft when the read fails", async () => {
    let gets = 0
    globalThis.fetch = vi.fn(async (_input: unknown, init?: RequestInit) => {
        if (init?.method === "PUT")
            return {
                ok: false,
                status: 409,
                statusText: "409",
                json: async () => ({ error: "x", code: "stale-revision" }),
            }
        gets += 1
        return {
            ok: false,
            status: 500,
            statusText: "500",
            json: async () => ({ error: "disk trouble", code: "error" }),
        }
    }) as unknown as typeof globalThis.fetch
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(true)
    try {
        wrap(
            <FileEditor
                session={{
                    folder: "x",
                    stage: "spec",
                    path: "spec/spec.md",
                    revision: "r1",
                    content: "mine",
                    verdict: false,
                }}
                onSaved={() => undefined}
                onCancel={() => undefined}
                onDirty={() => undefined}
            />
        )
        fireEvent.click(screen.getByRole("button", { name: "Save" }))
        fireEvent.click(
            await screen.findByRole("button", { name: "Refresh from server" })
        )
        expect(await screen.findByText("disk trouble")).toBeInTheDocument()
        expect(gets).toBe(1)
        // Not "the file is gone": the editor still edits, not creates.
        expect(
            screen.getByRole("heading", { name: "Edit spec/spec.md" })
        ).toBeInTheDocument()
        expect(screen.getByText("Stale write detected")).toBeInTheDocument()
        expect(screen.getByRole("textbox", { name: "Markdown" })).toHaveValue(
            "mine"
        )
    } finally {
        confirm.mockRestore()
    }
})

test("the new item form sends single values trimmed", async () => {
    const fetch = fakeFetch([
        [/^POST /, 201, { "full-id": "p.work/2026-10-15-new" }],
    ])
    globalThis.fetch = fetch as unknown as typeof globalThis.fetch
    wrap(
        <NewItemForm
            project={project()}
            references={references}
            onCreated={() => undefined}
            onCancel={() => undefined}
            onDirty={() => undefined}
        />
    )
    fireEvent.change(screen.getByRole("textbox", { name: "Title" }), {
        target: { value: "New" },
    })
    fireEvent.change(screen.getByRole("combobox", { name: "Assignee" }), {
        target: { value: "  bob  " },
    })
    fireEvent.click(screen.getByRole("button", { name: "Save" }))
    await waitFor(() => expect(fetch.calls).toHaveLength(1))
    expect(fetch.calls[0].body).toMatchObject({
        properties: { assignee: "bob" },
    })
})

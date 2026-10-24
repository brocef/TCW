import { useState } from "react"
import { fireEvent, render, screen, within } from "@testing-library/react"
import { vi } from "vitest"
import { ThemeProvider } from "../theme"
import type { TSortDirection, TWorkSortKey } from "../model/tree"
import {
    Conflict,
    DetailView,
    EditorView,
    FacetPopover,
    SortControl,
} from "./content-views"
import type { TDetail } from "./ui-types"
import { ProjectIdContext } from "./project-context"
import { capability, term } from "../test-fixtures"

window.HTMLElement.prototype.scrollIntoView = vi.fn()
const modified = "2026-07-22T18:30:00Z"

function Filters() {
    const [stages, setStages] = useState<string[]>(["ask", "build"])
    const [sortKey, setSortKey] = useState<TWorkSortKey>("name")
    const [direction, setDirection] = useState<TSortDirection>("ascending")
    return (
        <>
            <FacetPopover
                label="Stage"
                options={["ask", "build", "done"]}
                value={stages}
                onChange={setStages}
            />
            <SortControl
                sortKey={sortKey}
                direction={direction}
                onSortKeyChange={setSortKey}
                onDirectionChange={setDirection}
            />
        </>
    )
}

test("a facet is one checkbox list that counts what is ticked", async () => {
    render(
        <ThemeProvider>
            <Filters />
        </ThemeProvider>
    )
    fireEvent.click(screen.getByRole("button", { name: "Stage (2)" }))
    expect(await screen.findByRole("checkbox", { name: "ask" })).toBeChecked()
    const done = screen.getByRole("checkbox", { name: "done" })
    expect(done).not.toBeChecked()
    fireEvent.click(done)
    expect(screen.getByRole("button", { name: "Stage (3)" })).toBeVisible()
})

test("selects one work sort key, creation date included, and toggles its direction", async () => {
    render(
        <ThemeProvider>
            <Filters />
        </ThemeProvider>
    )
    const sort = screen.getByRole("combobox", { name: "Sort work items" })
    expect(sort).toHaveTextContent("Name")
    fireEvent.click(screen.getByRole("button", { name: "Sort descending" }))
    expect(screen.getByRole("button", { name: "Sort ascending" })).toBeVisible()
    fireEvent.click(sort)
    fireEvent.click(await screen.findByRole("option", { name: "Created" }))
    expect(sort).toHaveTextContent("Created")
    expect(screen.queryByRole("option", { name: "Modified" })).toBeNull()
})

test("renders modified subtext in the taxonomy and capability detail views", () => {
    const details: Array<{
        axis: "taxonomy" | "capabilities"
        detail: TDetail
    }> = [
        {
            axis: "taxonomy",
            detail: {
                term: term("term", { name: "Term", modified }),
                coreRevision: "",
            },
        },
        {
            axis: "capabilities",
            detail: {
                capability: capability("web", { name: "Web", modified }),
                coreRevision: "",
            },
        },
    ]
    render(
        <ThemeProvider>
            {details.map(({ axis, detail }) => (
                <DetailView
                    key={axis}
                    axis={axis}
                    detail={detail}
                    onEdit={() => undefined}
                />
            ))}
        </ThemeProvider>
    )
    expect(screen.getAllByText(/^Modified at /)).toHaveLength(2)
})

test("an inherited entry has no edit control and names its project", () => {
    const onEdit = vi.fn()
    render(
        <ThemeProvider>
            <ProjectIdContext.Provider value="p">
                <DetailView
                    axis="capabilities"
                    detail={{
                        capability: capability(
                            "shared",
                            { name: "Shared" },
                            "base"
                        ),
                        coreRevision: "",
                    }}
                    onEdit={onEdit}
                />
                <DetailView
                    axis="taxonomy"
                    detail={{
                        term: term("local", { name: "Local" }),
                        coreRevision: "",
                    }}
                    onEdit={onEdit}
                />
            </ProjectIdContext.Provider>
        </ThemeProvider>
    )
    expect(screen.getByText("owned by base")).toBeInTheDocument()
    expect(screen.getAllByRole("button", { name: "Edit" })).toHaveLength(1)
})

test("an entry that overrides another names it, and a partial one says so", () => {
    render(
        <ThemeProvider>
            <ProjectIdContext.Provider value="p">
                <DetailView
                    axis="capabilities"
                    detail={{
                        capability: capability("x", {
                            name: "X",
                            overrides: "core.capabilities/x",
                        }),
                        coreRevision: "",
                    }}
                    onEdit={vi.fn()}
                />
                <DetailView
                    axis="taxonomy"
                    detail={{
                        term: term("t", { name: "T", partial: true }),
                        coreRevision: "",
                    }}
                    onEdit={vi.fn()}
                />
            </ProjectIdContext.Provider>
        </ThemeProvider>
    )
    expect(screen.getByText("core.capabilities/x")).toBeInTheDocument()
    expect(screen.getByText(/^overrides/)).toBeInTheDocument()
    expect(
        screen.getByText("partial: inherited content could not be read")
    ).toBeInTheDocument()
})

test("a retired capability field is shown read-only and offered by no form", () => {
    render(
        <ThemeProvider>
            <DetailView
                axis="capabilities"
                detail={{
                    capability: capability("web", {
                        name: "Web",
                        fields: { Status: "Supported", "Planning doc": "old" },
                    }),
                    coreRevision: "r",
                }}
                onEdit={() => undefined}
            />
            <EditorView
                editor={{
                    mode: "core",
                    axis: "capabilities",
                    ref: "web",
                    revision: "r",
                    draft: { Status: "Supported", "Planning doc": "old" },
                    original: { Status: "Supported", "Planning doc": "old" },
                }}
                setDraft={() => undefined}
                saving={false}
                errors={[]}
                conflict={null}
                data={{ work: [], taxonomy: [], capabilities: [] }}
                scales={{ status: ["Supported"], priority: [], lifecycle: [] }}
                onSave={() => undefined}
                onCancel={() => undefined}
                onRefreshConflict={() => undefined}
            />
        </ThemeProvider>
    )
    expect(screen.getByText("Planning doc")).toBeInTheDocument()
    expect(screen.getByText("old")).toBeInTheDocument()
    expect(screen.queryByRole("textbox", { name: "Planning doc" })).toBeNull()
    expect(screen.queryByRole("combobox", { name: "Planning doc" })).toBeNull()
    expect(screen.queryByRole("combobox", { name: "Tracker" })).toBeNull()
})

test.each([
    ["Vocabulary", false],
    ["Feature", true],
])("a %s term's editor offers a vocabulary: %s", (kind, offered) => {
    render(
        <ThemeProvider>
            <EditorView
                editor={{
                    mode: "core",
                    axis: "taxonomy",
                    ref: "term",
                    revision: "r",
                    draft: { kind, vocabulary: [] },
                    original: { kind, vocabulary: [] },
                }}
                setDraft={() => undefined}
                saving={false}
                errors={[]}
                conflict={null}
                data={{ work: [], taxonomy: [], capabilities: [] }}
                scales={{ status: [], priority: [], lifecycle: [] }}
                onSave={() => undefined}
                onCancel={() => undefined}
                onRefreshConflict={() => undefined}
            />
        </ThemeProvider>
    )
    expect(
        screen.queryAllByRole("combobox", { name: "Vocabulary" })
    ).toHaveLength(offered ? 1 : 0)
})

test("the conflict banner nests no block inside its paragraph", () => {
    const errors = vi.spyOn(console, "error").mockImplementation(() => {})
    const onRefresh = vi.fn()
    const onDiscard = vi.fn()
    try {
        render(
            <ThemeProvider>
                <Conflict onRefresh={onRefresh} onDiscard={onDiscard} />
            </ThemeProvider>
        )
        expect(errors).not.toHaveBeenCalled()
    } finally {
        errors.mockRestore()
    }
    const banner = screen.getByRole("alert")
    expect(banner.querySelector("p div, p p")).toBeNull()
    fireEvent.click(screen.getByRole("button", { name: "Refresh from server" }))
    fireEvent.click(screen.getByRole("button", { name: "Discard draft" }))
    expect(onRefresh).toHaveBeenCalledOnce()
    expect(onDiscard).toHaveBeenCalledOnce()
})

// -- another project's capability, and its status by project (TCW-113) ---------

function capabilityPage(detail: TDetail, projectId = "shared") {
    const onEdit = vi.fn()
    render(
        <ThemeProvider>
            <ProjectIdContext.Provider value={projectId}>
                <DetailView
                    axis="capabilities"
                    detail={detail}
                    onEdit={onEdit}
                />
            </ProjectIdContext.Provider>
        </ThemeProvider>
    )
}

test("a capability another project owns shows whose it is and no Edit", () => {
    capabilityPage({
        capability: capability("abc", { name: "Abc" }, "desktop"),
        coreRevision: "",
    })
    expect(screen.getByText("owned by desktop")).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "Edit" })).toBeNull()
})

test("a capability the project owns shows Edit", () => {
    capabilityPage({
        capability: capability("abc", { name: "Abc" }, "shared"),
        coreRevision: "",
    })
    expect(screen.getByRole("button", { name: "Edit" })).toBeInTheDocument()
    expect(screen.queryByText(/owned by/)).toBeNull()
})

test("under down the page lists each status with its projects", () => {
    capabilityPage({
        capability: capability(
            "abc",
            {
                name: "Abc",
                status: "Missing",
                statuses: [
                    {
                        project: "shared",
                        status: "Missing",
                        inherited: false,
                        "full-id": "shared.capabilities/abc",
                    },
                    {
                        project: "desktop",
                        status: "Supported",
                        inherited: false,
                        "full-id": "desktop.capabilities/abc",
                    },
                    {
                        project: "server",
                        status: "Missing",
                        inherited: true,
                        "full-id": "shared.capabilities/abc",
                    },
                ],
                "overridden-by": ["desktop.capabilities/abc"],
            },
            "shared"
        ),
        coreRevision: "",
        projects: [
            { id: "shared", relation: "current" },
            { id: "desktop", relation: "descendant" },
            { id: "server", relation: "descendant" },
            {
                id: "mobile",
                relation: "descendant",
                unavailable: "fetch it with tcw project provision mobile",
            },
        ],
    })
    const block = screen.getByRole("region", { name: "Status by project" })
    const lines = [...block.querySelectorAll("li")].map((li) => li.textContent)
    expect(lines).toEqual([
        "Missing: shared, server (inherited)",
        "Supported: desktop",
        "unavailable: mobile",
    ])
    expect(screen.getByRole("link", { name: "desktop" })).toHaveAttribute(
        "data-nav-key",
        "desktop.capabilities/abc"
    )
    expect(screen.getByRole("link", { name: "shared" })).toHaveAttribute(
        "data-nav-key",
        "abc"
    )
    expect(screen.queryByRole("link", { name: "server" })).toBeNull()
})

test("a project whose own object sets no status is linked by its entry", () => {
    // Review round 5, finding 1: server's own `abc` holds only a name and
    // tablet, a grandchild, overrides desktop's with only a Priority. Both
    // are inherited and neither is in `overridden-by`; each entry's
    // `full-id` is its own object, so each is linked. phone has no object
    // of its own here, so its entry names desktop's, and it is not linked.
    capabilityPage({
        capability: capability(
            "abc",
            {
                name: "Abc",
                status: "Missing",
                statuses: [
                    {
                        project: "shared",
                        status: "Missing",
                        inherited: false,
                        "full-id": "shared.capabilities/abc",
                    },
                    {
                        project: "desktop",
                        status: "Supported",
                        inherited: false,
                        "full-id": "desktop.capabilities/abc",
                    },
                    {
                        project: "tablet",
                        status: "Supported",
                        inherited: true,
                        "full-id": "tablet.capabilities/abc",
                    },
                    {
                        project: "phone",
                        status: "Supported",
                        inherited: true,
                        "full-id": "desktop.capabilities/abc",
                    },
                    {
                        project: "server",
                        status: "Missing",
                        inherited: true,
                        "full-id": "server.capabilities/abc",
                    },
                ],
                "overridden-by": ["desktop.capabilities/abc"],
            },
            "shared"
        ),
        coreRevision: "",
    })
    const block = screen.getByRole("region", { name: "Status by project" })
    const lines = [...block.querySelectorAll("li")].map((li) => li.textContent)
    expect(lines).toEqual([
        "Missing: shared, server (inherited)",
        "Supported: desktop, tablet (inherited), phone (inherited)",
    ])
    const key = (name: string) =>
        within(block).getByRole("link", { name }).getAttribute("data-nav-key")
    expect(key("server")).toBe("server.capabilities/abc")
    expect(key("tablet")).toBe("tablet.capabilities/abc")
    expect(within(block).queryByRole("link", { name: "phone" })).toBeNull()
})

test("with no statuses the page has no status block", () => {
    capabilityPage({
        capability: capability("abc", { name: "Abc" }, "shared"),
        coreRevision: "",
    })
    expect(
        screen.queryByRole("region", { name: "Status by project" })
    ).toBeNull()
})

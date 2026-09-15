import { useState } from "react"
import { fireEvent, render, screen } from "@testing-library/react"
import { vi } from "vitest"
import { ThemeProvider } from "../theme"
import { CompleteModal, DetailView, FilterControls } from "./content-views"
import type { TDetail } from "./ui-types"

window.HTMLElement.prototype.scrollIntoView = vi.fn()
const modified = "2026-07-22T18:30:00Z"

function WorkFilters() {
    const [statuses, setStatuses] = useState<Record<string, boolean>>({
        backlog: true,
        active: true,
        completed: false,
    })
    const [tags, setTags] = useState<string[]>([])
    const [sortKey, setSortKey] = useState<"name" | "modified">("name")
    const [sortDirection, setSortDirection] = useState<
        "ascending" | "descending"
    >("ascending")
    return (
        <FilterControls
            axis="work"
            registeredTags={["web"]}
            statusFilter={statuses}
            setStatusFilter={setStatuses}
            kindFilter={[]}
            setKindFilter={() => undefined}
            tagFilter={tags}
            setTagFilter={setTags}
            workSortKey={sortKey}
            setWorkSortKey={setSortKey}
            workSortDirection={sortDirection}
            setWorkSortDirection={setSortDirection}
        />
    )
}

test("groups work statuses in one checkbox facet", async () => {
    render(
        <ThemeProvider>
            <WorkFilters />
        </ThemeProvider>
    )

    expect(screen.getByRole("button", { name: "Status (2)" })).toBeVisible()
    expect(screen.queryByRole("button", { name: "backlog" })).toBeNull()
    fireEvent.click(screen.getByRole("button", { name: "Status (2)" }))

    expect(
        await screen.findByRole("checkbox", { name: "Backlog" })
    ).toBeChecked()
    expect(screen.getByRole("checkbox", { name: "Active" })).toBeChecked()
    const completed = screen.getByRole("checkbox", { name: "Completed" })
    expect(completed).not.toBeChecked()
    fireEvent.click(completed)
    expect(screen.getByRole("button", { name: "Status (3)" })).toBeVisible()
})

test("selects one work sort key and toggles its direction", async () => {
    render(
        <ThemeProvider>
            <WorkFilters />
        </ThemeProvider>
    )

    const sort = screen.getByRole("combobox", { name: "Sort work items" })
    expect(sort).toHaveTextContent("Name")
    fireEvent.click(screen.getByRole("button", { name: "Sort descending" }))
    expect(screen.getByRole("button", { name: "Sort ascending" })).toBeVisible()

    fireEvent.click(sort)
    fireEvent.click(await screen.findByRole("option", { name: "Modified" }))
    expect(sort).toHaveTextContent("Modified")
    expect(screen.queryByText("Name ascending")).toBeNull()
})

test("renders modified subtext in every detail view", () => {
    const details: Array<{
        axis: "work" | "taxonomy" | "capabilities"
        detail: TDetail
    }> = [
        {
            axis: "work",
            detail: {
                item: {
                    slug: "work",
                    title: "Work",
                    status: "active",
                    modified,
                },
                coreRevision: "",
                artifacts: [],
                planStages: [],
                sidecars: [],
            },
        },
        {
            axis: "taxonomy",
            detail: {
                term: { slug: "term", name: "Term", modified },
                coreRevision: "",
            },
        },
        {
            axis: "capabilities",
            detail: {
                capability: { path: "web", name: "Web", modified },
                coreRevision: "",
            },
        },
    ]
    const views = details.map(({ axis, detail }) => (
        <DetailView
            key={axis}
            axis={axis}
            detail={detail}
            onEdit={() => undefined}
            onResource={() => undefined}
            onOpen={() => undefined}
            onReadArtifact={async (_slug, name) => ({
                name,
                content: "",
                revision: "",
            })}
            onDeletePlanStage={() => undefined}
            onAction={() => undefined}
        />
    ))
    render(<ThemeProvider>{views}</ThemeProvider>)

    expect(screen.getAllByText(/^Modified at /)).toHaveLength(3)
})

function workDetail(tracker: unknown) {
    return (
        <ThemeProvider>
            <DetailView
                axis="work"
                detail={
                    {
                        item: {
                            slug: "work",
                            title: "Work",
                            status: "backlog",
                            modified,
                            tracker,
                        },
                        coreRevision: "",
                        artifacts: [],
                        planStages: [],
                        sidecars: [],
                    } as TDetail
                }
                onEdit={() => undefined}
                onResource={() => undefined}
                onOpen={() => undefined}
                onReadArtifact={async (_slug, name) => ({
                    name,
                    content: "",
                    revision: "",
                })}
                onDeletePlanStage={() => undefined}
                onAction={() => undefined}
            />
        </ThemeProvider>
    )
}

test("a bound work item shows its ticket as a link, with provider and part", () => {
    render(
        workDetail({
            provider: "jira-cloud",
            project: "probe",
            part: "api",
            ticket: {
                id: "10001",
                key: "EX-1",
                url: "https://example.invalid/browse/EX-1",
            },
            bound: "2026-09-14",
            sync: null,
        })
    )

    expect(screen.getByText("Ticket")).toBeVisible()
    expect(screen.getByRole("link", { name: "EX-1" })).toHaveAttribute(
        "href",
        "https://example.invalid/browse/EX-1"
    )
    expect(screen.getByText(/· jira-cloud · part api/)).toBeVisible()
})

test("a ticket the tracker has not caught up with says so", () => {
    render(
        workDetail({
            provider: "jira-cloud",
            project: "probe",
            part: "default",
            ticket: { id: "1", key: "EX-1", url: "" },
            bound: "2026-09-14",
            sync: {
                state: "pending",
                move: "submit",
                since: "In Progress",
                claim: "done",
                reason: "the tracker could not be reached",
                at: "2026-09-14T10:00:00Z",
            },
        })
    )

    expect(
        screen.getByText(/· pending: the tracker could not be reached/)
    ).toBeVisible()
})

test("an unreadable binding shows why, and an unbound item shows no ticket", () => {
    const { unmount } = render(
        workDetail({ problem: "missing or empty: ticket.key" })
    )
    expect(
        screen.getByText(
            "tracker.yaml cannot be read: missing or empty: ticket.key"
        )
    ).toBeVisible()
    unmount()

    render(workDetail(null))
    expect(screen.queryByText("Ticket")).toBeNull()
})

test("the complete modal opens in its completion form, not its discard form", async () => {
    // Regression: `shipping` was `resolution === "done"`, so the unset default
    // rendered the discard presentation — titling the dialog "Close Work Item"
    // and labelling its button "Discard" before the user had chosen anything.
    render(
        <ThemeProvider>
            <CompleteModal
                detail={{ dodChecklist: ["tests pass"] } as never}
                onClose={() => undefined}
                onComplete={async () => true}
                errors={[]}
            />
        </ThemeProvider>
    )

    expect(screen.getByText("Complete Work Item")).toBeVisible()
    expect(screen.getByRole("button", { name: "Complete" })).toBeVisible()
    expect(screen.getByText("Definition of Done")).toBeVisible()
    expect(screen.getByText(/Reconciliation reminder/)).toBeVisible()
    expect(screen.queryByText(/This item will be discarded/)).toBeNull()
})

// The discard form is reached by picking a non-`done` resolution from a Radix
// Select in a portal, which jsdom drives poorly — that half is covered by the
// browser pass instead of faked here.

test("offers no Edit button on a generated sidecar", () => {
    // `rollup.md` is written by `tcw work reconcile`. The sidecar list is built
    // from the registry, so it arrived here editable for free — and an edit
    // saved through it is discarded by the next reconcile.
    const { container } = render(
        <ThemeProvider>
            <DetailView
                axis="work"
                detail={
                    {
                        item: {
                            slug: "epic",
                            title: "Epic",
                            status: "active",
                            modified,
                        },
                        coreRevision: "",
                        artifacts: [],
                        planStages: [],
                        sidecars: [
                            {
                                name: "capabilities.yaml",
                                present: true,
                                generated: false,
                            },
                            {
                                name: "rollup.md",
                                present: true,
                                generated: true,
                            },
                        ],
                    } as TDetail
                }
                onEdit={() => undefined}
                onResource={() => undefined}
                onOpen={() => undefined}
                onReadArtifact={async (_slug, name) => ({
                    name,
                    content: "",
                    revision: "",
                })}
                onDeletePlanStage={() => undefined}
                onAction={() => undefined}
            />
        </ThemeProvider>
    )

    // Still listed — hiding the file would be a worse answer than hiding the
    // button, and one Edit button survives, so this is not vacuously true.
    expect(screen.getByText("rollup.md")).toBeVisible()
    expect(screen.getByText("generated")).toBeVisible()
    // One button, for `capabilities.yaml` — so this is not vacuously true.
    expect(container.querySelectorAll(".sidecar-edit-btn")).toHaveLength(1)
})

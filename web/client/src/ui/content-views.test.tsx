import { useState } from "react"
import { fireEvent, render, screen } from "@testing-library/react"
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
    expect(screen.getByText("inherited from base")).toBeInTheDocument()
    expect(screen.getAllByRole("button", { name: "Edit" })).toHaveLength(1)
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

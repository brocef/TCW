import { useState } from "react"
import { fireEvent, render, screen } from "@testing-library/react"
import { vi } from "vitest"
import { ThemeProvider } from "../theme"
import type { TSortDirection, TWorkSortKey } from "../model/tree"
import { DetailView, FacetPopover, SortControl } from "./content-views"
import type { TDetail } from "./ui-types"

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

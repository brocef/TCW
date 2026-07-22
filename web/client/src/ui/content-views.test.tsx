import { useState } from "react"
import { fireEvent, render, screen } from "@testing-library/react"
import { vi } from "vitest"
import { ThemeProvider } from "../theme"
import { FilterControls } from "./content-views"

window.HTMLElement.prototype.scrollIntoView = vi.fn()

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

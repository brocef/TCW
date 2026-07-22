import { useState } from "react"
import { fireEvent, render, screen } from "@testing-library/react"
import { ThemeProvider } from "../theme"
import { FilterControls } from "./content-views"

function WorkFilters() {
    const [statuses, setStatuses] = useState<Record<string, boolean>>({
        backlog: true,
        active: true,
        completed: false,
    })
    const [tags, setTags] = useState<string[]>([])
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

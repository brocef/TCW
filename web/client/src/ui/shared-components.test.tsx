import { fireEvent, render, screen } from "@testing-library/react"
import { ThemeProvider } from "../theme"
import type { WorkItem } from "../model/types"
import { Tree } from "./shared-components"

test("uses the same child grid and standardized status surface at every depth", () => {
    const child = {
        name: "child",
        path: "parent/child",
        item: { slug: "child", title: "Child", status: "active" } as WorkItem,
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

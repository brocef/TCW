import { fireEvent, render, screen } from "@testing-library/react"
import { ThemeProvider } from "../theme"
import type { CapabilityItem, TaxonomyItem, WorkItem } from "../model/types"
import { ItemMeta, Tree } from "./shared-components"

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

import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { vi } from "vitest"
import { ThemeProvider } from "../theme"
import { WorkDocumentTabs } from "./work-document-tabs"

const artifacts = [
    { name: "initial-request", present: true },
    { name: "spec", present: true },
    { name: "plan", present: true },
]

function renderTabs(
    options: {
        slug?: string
        present?: string[]
        onReadArtifact?: ReturnType<typeof vi.fn>
    } = {}
) {
    const present = options.present ?? ["initial-request", "spec", "plan"]
    const onReadArtifact =
        options.onReadArtifact ??
        vi.fn(async (_slug: string, name: string) => ({
            name,
            content: `# Loaded ${name}`,
            revision: `${name}-revision`,
        }))
    const onEditInitialRequest = vi.fn()
    const onEditArtifact = vi.fn()
    const view = render(
        <ThemeProvider>
            <WorkDocumentTabs
                item={{
                    slug: options.slug ?? "first-item",
                    body: "# Initial body",
                }}
                artifacts={artifacts.map((artifact) => ({
                    ...artifact,
                    present: present.includes(artifact.name),
                }))}
                onEditInitialRequest={onEditInitialRequest}
                onEditArtifact={onEditArtifact}
                onReadArtifact={onReadArtifact}
            />
        </ThemeProvider>
    )
    return { ...view, onEditArtifact, onEditInitialRequest, onReadArtifact }
}

function selectTab(name: string) {
    fireEvent.mouseDown(screen.getByRole("tab", { name }), {
        button: 0,
        ctrlKey: false,
    })
}

test("shows the planning documents in order with Initial Request selected", () => {
    renderTabs()

    const tabs = screen.getAllByRole("tab")
    expect(tabs.map((tab) => tab.getAttribute("aria-label"))).toEqual([
        "Initial Request",
        "Spec",
        "Implementation Plan",
    ])
    expect(tabs[0]).toHaveAttribute("aria-selected", "true")
    expect(screen.getByRole("heading", { name: "Initial body" })).toBeVisible()
})

test("loads present documents and routes their edit actions", async () => {
    const { onEditArtifact, onReadArtifact } = renderTabs()

    selectTab("Spec")
    expect(
        await screen.findByRole("heading", { name: "Loaded spec" })
    ).toBeVisible()
    expect(onReadArtifact).toHaveBeenCalledWith("first-item", "spec")
    fireEvent.click(screen.getByRole("button", { name: "Edit Spec" }))
    expect(onEditArtifact).toHaveBeenCalledWith("first-item", "spec")

    selectTab("Implementation Plan")
    expect(
        await screen.findByRole("heading", { name: "Loaded plan" })
    ).toBeVisible()
})

test("routes Initial Request editing without loading an artifact", () => {
    const { onEditInitialRequest, onReadArtifact } = renderTabs()

    fireEvent.click(
        screen.getByRole("button", { name: "Edit Initial Request" })
    )
    expect(onEditInitialRequest).toHaveBeenCalledOnce()
    expect(onReadArtifact).not.toHaveBeenCalled()
})

test("keeps missing documents visible without an edit action", () => {
    renderTabs({ present: ["initial-request"] })

    selectTab("Spec")
    expect(screen.getByText("Spec is not yet present.")).toBeVisible()
    expect(screen.queryByRole("button", { name: "Edit Spec" })).toBeNull()
})

test("offers a retry after a document load failure", async () => {
    const onReadArtifact = vi
        .fn()
        .mockRejectedValueOnce(new Error("offline"))
        .mockResolvedValueOnce({
            name: "spec",
            content: "# Recovered",
            revision: "new-revision",
        })
    renderTabs({ onReadArtifact })

    selectTab("Spec")
    expect(
        await screen.findByText(/Could not load this document: offline/)
    ).toBeVisible()
    fireEvent.click(screen.getByRole("button", { name: "Retry" }))
    expect(
        await screen.findByRole("heading", { name: "Recovered" })
    ).toBeVisible()
    expect(onReadArtifact).toHaveBeenCalledTimes(2)
})

test("resets to Initial Request when the work item changes", async () => {
    const { rerender } = renderTabs()
    selectTab("Spec")
    expect(
        await screen.findByRole("heading", { name: "Loaded spec" })
    ).toBeVisible()

    rerender(
        <ThemeProvider>
            <WorkDocumentTabs
                item={{ slug: "second-item", body: "# Second request" }}
                artifacts={artifacts}
                onEditInitialRequest={() => undefined}
                onEditArtifact={() => undefined}
                onReadArtifact={async (_slug, name) => ({
                    name,
                    content: "# Should not load",
                    revision: "revision",
                })}
            />
        </ThemeProvider>
    )

    await waitFor(() =>
        expect(
            screen.getByRole("tab", { name: "Initial Request" })
        ).toHaveAttribute("aria-selected", "true")
    )
    expect(
        screen.getByRole("heading", { name: "Second request" })
    ).toBeVisible()
})

test("does not render the intake fallback under the request's name", () => {
    // `item.body` falls back to the intake, so an absent request would otherwise
    // show raw intake labelled "Initial Request".
    renderTabs({ present: ["spec", "plan"] })

    expect(screen.queryByRole("heading", { name: "Initial body" })).toBeNull()
    expect(
        screen.getByText("Initial Request is not yet present.")
    ).toBeVisible()
    expect(
        screen.getByRole("button", { name: "Edit Initial Request" })
    ).toBeVisible()
})

import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { ThemeProvider } from "../theme"
import { project, STAGES, workDetail } from "../test-fixtures"
import type { WorkDetail } from "../model/types"
import { WorkDocumentTabs } from "./work-document-tabs"

function renderTabs(
    detail: WorkDetail,
    options: {
        current?: string | null
        read?: (path: string) => Promise<{ content: string; revision: string }>
        onNewFile?: (stage: string, kind: string) => void
        onEditFile?: (stage: string, path: string) => void
        stages?: typeof STAGES
    } = {}
) {
    const read =
        options.read ??
        (async (path: string) => ({ content: `# ${path}`, revision: "r" }))
    return render(
        <ThemeProvider>
            <WorkDocumentTabs
                project={project({ stages: options.stages ?? STAGES })}
                detail={detail}
                current={options.current ?? null}
                readFile={read}
                onNewFile={options.onNewFile}
                onEditFile={options.onEditFile}
            />
        </ThemeProvider>
    )
}

test("one tab per stage that keeps an artifact, in the table's order", () => {
    renderTabs(workDetail("x"))
    expect(
        screen.getAllByRole("tab").map((tab) => tab.getAttribute("aria-label"))
    ).toEqual(["Ask", "Build", "Judge", "Lessons"])
})

test("opens on the item's own stage", () => {
    renderTabs(workDetail("x"), { current: "judge" })
    expect(screen.getByRole("tab", { name: "Judge" })).toHaveAttribute(
        "aria-selected",
        "true"
    )
    expect(screen.getByText(/Current verdict/)).toHaveTextContent(
        "Current verdict: none"
    )
})

test("a document not written offers Create only where editing is offered", () => {
    const onNewFile = vi.fn()
    const { unmount } = renderTabs(workDetail("x"))
    expect(screen.getByText("Not written.")).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "Create" })).toBeNull()
    unmount()
    renderTabs(workDetail("x"), { onNewFile })
    fireEvent.click(screen.getByRole("button", { name: "Create" }))
    expect(onNewFile).toHaveBeenCalledWith("ask", "document")
})

test("a written document is read and shown, with Edit", async () => {
    const detail = workDetail("x")
    detail.files[0].document = {
        path: "ask/ask.md",
        revision: "r",
        present: true,
    }
    const onEditFile = vi.fn()
    renderTabs(detail, { onEditFile })
    expect(
        await screen.findByRole("heading", { name: "ask/ask.md" })
    ).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: "Edit" }))
    expect(onEditFile).toHaveBeenCalledWith("ask", "ask/ask.md")
})

test("a read that fails says why and offers Retry", async () => {
    const detail = workDetail("x")
    detail.files[0].document = {
        path: "ask/ask.md",
        revision: "r",
        present: true,
    }
    let fail = true
    renderTabs(detail, {
        read: async () => {
            if (fail) throw new Error("disk trouble")
            return { content: "# Fine", revision: "r" }
        },
    })
    expect(await screen.findByText(/disk trouble/)).toBeInTheDocument()
    fail = false
    fireEvent.click(screen.getByRole("button", { name: "Retry" }))
    expect(
        await screen.findByRole("heading", { name: "Fine" })
    ).toBeInTheDocument()
})

test("rounds list newest first with their verdicts, the newest shown", async () => {
    const detail = workDetail("x", {
        verdicts: [{ stage: "judge", verdict: "rejected" }],
    })
    detail.files[2].rounds = [
        {
            path: "judge/round-2.md",
            revision: "b",
            number: 2,
            verdict: "rejected",
        },
        {
            path: "judge/round-1.md",
            revision: "a",
            number: 1,
            verdict: "invalid",
        },
    ]
    detail.files[2].handoffs = [
        { path: "judge/handoff-20261001T090000Z.md", revision: "h" },
    ]
    const onNewFile = vi.fn()
    renderTabs(detail, { current: "judge", onNewFile })
    expect(screen.getByText(/Current verdict/)).toHaveTextContent("rejected")
    const rounds = screen.getAllByRole("button", { name: /^Round/ })
    expect(rounds.map((button) => button.textContent)).toEqual([
        "Round 2",
        "Round 1",
    ])
    expect(screen.getByText("invalid")).toBeInTheDocument()
    expect(
        await screen.findByRole("heading", { name: "judge/round-2.md" })
    ).toBeInTheDocument()
    expect(
        screen.getByRole("button", { name: "handoff-20261001T090000Z.md" })
    ).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: "New round" }))
    fireEvent.click(screen.getByRole("button", { name: "New handoff" }))
    expect(onNewFile.mock.calls).toEqual([
        ["judge", "round"],
        ["judge", "handoff"],
    ])
})

test("a stage the backend keeps says so, with the ticket's link", () => {
    const stages = STAGES.map((row) =>
        row.name === "ask" ? { ...row, external: true } : row
    )
    renderTabs(
        workDetail("x", {
            link: { label: "Tracker", url: "https://tracker.example/X-1" },
        }),
        { stages }
    )
    expect(
        screen.getByText("This project's backend keeps the ask record.")
    ).toBeInTheDocument()
    expect(
        screen.getByRole("link", { name: "Open in Tracker" })
    ).toHaveAttribute("href", "https://tracker.example/X-1")
})

test("switching tabs shows that stage's files", async () => {
    renderTabs(workDetail("x"))
    fireEvent.mouseDown(screen.getByRole("tab", { name: "Build" }))
    await waitFor(() =>
        expect(screen.getByText("No rounds yet.")).toBeInTheDocument()
    )
})

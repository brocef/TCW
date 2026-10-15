import { fireEvent, render, screen } from "@testing-library/react"
import { ThemeProvider } from "../theme"
import { project, workDetail, workItem } from "../test-fixtures"
import type { WorkDetail } from "../model/types"
import { WorkPage } from "./work-views"

function renderPage(detail: WorkDetail, onRetry = vi.fn()) {
    render(
        <ThemeProvider>
            <WorkPage
                project={project()}
                detail={detail}
                readFile={async () => ({ content: "", revision: "r" })}
                onRetry={onRetry}
            />
        </ThemeProvider>
    )
    return onRetry
}

test("the stage is shown with the command that moves it, and nothing moves it", () => {
    renderPage(workDetail("x"))
    const line = screen.getByText(/^Stage:/)
    expect(line).toHaveTextContent(
        "Stage: ask. Move it with tcw work advance p/x."
    )
    expect(line.querySelector("code")).toHaveTextContent("tcw work advance p/x")
    for (const name of [/start/i, /complete/i, /advance/i, /drop/i, /discard/i])
        expect(screen.queryByRole("button", { name })).toBeNull()
})

test("links to this project's items navigate; another project's are labelled", () => {
    renderPage(
        workDetail("x", {
            item: workItem("x", {
                parent: "p/epic",
                "blocked-by": ["q/2026-01-01-theirs"],
                blocks: ["p/after"],
            }),
        })
    )
    expect(screen.getByRole("link", { name: "epic" })).toHaveAttribute(
        "data-nav-key",
        "epic"
    )
    expect(screen.getByRole("link", { name: "after" })).toHaveAttribute(
        "href",
        "/work/after"
    )
    const theirs = screen.getByText("2026-01-01-theirs", { exact: false })
    expect(theirs.closest("a")).toBeNull()
    expect(theirs.closest("[title]")).toHaveAttribute(
        "title",
        "In project q; open it there"
    )
})

test("comments read oldest first, by display name, and say when limited", () => {
    renderPage(
        workDetail("x", {
            comments: [
                { at: "2026-10-01T09:00:00Z", author: "acc-1", text: "first" },
                { at: "2026-10-02T09:00:00Z", author: "acc-2", text: "second" },
            ],
            commentsLimited: true,
            people: { "acc-1": "Ann" },
        })
    )
    const texts = screen.getAllByText(/^(first|second)$/)
    expect(texts.map((node) => node.textContent)).toEqual(["first", "second"])
    expect(screen.getByText(/^Ann ·/)).toBeInTheDocument()
    expect(screen.getByText(/^acc-2 ·/)).toBeInTheDocument()
    expect(screen.getByText("Showing the newest 2.")).toBeInTheDocument()
})

test("each part the backend could not give says so, with Retry", () => {
    const onRetry = renderPage(
        workDetail("x", {
            item: { unavailable: "Jira is unreachable" },
            requestText: { unavailable: "Jira is unreachable" },
            comments: { unavailable: "TCW_JIRA_TOKEN is not set" },
        })
    )
    expect(
        screen.getByText(
            /stage and properties could not be read: Jira is unreachable/
        )
    ).toBeInTheDocument()
    expect(
        screen.getByText(/The request could not be read/)
    ).toBeInTheDocument()
    expect(
        screen.getByText(
            /comments could not be read: TCW_JIRA_TOKEN is not set/
        )
    ).toBeInTheDocument()
    const retries = screen.getAllByRole("button", { name: "Retry" })
    expect(retries).toHaveLength(3)
    fireEvent.click(retries[0])
    expect(onRetry).toHaveBeenCalled()
    // The files stay readable: the stage tabs are still drawn.
    expect(screen.getByRole("tab", { name: "Ask" })).toBeInTheDocument()
})

test("the request the backend keeps is shown, and the ticket opens there", () => {
    renderPage(
        workDetail("x", {
            requestText: "Please build it.",
            link: { label: "Tracker", url: "https://tracker.example/X-1" },
            item: workItem("x", { untracked: ["X-9"] }),
        })
    )
    expect(screen.getByText("Please build it.")).toBeInTheDocument()
    expect(
        screen.getAllByRole("link", { name: "Open in Tracker" })[0]
    ).toHaveAttribute("href", "https://tracker.example/X-1")
    expect(screen.getByText("Linked tickets with no item")).toBeInTheDocument()
    expect(screen.getByText("X-9")).toBeInTheDocument()
})

test("a missing priority reads as none", () => {
    renderPage(workDetail("x", { item: workItem("x", { priority: null }) }))
    expect(screen.getByText("none")).toBeInTheDocument()
})

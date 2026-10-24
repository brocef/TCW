import { fireEvent, render, screen } from "@testing-library/react"
import { expect, test, vi } from "vitest"
import { ThemeProvider } from "../theme"
import type { TScopeChoice } from "../model/scope"
import type { TProject } from "../model/types"
import { ScopeControl } from "./scope-control"

// Radix's Select scrolls its chosen option into view, which jsdom lacks.
window.HTMLElement.prototype.scrollIntoView = vi.fn()

const FAMILY: TProject["scopes"] = {
    own: ["shared"],
    up: ["docs", "shared"],
    down: ["shared", "desktop", "server", "mobile"],
    all: ["docs", "shared", "desktop", "server", "mobile"],
}

function show(
    scopes: TProject["scopes"],
    choice: TScopeChoice = { scope: "own" },
    onChange = vi.fn()
) {
    render(
        <ThemeProvider>
            <ScopeControl scopes={scopes} choice={choice} onChange={onChange} />
        </ThemeProvider>
    )
    return onChange
}

test("hidden for a project with no family", () => {
    show({ own: ["p"], up: ["p"], down: ["p"], all: ["p"] })
    expect(screen.queryByRole("combobox", { name: "Scope" })).toBeNull()
    expect(screen.queryByRole("combobox", { name: "Project" })).toBeNull()
})

test("offers the four scopes, each labelled, own chosen by default", async () => {
    const onChange = show(FAMILY)
    const scope = screen.getByRole("combobox", { name: "Scope" })
    expect(scope).toHaveTextContent("own: This project")
    fireEvent.click(scope)
    const offered = (await screen.findAllByRole("option")).map(
        (option) => option.textContent
    )
    expect(offered).toEqual([
        "own: This project",
        "up: With its ancestors",
        "down: With its descendants",
        "all: Ancestors and descendants",
    ])
    fireEvent.click(screen.getByRole("option", { name: /^down/ }))
    expect(onChange).toHaveBeenCalledWith({ scope: "down" })
})

test("the project filter offers the scope's projects and all of them", async () => {
    const onChange = show(FAMILY, { scope: "down" })
    const project = screen.getByRole("combobox", { name: "Project" })
    expect(project).toHaveTextContent("All of them")
    fireEvent.click(project)
    const offered = (await screen.findAllByRole("option")).map(
        (option) => option.textContent
    )
    expect(offered).toEqual([
        "All of them",
        "shared",
        "desktop",
        "server",
        "mobile",
    ])
    fireEvent.click(screen.getByRole("option", { name: "desktop" }))
    expect(onChange).toHaveBeenCalledWith({ scope: "down", project: "desktop" })
})

test("a project the new scope does not cover is dropped", async () => {
    const onChange = show(FAMILY, { scope: "down", project: "desktop" })
    fireEvent.click(screen.getByRole("combobox", { name: "Scope" }))
    fireEvent.click(await screen.findByRole("option", { name: /^up/ }))
    expect(onChange).toHaveBeenCalledWith({ scope: "up" })
})

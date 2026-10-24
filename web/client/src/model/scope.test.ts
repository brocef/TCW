import { expect, test } from "vitest"
import {
    detailScope,
    scopeParams,
    scopeSearch,
    statusSummary,
    withScope,
} from "./scope"

test("the query string names the scope and the project", () => {
    expect(scopeParams("?scope=down&project=desktop")).toEqual({
        scope: "down",
        project: "desktop",
    })
    expect(scopeParams("?scope=up")).toEqual({ scope: "up" })
    expect(scopeParams("")).toEqual({ scope: "own" })
})

test("an unknown scope reads as own", () => {
    expect(scopeParams("?scope=sideways")).toEqual({ scope: "own" })
})

test("a path asks for the choice after any parameters it has", () => {
    expect(withScope("/api/work?all=1", { scope: "down" })).toBe(
        "/api/work?all=1&scope=down"
    )
    expect(withScope("/api/work", { scope: "down", project: "desktop" })).toBe(
        "/api/work?scope=down&project=desktop"
    )
    expect(withScope("/api/taxonomy", { scope: "own" })).toBe("/api/taxonomy")
    expect(scopeSearch({ scope: "own" })).toBe("")
    expect(scopeSearch({ scope: "own", project: "p" })).toBe("?project=p")
})

test("a status summary counts each status in first-appearance order", () => {
    expect(
        statusSummary([
            { project: "shared", status: "Missing", inherited: false },
            { project: "desktop", status: "Supported", inherited: false },
            { project: "server", status: "Omitted", inherited: false },
        ])
    ).toBe("Missing(1), Supported(1), Omitted(1)")
    expect(
        statusSummary([
            { project: "a", status: "Supported", inherited: false },
            { project: "b", status: "Missing", inherited: true },
            { project: "c", status: "Supported", inherited: true },
            { project: "d", status: null, inherited: false },
        ])
    ).toBe("Supported(2), Missing(1), (no status)(1)")
})

test("a detail request keeps the project only when it owns the object", () => {
    const choice = { scope: "down" as const, project: "desktop" }
    expect(detailScope(choice, "desktop")).toEqual(choice)
    expect(detailScope(choice, "server")).toEqual({ scope: "down" })
    expect(detailScope({ scope: "up" }, "p")).toEqual({ scope: "up" })
})

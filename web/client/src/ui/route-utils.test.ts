import { describe, expect, test } from "vitest"
import { itemKey, parsePath, pathFor } from "./route-utils"
import { capability, term, workItem } from "../test-fixtures"

describe("route utilities", () => {
    test.each([
        ["taxonomy", "feature/local-web-app"],
        ["capabilities", "web/editing"],
        ["work", "2026-10-01-example-item"],
    ] as const)("round trips %s object routes", (axis, key) => {
        expect(parsePath(pathFor(axis, key))).toEqual({ axis, key })
    })

    test("a work item's URL is its folder", () => {
        expect(pathFor("work", "2026-10-01-x")).toBe("/work/2026-10-01-x")
        expect(itemKey("work", workItem("2026-10-01-x"), "p")).toBe(
            "2026-10-01-x"
        )
    })

    test("TCW-110 AC 20a: this project's entry is keyed by its id-path, an inherited one by its full identifier", () => {
        expect(
            itemKey("work", workItem("x", { "full-id": "demo.work/x" }), "demo")
        ).toBe("x")
        expect(
            itemKey("capabilities", capability("cli/x", {}, "demo"), "demo")
        ).toBe("cli/x")
        expect(
            itemKey("capabilities", capability("cli/y", {}, "core"), "demo")
        ).toBe("core.capabilities/cli/y")
        expect(itemKey("taxonomy", term("term", {}, "core"), "demo")).toBe(
            "core.taxonomy/term"
        )
    })

    test("an inherited entry's key round trips through its route", () => {
        const key = "core.capabilities/cli/y"
        expect(parsePath(pathFor("capabilities", key))).toEqual({
            axis: "capabilities",
            key,
        })
    })

    test("defaults unknown paths to the work list", () => {
        expect(parsePath("/not-an-axis")).toEqual({ axis: "work", key: null })
    })
})

test("TCW-113 Design 6.3: another project's work item is keyed by its full identifier", () => {
    const theirs = workItem("x", {
        "full-id": "desktop.work/x",
        owner: "desktop",
    })
    expect(itemKey("work", theirs, "shared")).toBe("desktop.work/x")
    const ours = workItem("x", { "full-id": "shared.work/x", owner: "shared" })
    expect(itemKey("work", ours, "shared")).toBe("x")
})

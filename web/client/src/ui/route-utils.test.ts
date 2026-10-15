import { describe, expect, test } from "vitest"
import { itemKey, parsePath, pathFor } from "./route-utils"
import { workItem } from "../test-fixtures"

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
        expect(itemKey("work", workItem("2026-10-01-x"))).toBe("2026-10-01-x")
    })

    test("defaults unknown paths to the work list", () => {
        expect(parsePath("/not-an-axis")).toEqual({ axis: "work", key: null })
    })
})

import { describe, expect, test } from "vitest"
import { parsePath, pathFor } from "./route-utils"

describe("route utilities", () => {
    test.each([
        ["taxonomy", "feature/local-web-app"],
        ["capabilities", "web/editing"],
        ["work", "child-node/example-item"],
    ] as const)("round trips %s object routes", (axis, key) => {
        expect(parsePath(pathFor(axis, key))).toEqual({ axis, key })
    })

    test("defaults unknown paths to the work list", () => {
        expect(parsePath("/not-an-axis")).toEqual({ axis: "work", key: null })
    })
})

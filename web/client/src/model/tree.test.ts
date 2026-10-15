import { describe, expect, test } from "vitest"
import {
    buildPathTree,
    buildWorkTree,
    pathAncestors,
    pruneTree,
    sortWorkTree,
    workAncestors,
} from "./tree"
import { STAGES, workItem } from "../test-fixtures"

const ORDER = STAGES.map((row) => row.name)
const PRIORITIES = ["highest", "high", "medium", "low", "lowest"]

describe("path tree", () => {
    test("creates folders and selectable leaves", () => {
        const items = [{ path: "web/editing" }, { path: "web/browsing" }]
        const tree = buildPathTree(items, (item) => item.path)
        expect(tree).toHaveLength(1)
        expect(tree[0].path).toBe("web")
        expect(tree[0].children.map((node) => node.path)).toEqual([
            "web/editing",
            "web/browsing",
        ])
    })

    test("returns path ancestors", () => {
        expect(pathAncestors("a/b/c")).toEqual(["a", "a/b"])
    })
})

describe("work tree", () => {
    test("nests children under their parent's full slug", () => {
        const items = [
            workItem("parent"),
            workItem("child", { parent: "p/parent" }),
        ]
        const tree = buildWorkTree(items)
        expect(tree.map((node) => node.path)).toEqual(["p/parent"])
        expect(tree[0].children[0].path).toBe("p/child")
        expect(workAncestors("p/child", items)).toEqual(["p/parent"])
    })

    test("an item whose parent is in another project is a root", () => {
        const items = [
            workItem("parent"),
            workItem("child", { parent: "q/parent" }),
        ]
        expect(buildWorkTree(items).map((node) => node.path)).toEqual([
            "p/parent",
            "p/child",
        ])
        expect(workAncestors("p/child", items)).toEqual([])
    })

    test("keeps malformed cycles reachable", () => {
        const items = [
            workItem("a", { parent: "p/b" }),
            workItem("b", { parent: "p/a" }),
        ]
        const tree = buildWorkTree(items)
        expect(tree).toHaveLength(1)
        expect(new Set([tree[0].path, tree[0].children[0].path])).toEqual(
            new Set(["p/a", "p/b"])
        )
    })

    test("groups by the table's stage order before the chosen sort", () => {
        const tree = buildWorkTree([
            workItem("z", { title: "Zulu", stage: "ask" }),
            workItem("a", { title: "Alpha", stage: "ask" }),
            workItem("later", { title: "Aardvark", stage: "lessons" }),
            workItem("first", { title: "Yak", stage: "intake" }),
            workItem("none", { title: "A", stage: null }),
        ])
        expect(
            sortWorkTree(tree, "name", "ascending", ORDER, PRIORITIES).map(
                (node) => node.path
            )
        ).toEqual(["p/first", "p/a", "p/z", "p/later", "p/none"])
    })

    test("sorts by creation date", () => {
        const tree = buildWorkTree([
            workItem("old", { created: "2026-01-01T00:00:00+00:00" }),
            workItem("new", { created: "2026-06-01T00:00:00+00:00" }),
        ])
        expect(
            sortWorkTree(tree, "created", "descending", ORDER, PRIORITIES).map(
                (node) => node.path
            )
        ).toEqual(["p/new", "p/old"])
    })

    test.each(["ascending", "descending"] as const)(
        "a missing priority sorts after the lowest, %s",
        (direction) => {
            const tree = buildWorkTree([
                workItem("none", { priority: null }),
                workItem("low", { priority: "lowest" }),
                workItem("top", { priority: "highest" }),
            ])
            const sorted = sortWorkTree(
                tree,
                "priority",
                direction,
                ORDER,
                PRIORITIES
            ).map((node) => node.path)
            expect(sorted[2]).toBe("p/none")
            expect(sorted.slice(0, 2)).toEqual(
                direction === "ascending"
                    ? ["p/top", "p/low"]
                    : ["p/low", "p/top"]
            )
        }
    )
})

test("prune keeps matching branches and reports expansion", () => {
    const tree = buildPathTree(
        [{ path: "web/editing" }, { path: "cli/help" }],
        (item) => item.path
    )
    const result = pruneTree(tree, (item) => item.path.includes("editing"))
    expect(result.nodes.map((node) => node.path)).toEqual(["web"])
    expect(result.forceExpand).toEqual(new Set(["web"]))
})

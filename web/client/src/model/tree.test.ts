import { describe, expect, test } from "vitest"
import {
    buildPathTree,
    buildWorkTree,
    pathAncestors,
    pathTreeAncestors,
    pruneTree,
    sortWorkTree,
    workAncestors,
} from "./tree"
import { STAGES, workItem } from "../test-fixtures"
import type { TreeNode } from "./types"

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

    test("an inherited entry sits under one top node for its owner and namespace", () => {
        const keys = [
            "cli/x",
            "core.capabilities/cli/y",
            "core.capabilities/web",
        ]
        const tree = buildPathTree(keys, (key) => key)
        expect(tree.map((node) => node.name)).toEqual([
            "cli",
            "core.capabilities",
        ])
        const core = tree[1]
        expect(core.children.map((node) => node.path)).toEqual([
            "core.capabilities/cli",
            "core.capabilities/web",
        ])
        expect(core.children[0].children[0].item).toBe(
            "core.capabilities/cli/y"
        )
        expect(pathAncestors("core.capabilities/cli/y")).toEqual([
            "core.capabilities",
            "core.capabilities/cli",
        ])
    })
})

describe("path tree by parent", () => {
    interface TRow {
        key: string
        parent?: string | null
    }
    const build = (rows: TRow[]) =>
        buildPathTree(
            rows,
            (row) => row.key,
            (row) => row.parent ?? null
        )
    const paths = (nodes: Array<TreeNode<TRow>>): unknown =>
        nodes.map((node) =>
            node.children.length
                ? { [node.path]: paths(node.children) }
                : node.path
        )

    test("a child of another project's listed record sits under it", () => {
        const tree = build([
            { key: "core.taxonomy/billing" },
            { key: "refund", parent: "core.taxonomy/billing" },
        ])
        expect(paths(tree)).toEqual([
            { "core.taxonomy": [{ "core.taxonomy/billing": ["refund"] }] },
        ])
        expect(pathTreeAncestors(tree, "refund")).toEqual([
            "core.taxonomy",
            "core.taxonomy/billing",
        ])
    })

    test("a child of a record that is not listed sits under labels for it", () => {
        const tree = build([
            { key: "invoice" },
            { key: "refund", parent: "core.taxonomy/billing" },
        ])
        expect(paths(tree)).toEqual([
            "invoice",
            { "core.taxonomy": [{ "core.taxonomy/billing": ["refund"] }] },
        ])
        expect(tree[1].item).toBeNull()
        expect(tree[1].children[0].item).toBeNull()
        expect(tree[1].children[0].children[0].item?.key).toBe("refund")
    })

    test("a flat child of this project's own record sits under it", () => {
        const tree = build([
            { key: "invoice" },
            { key: "receipt", parent: "invoice" },
        ])
        expect(paths(tree)).toEqual([{ invoice: ["receipt"] }])
    })

    test("no parent, or the folder's own parent, keeps the path tree", () => {
        const rows = [
            { key: "a" },
            { key: "a/b", parent: "a" },
            { key: "a/c" },
            { key: "core.taxonomy/x/y" },
        ]
        expect(paths(build(rows))).toEqual(
            paths(buildPathTree(rows, (row) => row.key))
        )
    })

    test("records naming each other as parent each appear once", () => {
        const tree = build([
            { key: "a", parent: "b" },
            { key: "b", parent: "a" },
        ])
        const seen: string[] = []
        const walk = (nodes: Array<TreeNode<TRow>>) =>
            nodes.forEach((node) => {
                seen.push(node.path)
                walk(node.children)
            })
        walk(tree)
        expect(seen.sort()).toEqual(["a", "b"])
    })

    test("a record naming itself as parent is placed by its folder", () => {
        expect(paths(build([{ key: "a", parent: "a" }]))).toEqual(["a"])
    })

    test("ancestors of a path that is not in the tree are none", () => {
        expect(pathTreeAncestors(build([{ key: "a" }]), "zz")).toEqual([])
    })
})

describe("work tree", () => {
    test("nests children under their parent's full slug", () => {
        const items = [
            workItem("parent"),
            workItem("child", { parent: "p.work/parent" }),
        ]
        const tree = buildWorkTree(items)
        expect(tree.map((node) => node.path)).toEqual(["p.work/parent"])
        expect(tree[0].children[0].path).toBe("p.work/child")
        expect(workAncestors("p.work/child", items)).toEqual(["p.work/parent"])
    })

    test("an item whose parent is in another project is a root", () => {
        const items = [
            workItem("parent"),
            workItem("child", { parent: "q.work/parent" }),
        ]
        expect(buildWorkTree(items).map((node) => node.path)).toEqual([
            "p.work/parent",
            "p.work/child",
        ])
        expect(workAncestors("p.work/child", items)).toEqual([])
    })

    test("keeps malformed cycles reachable", () => {
        const items = [
            workItem("a", { parent: "p.work/b" }),
            workItem("b", { parent: "p.work/a" }),
        ]
        const tree = buildWorkTree(items)
        expect(tree).toHaveLength(1)
        expect(new Set([tree[0].path, tree[0].children[0].path])).toEqual(
            new Set(["p.work/a", "p.work/b"])
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
        ).toEqual([
            "p.work/first",
            "p.work/a",
            "p.work/z",
            "p.work/later",
            "p.work/none",
        ])
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
        ).toEqual(["p.work/new", "p.work/old"])
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
            expect(sorted[2]).toBe("p.work/none")
            expect(sorted.slice(0, 2)).toEqual(
                direction === "ascending"
                    ? ["p.work/top", "p.work/low"]
                    : ["p.work/low", "p.work/top"]
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

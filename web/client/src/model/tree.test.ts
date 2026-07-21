import { describe, expect, test } from "vitest";
import { buildPathTree, buildWorkTree, pathAncestors, pruneTree, workAncestors } from "./tree";
import type { WorkItem } from "./types";

describe("path tree", () => {
  test("creates folders and selectable leaves", () => {
    const items = [{ path: "web/editing" }, { path: "web/browsing" }];
    const tree = buildPathTree(items, (item) => item.path);
    expect(tree).toHaveLength(1);
    expect(tree[0].path).toBe("web");
    expect(tree[0].children.map((node) => node.path)).toEqual(["web/editing", "web/browsing"]);
  });

  test("returns path ancestors", () => {
    expect(pathAncestors("a/b/c")).toEqual(["a", "a/b"]);
  });
});

describe("work tree", () => {
  test("nests children under their parent", () => {
    const items: WorkItem[] = [{ slug: "parent" }, { slug: "child", parent: "parent" }];
    const tree = buildWorkTree(items);
    expect(tree.map((node) => node.path)).toEqual(["parent"]);
    expect(tree[0].children[0].path).toBe("child");
  });

  test("resolves qualified parent in the child namespace", () => {
    const items: WorkItem[] = [{ slug: "sub/parent" }, { slug: "sub/child", parent: "parent" }];
    expect(buildWorkTree(items)[0].children[0].path).toBe("sub/child");
    expect(workAncestors("sub/child", items)).toEqual(["sub/parent"]);
  });

  test("keeps malformed cycles reachable", () => {
    const items: WorkItem[] = [{ slug: "a", parent: "b" }, { slug: "b", parent: "a" }];
    const tree = buildWorkTree(items);
    expect(tree).toHaveLength(1);
    expect(new Set([tree[0].path, tree[0].children[0].path])).toEqual(new Set(["a", "b"]));
  });
});

test("prune keeps matching branches and reports expansion", () => {
  const tree = buildPathTree([{ path: "web/editing" }, { path: "cli/help" }], (item) => item.path);
  const result = pruneTree(tree, (item) => item.path.includes("editing"));
  expect(result.nodes.map((node) => node.path)).toEqual(["web"]);
  expect(result.forceExpand).toEqual(new Set(["web"]));
});

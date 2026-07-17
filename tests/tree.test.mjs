import { strictEqual, deepStrictEqual, ok } from "node:assert";
import { describe, it } from "node:test";
import * as Tree from "../tcw/serve/static/tree.js";

describe("buildPathTree", () => {
  it("produces folders and selectable nodes", () => {
    var items = [
      { name: "Auth", path: "auth" },
      { name: "Auth Login", path: "auth/login" },
      { name: "Web", path: "web" },
      { name: "Web Editing", path: "web/editing" },
      { name: "CLI", path: "cli/run" },
    ];
    var tree = Tree.buildPathTree(items, function (i) { return i.path; });

    // Roots: "auth", "web", "cli" (cli is a folder, not selectable)
    strictEqual(tree.length, 3);

    var auth = tree.find(function (n) { return n.name === "auth"; });
    ok(auth, "auth root exists");
    ok(auth.item, "auth is selectable");
    strictEqual(auth.children.length, 1);
    strictEqual(auth.children[0].name, "login");
    ok(auth.children[0].item, "auth/login is selectable");

    var web = tree.find(function (n) { return n.name === "web"; });
    ok(web, "web root exists");
    ok(web.item, "web is selectable");
    strictEqual(web.children.length, 1);
    strictEqual(web.children[0].name, "editing");
    ok(web.children[0].item, "web/editing is selectable");

    var cli = tree.find(function (n) { return n.name === "cli"; });
    ok(cli, "cli folder exists");
    strictEqual(cli.item, null, "cli folder is not selectable");
    strictEqual(cli.children.length, 1);
    ok(cli.children[0].item, "cli/run is selectable");
  });

  it("handles empty input", () => {
    strictEqual(Tree.buildPathTree([], function () { return ""; }).length, 0);
  });

  it("handles single root item", () => {
    var tree = Tree.buildPathTree([{ name: "X", path: "x" }], function (i) { return i.path; });
    strictEqual(tree.length, 1);
    ok(tree[0].item);
    strictEqual(tree[0].children.length, 0);
  });

  it("handles deeply nested path", () => {
    var tree = Tree.buildPathTree(
      [{ name: "D", path: "a/b/c/d" }],
      function (i) { return i.path; }
    );
    strictEqual(tree.length, 1);
    var a = tree[0];
    strictEqual(a.name, "a");
    strictEqual(a.item, null);
    var b = a.children[0];
    strictEqual(b.name, "b");
    strictEqual(b.item, null);
    var c = b.children[0];
    strictEqual(c.name, "c");
    strictEqual(c.item, null);
    var d = c.children[0];
    strictEqual(d.name, "d");
    ok(d.item);
  });

  it("federated items nest under non-selectable origin folder", () => {
    var items = [
      { name: "Term", qualified: "shared/term" },
      { name: "Local", qualified: "local" },
    ];
    var tree = Tree.buildPathTree(items, function (i) { return i.qualified; });

    var shared = tree.find(function (n) { return n.name === "shared"; });
    ok(shared, "shared origin folder exists");
    strictEqual(shared.item, null, "origin folder is not selectable");
    ok(shared.children[0].item, "shared/term is selectable");

    var local = tree.find(function (n) { return n.name === "local"; });
    ok(local && local.item, "local is selectable");
  });
});

describe("buildWorkTree", () => {
  it("nests children under their parent", () => {
    var items = [
      { slug: "parent-item", title: "Parent", parent: "", status: "active" },
      { slug: "child-item", title: "Child", parent: "parent-item", status: "backlog" },
    ];
    var tree = Tree.buildWorkTree(items, function (i) { return i.slug; });

    strictEqual(tree.length, 1);
    strictEqual(tree[0].name, "Parent");
    ok(tree[0].item);
    strictEqual(tree[0].children.length, 1);
    strictEqual(tree[0].children[0].name, "Child");
  });

  it("missing parent promotes child to root with key intact", () => {
    var items = [
      { slug: "orphan", title: "Orphan", parent: "nonexistent", status: "backlog" },
    ];
    var tree = Tree.buildWorkTree(items, function (i) { return i.slug; });

    strictEqual(tree.length, 1);
    strictEqual(tree[0].path, "orphan", "key is unchanged");
    ok(tree[0].item);
  });

  it("qualified slugs resolve parent in-namespace", () => {
    var items = [
      { slug: "sub/proj/parent", title: "Parent", parent: "", status: "active" },
      { slug: "sub/proj/child", title: "Child", parent: "parent", status: "backlog" },
    ];
    var tree = Tree.buildWorkTree(items, function (i) { return i.slug; });

    strictEqual(tree.length, 1);
    strictEqual(tree[0].path, "sub/proj/parent");
    strictEqual(tree[0].children.length, 1);
    strictEqual(tree[0].children[0].path, "sub/proj/child");
  });

  it("substring-but-not-namespace parent stays root", () => {
    var items = [
      { slug: "foo", title: "Foo", parent: "", status: "active" },
      { slug: "foobar", title: "Foobar", parent: "foo", status: "backlog" },
    ];
    var tree = Tree.buildWorkTree(items, function (i) { return i.slug; });

    // "foo" is the parent of "foobar" — bare slug resolves parent bare
    strictEqual(tree.length, 1);
    strictEqual(tree[0].path, "foo");
    strictEqual(tree[0].children.length, 1);
    strictEqual(tree[0].children[0].path, "foobar");
  });
});

describe("pruneTree", () => {
  it("keeps matching parent with matching child, reports force-expand", () => {
    var tree = Tree.buildPathTree(
      [
        { name: "A", path: "a" },
        { name: "B", path: "a/b" },
        { name: "C", path: "a/c" },
      ],
      function (i) { return i.path; }
    );
    var result = Tree.pruneTree(tree, function (item) {
      return item && item.path === "a/c";
    });
    strictEqual(result.nodes.length, 1);
    strictEqual(result.nodes[0].path, "a");
    strictEqual(result.nodes[0].children.length, 1);
    strictEqual(result.nodes[0].children[0].path, "a/c");
    ok(result.forceExpand.has("a"), "parent is force-expanded");
  });

  it("drops non-matching branch entirely", () => {
    var tree = Tree.buildPathTree(
      [{ name: "X", path: "x" }],
      function (i) { return i.path; }
    );
    var result = Tree.pruneTree(tree, function () { return false; });
    strictEqual(result.nodes.length, 0);
  });

  it("keeps all when all match", () => {
    var tree = Tree.buildPathTree(
      [{ name: "A", path: "a" }, { name: "B", path: "a/b" }],
      function (i) { return i.path; }
    );
    var result = Tree.pruneTree(tree, function () { return true; });
    strictEqual(result.nodes.length, 1);
    strictEqual(result.nodes[0].children.length, 1);
  });
});

describe("ancestorsOf", () => {
  it("path mode returns segment prefixes", () => {
    var result = Tree.ancestorsOf("a/b/c", "path");
    deepStrictEqual(result, ["a", "a/b"]);
  });

  it("work mode returns parent chain", () => {
    var items = [
      { slug: "root", title: "Root", parent: "" },
      { slug: "mid", title: "Mid", parent: "root" },
      { slug: "leaf", title: "Leaf", parent: "mid" },
    ];
    var result = Tree.ancestorsOf("leaf", "work", items);
    deepStrictEqual(result, ["root", "mid"]);
  });

  it("unknown key returns empty array without throwing", () => {
    var result = Tree.ancestorsOf("unknown-axis/unknown-key", "path");
    deepStrictEqual(result, ["unknown-axis"]);
  });
});

describe("mergeExpansion", () => {
  it("force-expand paths are added to user-expanded set", () => {
    var user = new Set(["a", "b"]);
    var force = new Set(["b", "c"]);
    var result = Tree.mergeExpansion(user, force);
    ok(result.has("a"), "user expand preserved");
    ok(result.has("b"), "common path present");
    ok(result.has("c"), "force-expand added");
  });

  it("empty inputs produce empty set", () => {
    var result = Tree.mergeExpansion(new Set(), new Set());
    strictEqual(result.size, 0);
  });
});

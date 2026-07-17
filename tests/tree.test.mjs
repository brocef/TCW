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

  it("keys named after Object.prototype properties are safe", () => {
    // "constructor" is a producible slug (a term named "Constructor");
    // "__proto__" is accepted as an explicit slug. Neither may crash the
    // build, drop an item, or pollute Object.prototype.
    var items = [
      { name: "C", path: "constructor" },
      { name: "CC", path: "constructor/child" },
      { name: "P", path: "__proto__" },
    ];
    var tree = Tree.buildPathTree(items, function (i) { return i.path; });
    var paths = tree.map(function (n) { return n.path; }).sort();
    deepStrictEqual(paths, ["__proto__", "constructor"]);
    var ctor = tree.find(function (n) { return n.path === "constructor"; });
    ok(ctor.item, "constructor node selectable");
    strictEqual(ctor.children.length, 1);
    strictEqual(({}).item, undefined, "Object.prototype not polluted");

    var work = Tree.buildWorkTree(
      [{ slug: "toString", title: "T", parent: "" },
       { slug: "valueOf", title: "V", parent: "toString" }],
      function (i) { return i.slug; }
    );
    strictEqual(work.length, 1);
    strictEqual(work[0].children[0].path, "valueOf");
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

  it("parent cycle does not hang and every item stays reachable", () => {
    var items = [
      { slug: "a", title: "A", parent: "b", status: "active" },
      { slug: "b", title: "B", parent: "a", status: "active" },
      { slug: "solo", title: "Solo", parent: "", status: "backlog" },
    ];
    var tree = Tree.buildWorkTree(items, function (i) { return i.slug; });

    // Collect all reachable paths
    var seen = [];
    function walk(nodes) {
      nodes.forEach(function (n) { seen.push(n.path); walk(n.children); });
    }
    walk(tree);
    deepStrictEqual(seen.sort(), ["a", "b", "solo"], "no item vanishes in a cycle");
  });

  it("self-parent stays root", () => {
    var items = [{ slug: "x", title: "X", parent: "x", status: "active" }];
    var tree = Tree.buildWorkTree(items, function (i) { return i.slug; });
    strictEqual(tree.length, 1);
    strictEqual(tree[0].path, "x");
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

  it("path mode returns prefixes even for a key not in any item set", () => {
    var result = Tree.ancestorsOf("unknown-axis/unknown-key", "path");
    deepStrictEqual(result, ["unknown-axis"]);
  });

  it("work mode with a parent cycle terminates", () => {
    var items = [
      { slug: "a", title: "A", parent: "b" },
      { slug: "b", title: "B", parent: "a" },
    ];
    var result = Tree.ancestorsOf("a", "work", items);
    deepStrictEqual(result, ["b"], "stops at the cycle, no hang");
  });

  it("work mode unknown key returns empty without throwing", () => {
    deepStrictEqual(Tree.ancestorsOf("nope", "work", []), []);
  });

  it("work mode resolves qualified keys in-namespace", () => {
    var items = [
      { slug: "sub/proj/parent", title: "P", parent: "" },
      { slug: "sub/proj/child", title: "C", parent: "parent" },
    ];
    deepStrictEqual(Tree.ancestorsOf("sub/proj/child", "work", items),
      ["sub/proj/parent"]);
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

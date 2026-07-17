// ============================================================
// PURE TREE MODEL — no DOM, no browser globals
// ============================================================
// Consumed by app.js via <script> tag (functions become browser globals)
// and by tests/tree.test.mjs via ESM export.

/* global window */

// ── Path-axis tree (taxonomy, capabilities) ──────────────────

/**
 * Build a nested tree from `/`-delimited path keys.
 * @param {any[]} items - flat item array
 * @param {(item: any) => string} keyOf - extract the path key
 * @returns {Array} tree nodes with { name, path, item, children }
 */
function buildPathTree(items, keyOf) {
  var keySet = {};
  var keys = [];
  items.forEach(function (it) {
    var k = keyOf(it);
    if (keySet[k]) return;
    keySet[k] = true;
    keys.push(k);
  });

  var map = {}; // path -> node

  keys.forEach(function (key) {
    var segments = key.split("/");
    var cursor = "";
    segments.forEach(function (seg) {
      cursor = cursor ? cursor + "/" + seg : seg;
      if (!map[cursor]) {
        map[cursor] = { name: seg, path: cursor, item: null, children: [] };
      }
    });
    // Mark the leaf node as selectable
    map[key].item = items.find(function (it) { return keyOf(it) === key; });
  });

  // Wire parent -> children for ALL nodes in the map (including intermediate
  // folders created during path splitting), then collect unattached roots.
  var roots = [];
  var seen = {};

  // Attach every node to its parent if the parent exists in the map
  Object.keys(map).forEach(function (path) {
    var node = map[path];
    var parentPath = path.substring(0, path.lastIndexOf("/"));
    if (parentPath && map[parentPath]) {
      map[parentPath].children.push(node);
      seen[path] = true;
    }
  });

  // Collect nodes that weren't attached (true roots)
  Object.keys(map).forEach(function (path) {
    if (!seen[path]) {
      roots.push(map[path]);
    }
  });

  return roots;
}

// ── Work-axis tree (parent relation) ─────────────────────────

/**
 * Build a nested tree from work items using the `parent` field.
 * Resolves parent within the child's own namespace prefix.
 * @param {any[]} items - work items with `slug` and `parent`
 * @param {(item: any) => string} keyOf - extract the unique key
 * @returns {Array} tree nodes
 */
function buildWorkTree(items, keyOf) {
  var index = {};
  var keys = [];
  items.forEach(function (it) {
    var k = keyOf(it);
    if (!index[k]) {
      index[k] = { name: it.title || k, path: k, item: it, children: [] };
      keys.push(k);
    }
  });

  var roots = [];
  var attached = {};

  keys.forEach(function (key) {
    var node = index[key];
    var item = node.item;
    if (!item.parent || !item.parent.trim()) {
      roots.push(node);
      attached[key] = true;
      return;
    }

    var parentRef = item.parent.trim();
    var parentKey;

    // Resolve parent within the child's namespace prefix: for a qualified key
    // "sub/proj/<slug>" the namespace is everything before the last "/".
    var slashIdx = key.lastIndexOf("/");
    if (slashIdx !== -1) {
      var prefix = key.substring(0, slashIdx + 1);
      parentKey = prefix + parentRef;
      if (!index[parentKey]) {
        parentKey = parentRef;
      }
    } else {
      parentKey = parentRef;
    }

    if (index[parentKey] && parentKey !== key) {
      index[parentKey].children.push(node);
      attached[key] = true;
    } else {
      if (!attached[key]) {
        roots.push(node);
        attached[key] = true;
      }
    }
  });

  return roots;
}

// ── Prune tree ────────────────────────────────────────────────

/**
 * Prune a tree to nodes whose item matches `predicate`, keeping ancestors.
 * @param {Array} nodes - root-level tree nodes
 * @param {(item: any|null) => boolean} predicate - true = keep the item
 * @returns {{ nodes: Array, forceExpand: Set }}
 */
function pruneTree(nodes, predicate) {
  var forceExpand = new Set();

  function pruneOne(node) {
    if (node.children && node.children.length > 0) {
      var kept = node.children.map(pruneOne).filter(Boolean);
      node.children = kept;
      if (kept.length > 0) {
        forceExpand.add(node.path);
        return node;
      }
    }
    if (node.item && predicate(node.item)) {
      return node;
    }
    return null;
  }

  var kept = nodes.map(pruneOne).filter(Boolean);
  return { nodes: kept, forceExpand: forceExpand };
}

// ── Ancestors ─────────────────────────────────────────────────

/**
 * Return ancestor path keys for a given key.
 * For path keys ("a/b/c"): ["a", "a/b"].
 * For work keys: the chain of parent keys.
 * @param {string} key - the item key
 * @param {string} mode - "path" or "work"
 * @param {Array} [items] - for work mode, the full item list
 * @returns {Array}
 */
function ancestorsOf(key, mode, items) {
  if (mode === "work" && items) {
    var found = items.find(function (it) { return it.slug === key; });
    if (!found || !found.parent) return [];
    var chain = [];
    var visited = {};
    var cursor = key;
    while (cursor) {
      visited[cursor] = true;
      var item = items.find(function (it) { return it.slug === cursor; });
      if (!item || !item.parent) break;
      var parentRef = item.parent.trim();
      var parentKey;
      var slashIdx = cursor.lastIndexOf("/");
      if (slashIdx !== -1) {
        var prefix = cursor.substring(0, slashIdx + 1);
        parentKey = prefix + parentRef;
        if (!items.some(function (it) { return it.slug === parentKey; })) {
          parentKey = parentRef;
        }
      } else {
        parentKey = parentRef;
      }
      if (visited[parentKey]) break;
      chain.unshift(parentKey);
      cursor = parentKey;
    }
    return chain;
  }

  // Path mode
  var parts = key.split("/");
  var result = [];
  for (var i = 1; i < parts.length; i++) {
    result.push(parts.slice(0, i).join("/"));
  }
  return result;
}

// ── Effective expansion merge ─────────────────────────────────

/**
 * Merge user-expand state with force-expand paths from a search/prune.
 * @param {Set} expanded - current user-expand set
 * @param {Set} forceExpand - paths that must be expanded
 * @returns {Set}
 */
function mergeExpansion(expanded, forceExpand) {
  var merged = new Set(expanded);
  forceExpand.forEach(function (p) { merged.add(p); });
  return merged;
}

// ── Browser global export (for <script> tag loading) ──────────

if (typeof window !== "undefined") {
  window.TCWTree = {
    buildPathTree: buildPathTree,
    buildWorkTree: buildWorkTree,
    pruneTree: pruneTree,
    ancestorsOf: ancestorsOf,
    mergeExpansion: mergeExpansion,
  };
}

// ── ESM export (for Node.js testing) ──────────────────────────

export { buildPathTree, buildWorkTree, pruneTree, ancestorsOf, mergeExpansion };

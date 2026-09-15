# Spec — Subproject-qualified slugs for descendant work items

## Capability changes

No **new** capability is declared. The user-facing delta is captured as changes to
existing capabilities (back-pointers recorded in `capabilities.yaml`); the ledger
flip at completion is body/scope edits, not status flips (all stay `Supported`):

- **`cli/host-multiple-projects-in-one-repo#host-multiple-projects-in-one-repo`** —
  extend the body: from an ancestor node you can now address a descendant node's
  work item by a **subproject-qualified slug** (`sub/proj/<slug>`) with any work
  command, equivalent to `cd`-ing into that node first.
- **`work#view-the-board`** — `tcw work list --include-descendants` now prints
  descendant items with their qualifier prefix so each printed slug is a usable
  address.
- **`web#browse-tcw-content-in-a-local-web-app`** — `tcw serve --include-descendants`
  aggregates descendant boards (qualified slugs) alongside the anchor's.
- **`web/editing#edit-tcw-content-in-a-local-web-app`** — in that mode the web app
  can open/edit descendant items addressed by qualified slug.

Rejected alternative: a dedicated `#address-a-descendant-item-by-a-qualified-slug`
capability. Prior art (the `--include-descendants` feature) recorded a board change
without a new capability; qualified addressing reads as an extension of the
existing multi-project story, so a body edit is the honest, minimal record. Easy to
promote to its own capability at completion if preferred.

`tcw capabilities check` is clean at baseline; contradiction search
(`descendant`/`qualified`/`slug`/`subproject`) surfaced no conflicting entry.

## Problem

`tcw work list --include-descendants` is the only command that aggregates items
across descendant nodes. It groups boards under a `# ./sub/proj` header, but each
item's printed slug is the **bare** node-local slug (e.g. `2026-07-04-foo`). That
slug is not a usable address from the anchor: `tcw work show 2026-07-04-foo` run at
the anchor searches only the anchor node and reports "no such work item". The
reader has to notice the header, `cd` into the subproject, and retype the slug.

We want the aggregated output to print an address the reader can paste back into
**any** work command, and we want `tcw serve` to offer the same descendant view.

## Goals

- In descendant-aggregating output, prefix each descendant item's slug with its
  node-relative path (`sub/proj/<slug>`), so the printed slug is a valid address.
- Make every work command that accepts a slug (`show`, `path`, `start`, `edit`,
  `complete`, `drop`) resolve a qualified slug to the correct descendant node and
  operate there, while a bare slug keeps resolving against the anchor node only.
- Add opt-in `tcw serve --include-descendants`: aggregate descendant boards with
  qualified slugs and resolve qualified slugs across the `/api/work/*` routes.
- Preserve the prime directive: no change to the abstract `WorkStore` /
  `WorkItem`; resolution is an FS-adapter-local helper.

## Non-goals

- Descendant aggregation for taxonomy or capabilities (neither aggregates today).
- Cross-node blocking relations. When editing a descendant item, `--blocked-by` /
  `--blocks` refs are interpreted **within the resolved node**, matching the
  `cd`-into-the-node mental model.
- Auto-searching descendants for a bare slug (kept out for backward compat +
  ambiguity avoidance).
- Creating items in a descendant from the anchor (`tcw work new` / serve POST stay
  anchor-local). Addressing existing items is the ask.

## Current-state findings

- **Only work aggregates descendants.** `include_descendants` appears solely in
  `tcw/work/cli.py`. `descendant_nodes(root)` (`tcw/store/fs.py:149`) returns all
  sentinel-bearing `docs/work/` nodes at any depth (transitive, path-sorted,
  skips `.git`/`.worktrees`/symlinks).
- **List rendering.** `_list` (`tcw/work/cli.py:233`) iterates `[node,
  *descendant_nodes(node)]`, prints a `# ./<rel>` header per group, and calls
  `_render_board` — which prints `it.slug` bare (`tcw/work/cli.py:222`).
- **Slug resolution is node-local.** `FsWorkStore._find` (`tcw/store/fs.py:1247`)
  globs `state.yaml` under one node and matches on `d.name == slug`; `get`/`path`
  wrap it. `MultipleMatch` fires only on an intra-node collision. Slugs are
  `slugify`'d to `[a-z0-9-]` (`tcw/store/fs.py:313`) — never contain `/`.
- **Federation precedent.** `FsTaxonomyStore.get` (`tcw/store/fs.py:466`) already
  resolves `alias/slug` qualified refs by splitting on `/`. Analogous shape; here
  the qualifier is a node path rather than a config alias.
- **Serve is single-node.** Every `/api/work/*` handler opens
  `FsWorkStore.open(self.server.node_root)` and operates on the raw slug
  (`tcw/serve/__init__.py`). The board route returns `work.board()`.
- **Serve already tolerates `/` in refs.** Taxonomy/capability refs contain `/`;
  the frontend sends them percent-encoded (`encodeURIComponent`,
  `tcw/serve/static/app.js`) and the backend matches `([^/]+)` then `unquote`s
  (`_decode_path_param`). Work slugs use the same `encodeURIComponent` on the
  client and `([^/]+)`+`unquote` on the server — so a percent-encoded qualified
  work slug already **routes and decodes** with no URL-pattern change. Only the
  store-selection step (`open(node_root)` → resolver) must change.
- **Python floor** is `>=3.11`, so `Path.is_relative_to` is available for the
  traversal guard.

## Proposed behavior

### 1. The resolver (FS-adapter-local, shared by CLI + serve)

Add to `tcw/store/fs.py`:

```python
def resolve_qualified_work_ref(anchor: Path, ref: str) -> tuple["FsWorkStore", str] | None:
    """Resolve a (possibly qualified) work ref against `anchor`.

    Bare slug (no '/')      -> (anchor store, slug)                 [unchanged]
    'sub/proj/<slug>'       -> (descendant-node store, <slug>)      [new]
    Returns None if the qualifier is not a real node within `anchor`
    (unknown path, traversal escape, or symlink out of the tree).
    """
```

Resolution rule (unambiguous because a bare slug has no `/`):
- `anchor = anchor.resolve()` **first** — the guard below is lexical, and callers
  may pass an unresolved path (macOS `/tmp` → `/private/tmp`), which would
  otherwise make `is_relative_to` / `relative_to` misfire.
- Strip an optional leading `./`.
- No `/` → `(FsWorkStore.open(anchor), ref)`.
- Else `qualifier, _, bare = ref.rpartition("/")`; empty `bare`/`qualifier` → None
  (so `slug/` and a leading-slash `/slug` both → None).
- `target = (anchor / qualifier).resolve()`.
- **Traversal guard:** reject unless `target == anchor` or `target.is_relative_to(anchor)`.
- **Reject** if the *resolved* target's anchor-relative segments
  (`target.relative_to(anchor).parts`) include `.git` or `.worktrees`
  (`WORKTREES_DIR`). Check the resolved segments, **not** the raw qualifier string,
  so a symlink or `..`-recombination into `.worktrees` (e.g. `sub/../.worktrees/x`
  or an innocently-named symlink pointing there) can't slip past. Rationale: a
  `start --worktree` checkout copies the sentinel, so `anchor/.worktrees/<branch>`
  is otherwise a real node inside the anchor that the board never emits.
- **Node check:** reject unless `target == anchor` or `target` is a real node
  (`(target / SENTINEL).is_file()` and `(target / "docs" / "work").is_dir()`).
- `(FsWorkStore.open(target), bare)`.

This is O(1) (no tree walk) and safe: it validates the resolved target is a
genuine node genuinely inside the anchor, so `..` / absolute-path / symlink
*escapes* fail closed. (An absolute `qualifier` like `/etc` makes `anchor / "/etc"`
== `/etc`, which the `is_relative_to` guard rejects.) One benign asymmetry: an
*in-tree* symlink pointing at a legitimate node is followed and accepted, whereas
`descendant_nodes` skips all symlinked dirs and would never *emit* that address —
so the resolver is a slight superset of the board-emittable set, not a strict
subset. Acceptable (the target is still a real node inside the anchor).

### 2. CLI (`tcw/work/cli.py`)

- `_render_board(st, status, show_all, prefix="")` — prepend `prefix` to each
  emitted slug. Blocker labels and the child-indentation tree are unchanged
  (blockers are node-local bare slugs).
- `_list` — anchor group `prefix=""`; each descendant group
  `prefix=f"{root.relative_to(node)}/"`. The `# ./<rel>` header is unchanged.
- A `_resolve(slug)` helper finds the anchor node exactly as today —
  `find_node("work")` (nearest `tcw-config.yaml`) — then calls
  `resolve_qualified_work_ref(node, slug)`. `show`/`path`/`start`/`edit`/`complete`/
  `drop` use it and operate on the returned `(store, bare)` instead of the anchor
  store + raw slug. Unresolvable qualifier → the existing "no such work item"
  error. **`_drop` must be converted too** — today it routes through
  `_run(lambda st: st.drop(args.slug))`, a different shape from the others, so it's
  the easiest to miss.
- **bare vs qualified discipline:** every store/git/path-building call takes the
  **bare** slug; every user-facing echo prints the **qualified** ref. This is an
  audit, not a find-replace — a blind "replace all with bare" breaks the hints,
  and "leave all as `args.slug`" corrupts state. The full **bare** call-site list
  (verified against `tcw/work/cli.py`):
  - `_show`/`_path`: `st.get(bare)` / `st.path(bare)`.
  - `_start`: `st.start(bare)`; `st.set_field(bare, "worktree", f"{WORKTREES_DIR}/{bare}")`;
    `st.set_field(bare, "branch", f"work/{bare}")`; `add_worktree(node, bare)`; the
    worktree-start commit message (cli.py:301) should also use `bare` — the
    descendant repo shouldn't record the parent's qualifier (cosmetic, in-repo).
  - `_edit`: `st.get(bare)`; both blocker directions —
    `st.add_blocker(bare, ref)` (`--blocked-by`) **and**
    `st.add_blocker(ref, bare)` (`--blocks`, cli.py:327 — the reverse call writes
    the *bare* slug into `ref`'s node-local `blocked_by`; leaving it qualified
    would persist a cross-node qualifier into a node-local field);
    `st.remove_blocker(bare, ref)`; `st.update_work(bare, …)`.
  - `_complete`: `st.get(bare)`; `st.complete(bare, …)`; `merge_worktree(store.node_root, branch)`;
    **`remove_worktree(store.node_root, bare, branch)`** (cli.py:384 — the slug
    builds the `.worktrees/<slug>` teardown path; leaving it qualified silently
    fails to remove the real worktree).
  - `_drop`: `store.drop(bare)`.
  - **qualified** (echo) sites: `_complete_hint(qualified)`, the `started <qualified>`
    line, and every `no such work item: <qualified>` error — so the suggested/echoed
    commands are copy-pasteable from the anchor.
- `edit` blocker refs (`--blocked-by`/`--blocks`/`--unblocked-by`) are resolved
  **within the target store** (node-local bare refs, per non-goals); passing a
  qualified value there simply fails to resolve in that node.
- **CLI resolution is ungated** (unlike serve, below): the CLI is the user's
  trusted local shell and a qualified slug is exactly `cd`-equivalent, so
  `show`/… resolve qualified slugs from anywhere with no flag.

### 3. Serve (`tcw/serve/__init__.py`, `tcw/cli.py`)

- `serve(...)` and `TcwServer` gain `include_descendants: bool` (default False).
- `tcw/cli.py` `p_serve` gains `--include-descendants`; `_cmd_serve` passes it.
- Board route `GET /api/work` — when `include_descendants`, aggregate
  `[anchor, *descendant_nodes(anchor)]` (anchor `.resolve()`d first, mirroring
  `_list`, so `root.relative_to(anchor)` can't raise on a symlinked path),
  qualifying each descendant item's slug (`item.slug = f"{rel}/{item.slug}"`); else
  the current single-node board.
- A handler helper `_resolve_work(slug) -> (FsWorkStore, str) | None`, **gated on
  `self.server.include_descendants`**:
  - flag **off** → return `(FsWorkStore.open(node_root), slug)` unconditionally.
    A bare slug works exactly as today; a `/`-bearing slug fails to match any
    folder name → the existing 404. Serve is byte-for-byte unchanged without the
    flag (no new resolution, no new mutation surface).
  - flag **on** → `resolve_qualified_work_ref(self.server.node_root, slug)`;
    unresolvable → 404.
  Every `/api/work/<slug>…` route (detail, artifacts, sidecars, sidecar-discovery,
  `actions/{start,complete}`, PATCH, DELETE, `artifacts/<name>/open`) uses it in
  place of `FsWorkStore.open(node_root)` + raw slug. Percent-decoding
  (`_decode_path_param`/`unquote`) already happens in the routes **before**
  `_resolve_work`, so the resolver sees a decoded `../…` and the traversal guard
  applies to the real path (an encoded `..%2Fescape%2F<slug>` decodes to
  `../escape/<slug>` → guard → None → 404).
- Taxonomy/capabilities routes and `POST /api/work` (create) stay anchor-local.
- Frontend: **no change required** for correctness — the board renders whatever
  slugs `/api/work` returns and already `encodeURIComponent`s them for detail
  fetches, which the backend resolver then routes. Optional polish (node grouping /
  a subproject label in the list) is deferred unless trivial.

### `tcw serve --include-descendants` default

**Off** by default — parity with `tcw work list` and preserves today's
single-node serve behavior. Both aggregation **and** API resolution are gated on
the flag (see §3): leaving resolution always-on is **not** harmless — it would flip
a qualified-slug request from 404→200 and expose descendant *mutation* without
opt-in, contradicting "serve unchanged without the flag." (CLI resolution, by
contrast, is ungated — trusted local shell, §2.)

## Acceptance criteria

- `tcw work list --include-descendants` from an ancestor prints descendant items as
  `sub/proj/<slug>`; the anchor's own items stay bare.
- Each of `show`, `path`, `start`, `edit`, `complete`, `drop` accepts a
  `sub/proj/<slug>` and acts on that descendant item; `path` prints the descendant
  folder; a nested `a/b/<slug>` resolves through two levels.
- A bare slug still resolves against the anchor only (unchanged); a slug that
  exists only in a descendant is **not** found bare (must be qualified).
- `tcw serve --include-descendants` board includes descendant items with qualified
  slugs; opening/editing one via the web app resolves to the descendant.
- **Without** `--include-descendants`, serve is unchanged: a percent-encoded
  qualified slug on any `/api/work/*` route (read **and** mutate) returns 404 — no
  descendant is read or mutated.
- A traversal qualifier (`../escape/<slug>`, percent-encoded over serve), an
  absolute qualifier (`/etc/...`), and a `.worktrees/<x>/<slug>` / `.git/...`
  qualifier all resolve to None → CLI "no such work item" / serve 404; nothing
  outside the anchor (or inside `.git`/`.worktrees`) is read.
- `drop` via a qualified slug removes the descendant item (the handler that rides a
  different code path is covered).
- `pytest` green; existing `--include-descendants` and single-node serve tests
  unaffected.
- No method added to `WorkStore`/`TaxonomyStore`/`CapabilitiesStore` ABCs; no field
  added to `WorkItem`.

## Risks & dependencies

- **Ambiguity of qualifier vs slug** — eliminated by the invariant that slugs never
  contain `/`; the last `/`-segment is always the bare slug. Guard: keep this
  reasoning in a comment so a future slug-charset change re-examines it.
- **Cross-node mutation from a parent session** — intentional (the `cd`-equivalence
  argument); a worktree `complete`/`start --worktree` still merges/tears down in the
  *resolved* node's repo because the resolved store's `node_root` is that
  descendant. Worth a test that uses a real sub-repo topology. Nuance: a descendant
  that is a *sentinel-only plain subfolder of one repo* (which `descendant_nodes`
  deliberately allows) has no repo of its own, so `git -C <subfolder>` operates on
  the enclosing repo and the worktree lands under the subfolder — acknowledge this
  case; worktree flows target descendants that are their own repos.
- **`blocked-by:` labels stay bare on qualified list rows** — a descendant row
  prints `sub/proj/<slug> | … | blocked-by: <other>` where `<other>` is a
  node-local bare ref. Intentional (blockers are node-local), but a mild UX trap;
  the README/skill note (below) states that `blocked-by:` refs are always
  interpreted within the resolved node.
- **Serve untrusted input** — mitigated by the traversal + real-node guard in the
  single resolver both surfaces share.
- **`descendant_nodes` cost** — unchanged; the resolver deliberately avoids calling
  it (O(1) target check) while the board aggregation already pays for it as today.

## Related work items

- `2026-07-01-aggregate-descendant-node-boards-in-work-list-include-descendants`
  (completed) — introduced `--include-descendants`; this builds directly on it.
- `2026-06-19-cross-node-recursion-work-spec-2` (completed) — established the
  cross-node layer and the "cross-node writes = inbox only" boundary this feature
  deliberately does not cross (qualified addressing is direct user action, not the
  delegate/escalate request channel).

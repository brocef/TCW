# Plan — Subproject-qualified slugs for descendant work items

Ordered phases. Phase 1 is the foundation both surfaces share; Phases 2 (CLI) and
3 (serve) are independent of each other and can run in parallel once Phase 1
lands; Phase 4 (docs) follows.

## Phase 1 — The shared resolver (foundation)

**Touch:** `tcw/store/fs.py`, `tests/test_store_nodes.py` (or a new
`tests/test_qualified_ref.py`).

1. Add `resolve_qualified_work_ref(anchor: Path, ref: str) -> tuple[FsWorkStore, str] | None`
   near `descendant_nodes` / the other node helpers. Logic **exactly per spec §1,
   in this order** (do not reorder — the guards depend on it):
   `anchor = anchor.resolve()` first; strip leading `./`; bare (no `/`) →
   `(open(anchor), ref)`; else `qualifier, _, bare = ref.rpartition("/")`, with
   empty `bare`/`qualifier` → None; `target = (anchor / qualifier).resolve()`;
   **traversal guard** — reject unless `target == anchor` or
   `target.is_relative_to(anchor)`; **then** reject if
   `target.relative_to(anchor).parts` intersects `{".git", WORKTREES_DIR}` — the
   check is on the **resolved** target's segments, **not** the raw qualifier string
   (a raw-string check misses an innocently-named in-tree symlink into
   `.worktrees`; and `target==anchor` yields `relative_to` == `Path('.')` with
   `.parts == ()`, so it neither raises nor false-matches); **then** node check —
   reject unless `target == anchor` or `target` is a real node (`SENTINEL` +
   `docs/work/`); return `(open(target), bare)`. Comment the "slugs never contain
   `/`" invariant.
2. Unit tests: bare → anchor; `sub/<slug>` → descendant; nested `a/b/<slug>`;
   `./sub/<slug>` (leading `./`); unknown qualifier → None; plain-subdir
   (non-node) qualifier → None; **traversal** `../escape/<slug>` and
   `sub/../../etc/passwd` (post-resolve escape) → None;
   **absolute** `/etc/passwd` → None; **malformed** `/`, `/slug`, and `slug/`
   (empty qualifier/bare) → None; **`.worktrees/<x>/<slug>`** and **`.git/...`** →
   None. Critically, to prove the guard is on the *resolved* segments (a raw-string
   check would pass all of the above), add **two distinct cases a raw check gets
   wrong**: (a) an in-tree **symlink** dir with an innocent name (`link` →
   `anchor/.worktrees/x`, whose copied sentinel + `docs/work/` make it a real node)
   → `link/<slug>` must return None; (b) a `..`-recombination (`sub/../.git/<slug>`)
   → None.
   **render→resolve round-trip** — take `f"{rel}/{item.slug}"` as produced by
   `_list`/serve and assert the resolver returns `(descendant store, item.slug)`
   (locks prefix/trailing-slash consistency across the three sites).

## Phase 2 — CLI (depends on Phase 1)

**Touch:** `tcw/work/cli.py`, `tests/test_work.py`.

1. `_render_board(st, status, show_all, prefix="")`: prepend `prefix` to the
   printed slug in `emit`. Leave blocker labels and child indentation bare.
2. `_list`: pass `prefix=""` for the anchor group and, for each descendant group,
   `prefix=f"{descendant.relative_to(anchor)}/"`. **Note the variable roles** (they
   match the existing loop at `cli.py:240-244`): `node`/`anchor` is the current
   node, `root`/`descendant` is the iterated descendant, so `root.relative_to(node)`
   is the descendant-relative-to-anchor path (descendant *is* under anchor — not
   inverted). It equals the existing `rel` used for the `# ./<rel>` header, which is
   unchanged.
3. Add a `_resolve(slug)` helper: `find_node(NAME)` (same node identification as
   today — nearest `tcw-config.yaml`) → `resolve_qualified_work_ref(node, slug)`.
   It must let each caller distinguish two failures: **(a) no work node here**
   (`find_node` → None → the existing `_store()` "no tcw work node here" message +
   exit 1) vs **(b) node exists, qualifier unresolvable** (resolver → None → the
   per-command `no such work item: <qualified-slug>` echo). Concrete mechanism to
   avoid collapsing them: `_resolve` prints the right message itself — the
   `_store()` no-node message for (a), or `no such work item: <slug>` (with the
   original qualified `slug`) for (b) — and returns `None`; each caller just
   `return 1` on `None`. (Both surface as `None`, so the *helper* must own the
   message choice, not the caller.) Convert `_show`,
   `_path`, `_start`, `_edit`, `_complete`, `_drop` to resolve first, then use the
   returned `(store, bare)`. **`_drop` today routes through
   `_run(lambda st: st.drop(...))` (which re-opens the anchor store) — stop using
   `_run` for it; resolve then `store.drop(bare)` like the others.** Also: `_path`
   today does **not** wrap `st.path` in a `MultipleMatch` try (pre-existing — an
   ambiguous bare slug tracebacks); the resolver doesn't change that (it opens the
   store but doesn't call `path`, so `MultipleMatch` still fires inside `path`).
   While converting `_path`, wrap it consistently with `_show`/`_complete`.
4. **bare vs qualified (spec §2) — this is an audit of every call site, not a
   find-replace.** All store/git/path-building calls take `bare`; all user-facing
   echoes print the qualified ref. Beyond the obvious `_start` sites
   (`st.set_field(bare, "worktree", f"{WORKTREES_DIR}/{bare}")`,
   `…, "branch", f"work/{bare}"`, `add_worktree(node, bare)`, `st.start(bare)`),
   the two easy-to-miss ones the spec now enumerates: **`_edit`'s reverse blocker
   `st.add_blocker(ref, bare)`** (cli.py:327 — must be bare, else a qualified ref is
   persisted into a node-local `blocked_by`) and **`_complete`'s
   `remove_worktree(store.node_root, bare, branch)`** (cli.py:384 — the slug builds
   the `.worktrees/<slug>` teardown path; qualified → silent no-op). Echoes
   (`_complete_hint(qualified)`, `started <qualified>`) print qualified.
5. Tests:
   - `list --include-descendants` prints `Project-A/2026-01-01-a-feature` and keeps
     the anchor item bare (extend the existing group-by-node test).
   - `show`/`path` on a qualified slug hit the descendant; `path` prints the
     descendant folder.
   - **Two-level + anchor-is-not-root:** `show`/`path` on `a/b/<slug>` resolves
     through two levels; and run from a *mid-tree* node (e.g. invoked inside
     `sub/proj/`) a qualified `grandchild/<slug>` resolves relative to *that*
     node — the anchor is wherever the command runs, not the repo root.
   - `start` → `complete --resolution done --confirm` a descendant item via
     qualified slug (round-trips the state machine in the child node); assert
     `_complete_hint` prints the **qualified** slug.
   - **`start --worktree` → `complete` on a descendant via qualified slug** (real
     sub-repo topology): assert the worktree is created under the *descendant's*
     `.worktrees/<bare>` and that `complete` actually removes it (guards the
     `remove_worktree` bare-slug bug). Note the sentinel-only-plain-subfolder
     caveat from spec risks when choosing the fixture topology.
   - `drop` a descendant item via qualified slug (the different-code-path handler).
   - `edit --blocked-by` **and** `--blocks` (reverse) on a qualified slug: assert a
     blocker is added **and that the stored blocker ref is bare** (read back via
     `show`/state — catches a qualified ref leaking into node-local `blocked_by`).
   - A qualified ref whose bare part is ambiguous inside the descendant still
     surfaces `MultipleMatch`.
   - Backward compat: bare slug for a descendant-only item is **not** found from
     the anchor; anchor bare slug unchanged.

## Phase 3 — Serve (depends on Phase 1; parallel with Phase 2)

**Touch:** `tcw/serve/__init__.py`, `tcw/cli.py`, `tests/test_store_editor.py`
(serve tests live here per the existing `descendant`-referencing test file).

1. `tcw/cli.py`: add `--include-descendants` to `p_serve`; thread through
   `_cmd_serve` → `serve(...)`.
2. `serve(...)` + `TcwServer.__init__`: accept and store `include_descendants`.
3. `GET /api/work`: when `self.server.include_descendants`, aggregate
   `[anchor, *descendant_nodes(anchor)]` boards (anchor `.resolve()`d first, like
   `_list`, so `root.relative_to(anchor)` can't raise on a symlinked path),
   qualifying each descendant item's `slug` with `f"{rel}/"`; else unchanged
   single-node board.
4. Add `TcwHandler._resolve_work(slug) -> (FsWorkStore, str) | None`, **gated on
   `self.server.include_descendants`**: off → `(FsWorkStore.open(node_root), slug)`
   unconditionally (bare works, `/`-slug 404s — serve unchanged without the flag);
   on → the shared resolver against `self.server.node_root`. Route every
   `/api/work/<slug>…` handler (GET detail, GET/PUT artifacts, GET/PUT sidecars, GET
   sidecars discovery, POST `actions/{start,complete}`, PATCH, DELETE, POST `…/open`)
   through it in place of the anchor `work` store + raw slug. Unresolvable → 404
   (reuse the existing "no such work item" 404 path).
5. Leave taxonomy/capabilities routes and `POST /api/work` (create) anchor-local.
6. Frontend: no functional change (qualified slugs already `encodeURIComponent`
   correctly). Only touch `app.js`/`style.css` if a node label is trivial; else
   defer to a follow-up (note it in `outcome.md`).
7. Tests:
   - `--include-descendants` board response includes a descendant item with a
     qualified slug; default (no flag) board is single-node.
   - `GET /api/work/<percent-encoded-qualified-slug>` returns the descendant detail
     (flag on).
   - A mutating action (e.g. `start`) on a descendant via qualified slug works
     (flag on).
   - **Flag off:** the same percent-encoded qualified slug on a GET **and** on a
     mutating route (PATCH/DELETE/action) → 404; no descendant read/mutated.
   - A percent-encoded traversal slug (`..%2Fescape%2F<slug>`) → 404 (flag on);
     add one serve-level assertion for an absolute (`%2Fetc%2F…`) and a
     `.worktrees` qualifier → 404 too, so the acceptance rows are covered at the
     serve layer and not only in the resolver unit tests.

## Phase 4 — Docs sync & capability record (after Phases 2–3)

Triggers expected to fire (per CLAUDE.md Documentation Sync):

- **`README.md`** [Public-API]:
  - `tcw work list --include-descendants` section (~L383): note descendant slugs
    print qualified and are usable addresses.
  - Serve usage: document `tcw serve --include-descendants`.
  - "Multiple projects in one repo" section (~L176–194): add that an ancestor can
    address a descendant item by `sub/proj/<slug>` with any work command; refine the
    existing cross-node Note accordingly. State that `blocked-by:` refs are always
    node-local (interpreted within the resolved node), so a blocker shown on a
    qualified list row is a bare ref in that descendant.
- **`skills/tcw-work/SKILL.md`** [Skill-Driven-Component]: update the `list`
  quick-ref line (qualified slugs) and add a one-liner that work slug-commands accept
  `sub/proj/<slug>` when run from an ancestor; mention it in the Resume section if it
  aids cross-node resume.
- **`docs/changelogs/upcoming.md`** [Any-Code-Change]: Added (`tcw serve
  --include-descendants`; qualified-slug resolution across work commands) / Changed
  (`work list --include-descendants` slug format), with the commit-hash range.
- **`docs/release-notes/upcoming.md`** [Public-API]: plain-language note that
  subproject boards now show addressable slugs and any command accepts them.
- Invoke the `skill-cefailures:documentation-sync` skill before reporting complete
  (per CLAUDE.md).

## Completion-time steps (NOT part of this planning task)

- `tcw work start <slug>` as the first implementation commit (with committed
  spec/plan) before any code edit.
- Capability ledger flip (tcw-capabilities): edit the
  `cli/host-multiple-projects-in-one-repo` body to describe qualified addressing;
  confirm `work#view-the-board` / `web#*` scope text; `tcw capabilities check`.
- Version: **minor** bump offered (user-facing feature addition) via
  `scripts/cut_version.py`, with `upcoming.md` entries written first.

## Verification commands

- `pytest -q` (full suite; targeted: `pytest tests/test_work.py
  tests/test_store_editor.py tests/test_store_nodes.py -q`).
- Manual smoke: in a temp repo with a subproject node, `tcw work list
  --include-descendants`, then `tcw work show sub/proj/<slug>` and `tcw work path
  sub/proj/<slug>`; `tcw serve --include-descendants` and open a descendant item.
- `python -m tcw --version` and `tests/test_plugin_manifests.py` after any version
  cut (version-string lockstep guard).

## Parallelization summary

- Phase 1 must complete first (both surfaces import the resolver).
- Phases 2 and 3 are independent → parallelizable.
- Phase 4 after 2 and 3 (docs describe the shipped surface).

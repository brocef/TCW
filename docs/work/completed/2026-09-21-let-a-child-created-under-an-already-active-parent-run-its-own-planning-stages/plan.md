# Plan — Let a child created under an already-active parent run its own planning stages

## Overview

The spec settles the layout: a new child is an ordinary top-level item whose
`state.yaml` records `parent: <slug>`, and a legacy child (nested in its parent's
folder, no `parent:` key) keeps following its parent. This plan builds it in the
order that keeps the suite green at every commit.

1. Read side first. Tasks 1–2 teach the store to read a `parent:` field and to
   answer "which descendants are open with their own status?". Nothing any user
   does changes yet.
2. The rules next. Tasks 3–5 wire that answer into `complete`, `drop`, epic
   readiness and the worktree merge. Every child `create_work` makes is still a
   nested legacy child at this point, and legacy children never block, so existing
   tests stay green. The new tests build field-style children by hand.
3. The switch. Task 6 changes `create_work` to write the new layout. This is the
   first task that changes default behavior, and it is isolated from the rest.
4. The legacy edges. Tasks 7–9 handle a legacy child's own transitions, claim
   recovery, re-parenting and deletion.
5. Tests of the other surfaces (Task 10), then the documentation block (Task 11).

**Where the work happens.** Implementation happens in `.worktrees/<slug>`, which
`tcw work start <slug> --worktree` creates. Several sessions share this checkout,
so use a private virtual environment rather than re-pointing the shared editable
install:

```sh
python -m venv --system-site-packages <scratch>/venv
<scratch>/venv/bin/pip install -e <worktree> --no-deps
<scratch>/venv/bin/pip install --ignore-installed pytest
```

Run everything with `PATH="<scratch>/venv/bin:$PATH"` and the current directory
set to the worktree. Run tests with bare `pytest`, as CI does. Before finishing,
restore the shared install with `pip install -e /Users/brian/Projects/TCW`.

This item edits `tcw/`, so the project guide's exception applies: once code
editing starts, drive the work system by editing files directly and say so. Do
not run `tcw work` transition verbs against the tree under change.

**Names this plan introduces** (all in `tcw/store/base.py` unless stated; the
spec left the naming to the plan):

- `WorkStore.parent_children(slug) -> list[WorkItem]` — the items whose `parent`
  is `slug`. It mirrors `initiative_children` (`tcw/store/base.py:3545-3551`) and
  is built from one `query()`.
- `WorkStore.independent_descendants(slug) -> list[WorkItem]` — every item in
  the subtree below `slug` that has its own status, open or resolved. It walks
  the whole subtree from a single `query()` snapshot, keeps a set of visited
  slugs so a hand-made cycle cannot loop, and walks *through* children that
  follow their parent without returning them. `drop` uses this directly.
- `WorkStore.open_descendants(slug) -> list[str]` — the slugs from
  `independent_descendants` whose status is not in `RESOLVED_STATUSES`.
  `complete`, epic readiness and the CLI's pre-merge check use this.
- `WorkStore._follows_parent(item) -> bool` — default `False`. `FsWorkStore`
  overrides it: `True` when the item's folder is nested inside another item's
  folder and its `state.yaml` has no `parent` key.
- `WorkStore._require_live_parent(parent_slug, *, moving: str | None = None)` —
  raises `ValueError` when the named parent is missing, is `completed` or
  `discarded`, or has a resolved ancestor. With `moving` set, it also raises when
  walking up from the parent reaches `moving` (a cycle).
- `FsWorkStore._in_flight_items() -> list[WorkItem]` (adapter-private) — every
  item inside `.claiming/`: each claimed folder **and every item nested inside
  it**. They are read with the same `_read_item`, and their status is reported
  as `active`, because that is where a claim lands. A nested item's parent comes
  from its field, else from its enclosing folder inside the claim. The
  filesystem override of `_relation_snapshot` (Task 2) adds these to the snapshot
  before walking, so a claimed item and its nested descendants stay visible.
  `_follows_parent` works by path, so it recognises an item nested inside a claim
  folder with no field as a legacy follower too.
- `FsWorkStore._tracked_source(slug) -> Path | None` (adapter-private) — the
  folder the git index holds for `slug` under `backlog/`. It runs
  `git -C <store_git_root> ls-files -- <store-relative backlog path>` and
  matches `…/<slug>/state.yaml`, using store-relative paths the way
  `_committed_item_path` does. It raises `ValueError` on two or more matches.
  Claim recovery and the CLI's `start --worktree` commit use it to find an
  interrupted claim's original source.

**Riskiest tasks:** 6 (it changes what every `--parent` does), 7 (the claim
path, shared with other work), and 9 (deleting folders). Each comes after its
supporting code and its tests exist, and each is its own commit.

**Blockers:** none. The related items
(`2026-09-16-stop-an-item-reaching-implement-…`,
`2026-09-15-make-start-take-over-recover-an-interrupted-claim-…`,
`2026-09-15-make-the-strict-tracker-gate-refuse-unfollowable-moves-and-allow-child-items`)
neither block this one nor are blocked by it. Risk 5 of the spec covers the
shared claim code: whichever item lands second reconciles.

## Tasks

### Task 1 — Read a `parent:` field, and report bad pointers

**Modify**

- `tcw/store/fs.py`:
  - **`_parent_slug` (`:4115-4124`).** Take the state already loaded by
    `_read_item`, and return `state.get("parent")` when it is a non-empty string.
    Fall back to the nesting walk only when the key is absent. Pass the loaded
    state in so the file is not read twice.
  - **`check()` (`:5826`).** For each item with a `parent:` field, report
    `"<slug>: parent '<p>' names no work item or tombstone in this store"` when
    neither `get(p)` nor `tombstone(p)` answers. When the item's folder is nested
    and the field names a different item than the enclosing folder, report
    `"<slug>: parent field '<p>' disagrees with the folder it sits in ('<q>')"`.

**Tests**

- `tests/test_work.py`. With the helper `_legacy_child(root, status, parent,
  child)`, which writes `docs/work/<status>/<parent>/<child>/state.yaml` by hand,
  check that the child reads with `parent == <parent>` and `status == <status>`
  (criterion 14, read half). A top-level folder with `parent: p` in its
  `state.yaml` reads with `parent == "p"`.
- `tests/test_validate.py`: one test per message above (criterion 18), and one
  showing a `parent:` naming a tombstoned slug is **not** reported.

### Task 2 — Answer "which descendants are open?", and stop misreporting legacy children

**Modify**

- `tcw/store/base.py`: add `parent_children`, `independent_descendants`,
  `open_descendants` and `_follows_parent` as described in the Overview.
  `independent_descendants` builds its snapshot through a small overridable
  hook, `_relation_snapshot()`, which defaults to `query()`.
- `tcw/store/fs.py`:
  - Override `_follows_parent`: nested folder and no `parent` key. Read the key
    from disk, because `WorkItem.parent` cannot tell a field from nesting.
  - Add `_in_flight_items`. Override `_relation_snapshot` to return `query()`
    plus `_in_flight_items()`. That covers the claim window, including the
    contents nested inside a claimed folder (spec, "Places that still need
    work").
  - **`check()`.** Skip `_status_resolution_problems` for an item where
    `_follows_parent` is true, the status is resolved and the resolution is
    missing. It carries its parent's resolution. This removes the false report
    from step 6 of the spec's Problem.

**Tests**

- `tests/test_work.py`, built with hand-written folders:
  - `open_descendants` on a parent with a field child in each of `backlog`,
    `active`, `review`, `completed` and `discarded` returns exactly the three
    open ones.
  - A resolved field child with an `active` field grandchild returns the
    grandchild (the subtree half of criterion 7).
  - A legacy nested child is not returned, but a field child of that legacy
    child is (criterion 15).
  - Two items whose `parent:` fields point at each other do not loop.
  - A folder left in `.claiming/<child>-<32 hex>/` whose `state.yaml` has
    `parent: <p>` is returned for `<p>` (the store half of criterion 9).
  - **Nested claim contents.** Set up an interrupted claim of a legacy item:
    `.claiming/<a>-<32 hex>/` has `parent: <p>` and holds a nested legacy child
    `<b>/`, and a top-level field item `<f>` in `active/` has `parent: <b>`.
    Then:
    - `open_descendants(p)` returns `a` and `f`;
    - it does not return `b`, which follows `a`;
    - `independent_descendants(p)` also includes `f` once `f` is completed.

    Without the claim-contents scan, `f` would be unreachable, because its
    parent `b` would be invisible.
  - `independent_descendants` returns a resolved field grandchild beneath a
    legacy child (the case `drop` needs in Task 3).
- `tests/test_validate.py`: a legacy child under a completed parent with no
  resolution produces no problem (criterion 14, validate half). A *top-level*
  completed item with no resolution is still reported, so the exemption is
  narrow.

### Task 3 — Refuse resolving or dropping over open descendants

**Modify**

- `tcw/store/base.py`:
  - **`complete` (`:3790`).** After the legality check (`:3801-3803`) and
    **before** the `if not force:` block (`:3804`), call
    `open_descendants(slug)`. If it is non-empty, raise
    `ValueError(f"Cannot complete {slug}; these items beneath it are still open:
    {', '.join(...)}. Complete or discard them first.")`. The check applies to
    both resolutions, and `--force` does not reach it.
  - **`drop` (`:3861`).** Before `_delete`, refuse when
    `independent_descendants(slug)` is non-empty, open or resolved, naming each
    one. This covers:
    - a direct field child;
    - a resolved field grandchild beneath a legacy child;
    - an in-flight claim.

    Legacy nested children with no independent descendants are still deleted
    with the folder.

**Tests**

- `tests/test_work.py`, with field children written by hand, because
  `create_work` still nests until Task 6:
  - Criterion 6: `complete` with `done`, with `wontfix`, and each with
    `force=True`, raises while a child is in `backlog`, `active` or `review`. The
    message names the child, and the parent's folder has not moved. After the
    child completes, the parent completes.
  - Criterion 7: an `active` grandchild under a resolved child blocks.
  - Criterion 8: `drop` raises with a `backlog` field child, with a
    `completed` field child, and with a `completed` field grandchild beneath a
    legacy child. `drop` still succeeds on a parent whose only descendants are
    legacy children, written with `_legacy_child`. (The existing
    `test_drop_parent_removes_children` at `:1588` still passes in this task,
    because `create` still nests; Task 6 rewrites it.)
  - Criterion 9: with a claim folder left in `.claiming/`, both `complete` and
    `drop` of the parent raise.
  - Criterion 14, completion half: completing a parent with a legacy child
    succeeds and carries the child into `completed/`.
- `tests/test_work.py`, through the CLI: `main(["work", "complete", p,
  "--resolution", "done", "--confirm", "--force"])` exits 1 and prints the
  child's slug.

### Task 4 — Make epic readiness agree with completion

**Modify**

- `tcw/store/base.py`, `epic_completable` (`:3638-3649`): also return `False`
  when `open_descendants(item.slug)` is non-empty. Leave
  `epic_children_all_resolved` alone: it answers the structural "may close from
  backlog" question, and `complete` now refuses that route anyway through
  Task 3's check, which runs before the `from_backlog_epic` bypass at `:3857`.
  Confirm that the "Ready to close" instruction in the rollup reads
  `epic_completable` (`tcw/work/recursion.py`) and not the structural check.

**Tests**

- `tests/test_epic_completable.py`: an epic whose initiative children are all
  resolved but which has an open field child is not completable. Once the child
  resolves, it is.
- `tests/test_recursion.py` (criterion 12): `reconcile --complete-when-ready` on
  that epic neither completes it nor raises, and its rollup does not say "Ready
  to close". After the child resolves, a second reconcile completes it.

### Task 5 — Refuse before a worktree merge, not after

**Modify**

- `tcw/work/cli.py`, `_complete` (`:3503`). Immediately after the strict-tracker
  refusal (`:3638-3640`) and before `merge_worktree` (`:3642`), check for open
  descendants and refuse. Run the check for every resolution, not only when
  shipping.
  - **Which copy to check.** A field child created in the parent's worktree is
    on the work branch and invisible to the primary checkout's store until the
    merge. `_complete` already reads the branch's copy for its other pre-merge
    judgments (`branch_store` from `_branch_copy`, `:3467` and `:3545-3549`).
    Check the union of `st.open_descendants(bare)` and, when `branch_store` is
    not `None`, `branch_store.open_descendants(bare)`.
  - If the union is non-empty, print the store's message and return 1, leaving
    the branch, the worktree and the item untouched.
  - The store's own check in `complete` still runs after the merge, for every
    other caller.
  - **Stated limit.** When `_branch_copy` falls back to `(None, item)` because
    the worktree cannot be read, only the primary copy is checked. A child that
    exists only on an unreadable branch is then found by the store's check after
    the merge, not before it. Record this limit in `outcome.md`.

**Tests**

- `tests/test_worktree_completion.py` (criterion 11): start a parent with
  `--worktree`, commit something on its branch, give it an open field child, and
  run `tcw work complete <parent> --resolution done --confirm`. Assert: exit 1,
  the parent is still `active`, `git branch --list work/<parent>` still exists,
  the worktree directory still exists, and trunk's `HEAD` has not changed (no
  merge commit).
- The same assertions when the open field child was created **inside the
  worktree** and committed only on `work/<parent>`, so the primary checkout's
  store cannot see it.

### Task 6 — Create every new child in `backlog` with a `parent:` field (risky)

This is the behavior switch. Everything that protects it already exists.

**Modify**

- `tcw/store/fs.py`, `create_work`:
  - **Parent validation (`:6420-6425`).** Replace the bare existence check with
    `self._require_live_parent(parent)` (criterion 3). Keep the error for a
    missing parent, `no such parent work item: <p>`, word for word, because
    `test_create_child_unknown_parent_errors` and
    `test_cli_new_unknown_parent_errors` assert on it.
  - **Directory (`:6444-6447`).** Always `self.root / "backlog" / slug`, and add
    `state["parent"] = parent` next to where `initiative` is added.
- `tcw/store/fs.py`, `update_work` (`:6560-6578`, `:6637-6642`). This moves here
  from Task 8, because once children stop nesting, the folder-based re-parent
  code breaks existing tests.
  - **Setting a parent** writes `state["parent"] = parent`, not a folder move.
    Before writing, check that the parent exists and walk up from it through the
    relation (field, else nesting). If the walk reaches the item itself, raise
    `ValueError("cannot re-parent an item under itself or a descendant")`. Keep
    that exact text, because
    `tests/test_store_editor.py:1431-1439` matches `"itself or a descendant"`.
    This replaces the folder-ancestry test at `:6573`, which cannot see a field
    child.
  - **Clearing a parent** (`None` or `""`) runs `state.pop("parent", None)`. A
    legacy nested child also moves to the top-level folder of its status, as
    today.
  - Keep `_mv` only for that legacy move, and for setting a parent on a legacy
    nested child: move it to the top level first, then write the field. Status
    never changes.
- `tcw/store/base.py`: add `_require_live_parent`. Update the `create` docstring
  (`:3033-3034`) to say that the child starts in `backlog` and the relation never
  sets a status.

**Tests** (replacing the old pins — criterion 22)

- `tests/test_work.py`:
  - Rewrite `test_create_child_nests_and_derives_parent` (`:1533`) as
    `test_create_child_records_parent_and_starts_in_backlog`. The child is at
    `docs/work/backlog/<child>/`, its `state.yaml` has `parent: <p>`, and it
    reads `status == "backlog"`, `parent == p`. Parametrize over a parent in
    `backlog`, `active` and `review` (criteria 1 and 2).
  - Rewrite `test_parent_transition_carries_children` (`:1562`) as
    `test_parent_start_leaves_child_in_backlog` (criterion 5). Keep the old
    assertion (the child is active and nested after the parent's start) as
    `test_legacy_child_rides_parent_start`, using `_legacy_child`.
  - Rewrite `test_child_transition_denests_to_top_level` (`:1575`) as
    `test_child_keeps_parent_through_its_transitions`. Run `start`, `submit`,
    `rework` and `complete done`, and assert `parent == p` after each
    (criterion 4). The legacy version is Task 7's criterion-16 test.
  - Criterion 3: `create(..., parent=<completed item>)`, and one whose
    grandparent is discarded, raise, and no new folder exists under `backlog/`.
  - `test_cli_new_parent_and_list_nesting` (`:1597`) should pass unchanged, since
    `tcw work list` nests by field. Keep it as the listing check.
  - `test_discovery_is_depth_agnostic` (`:1552`) asserts
    `st.path(c) == backlog/<p>/<c>`. Build its child with `_legacy_child` so it
    keeps testing depth-agnostic discovery. Add one line asserting a `create`d
    child's path is `backlog/<c>`.
  - `test_drop_parent_removes_children` (`:1588`): build the child with
    `_legacy_child`. A `create`d child would now make `drop` refuse (Task 3),
    and that case is already covered there.
- Other files whose tests assume the old layout, each adapted in this task:
  - `tests/test_store_editor.py:1420` `test_update_work_denest`: the child is
    now a field child, so assert the `parent` key is gone from its `state.yaml`
    and it stays in `backlog/`. Add a legacy variant that asserts the move to
    the top level.
  - `tests/test_store_editor.py:1431` `test_update_work_reparent_rejects_self_and_descendant`:
    passes on the new relation walk with its error text unchanged. Confirm that
    it passes for the right reason: the field child case goes through the walk,
    not the old folder check.
  - `tests/test_store_editor.py:301` `test_create_work_rejects_unknown_parent`:
    keep the text `no such parent` in `_require_live_parent`'s missing-parent
    error.
  - `tests/test_environment_hardness.py:353-357` `test_work_parent_child_nesting`
    asserts that the child becomes `active` when the parent starts. Invert it:
    the child stays `backlog` and keeps `parent`.
- `tests/test_stage_verb.py` (criterion 1): after `tcw work new C --parent <active
  parent>`, `tcw work stage gate request <child>` exits 0 (given `intake.md`).
  With the artifacts each gate needs in place, `spec` and `plan` also exit 0.
- Run the **whole** suite with bare `pytest` at the end of this task. Any other
  test that assumed a nested path for a new child shows up here. Fix each one
  in this task by switching it to a field child or to `_legacy_child`, whichever
  it actually meant.

### Task 7 — A legacy child's own transitions keep its parent (risky)

**Modify**

- `tcw/store/fs.py`:
  - **`_effect_transition_locked` (`:6190`).** After `src = self._find(slug)`, if
    `_follows_parent` is true for the item, add
    `fields["parent"] = self._parent_slug(src)` (from the nesting walk), creating
    `fields` if it is `None`. It is then written in the same move and commit as
    the status change.
  - **`start` main claim (`:4044-4046`).** If `src` is nested and its
    `state.yaml` has no `parent` key, write `parent: <nesting-derived parent>`
    into `src/state.yaml` **before** `os.replace(src, private)`. Then every
    interrupted claim already carries the field. A legacy child whose field
    agrees with its enclosing folder is not reported by Task 1's disagreement
    check, so writing it early is safe even if the claim then loses the race and
    the folder stays where it was. If the write itself fails, nothing has moved.
  - **Staging the source.** The main path already stages the real `src`
    (`git_stage(self.store_git_root, src, dst)`, `:4059`), which is
    `backlog/<p>/<child>` for a legacy child, so it needs no change.
  - **`start` take-over (`:3943-3966`).** The claim's `state.yaml` already holds
    `parent:`, so recovery never needs to derive it. Only staging needs the
    original source: replace the hard-coded `self.root / "backlog" / claimed`
    with `self._tracked_source(claimed)`. Fall back to `backlog/<claimed>` when
    nothing is tracked (a never-committed item, where there is no deletion to
    stage). Refuse with the `ValueError` `_tracked_source` raises on two or more
    matches, and name them.
- `tcw/work/cli.py`, `start --worktree` commit (`:1285-1287`). Capture the
  source before `st.start(...)` as `st.path(bare)`, or, when that is `None`
  (recovering an interrupted claim, whose folder is in `.claiming/`; see
  `:1226`), as `st._tracked_source(bare)`. Build `store_paths` from that source,
  relative to `st.store_git_root`, plus `rel / "active" / bare`, instead of
  `rel / "backlog" / bare`.

**Tests**

- `tests/test_work.py` (criterion 16, first half): with a legacy child in an
  `active` parent, `submit` moves it to `docs/work/review/<child>/` with
  `parent: <p>` in its `state.yaml`, and `get(child).parent == p`. With a legacy
  child in a `backlog` parent, `start(child, owner="x")` puts it at
  `active/<child>/` with the field written, and `git status --porcelain` shows no
  leftover nested path.
- `tests/test_external_work_store.py` (criterion 10), next to
  `test_takeover_recovers_interrupted_private_claim` (`:592`): recovering an
  interrupted claim of a **field** child publishes it to `active/` with
  `parent:` intact. A second case covers an interrupted claim of a **legacy**
  child, made by interrupting the claim after `os.replace(src, private)`:
  - the `state.yaml` in `.claiming/` already has `parent: <p>`;
  - after `--take-over`, the nested source `backlog/<p>/<child>` is staged as a
    deletion.

  A third case covers `_tracked_source` with two tracked folders of the same
  name: it refuses, naming both.
- `tests/test_external_work_store.py`: `tcw work start <legacy child>
  --worktree --take-over --owner x` recovering an interrupted claim commits the
  nested source's removal (the path where `st.path()` is `None`).
- `tests/test_work.py`: a claim of a legacy child that loses the race leaves the
  child where it was, with `parent:` matching its folder, and `tcw validate`
  reports nothing for it.
- `tests/test_external_work_store.py` (criterion 16, worktree half): run
  `start --worktree` on a legacy child with `work.auto-commit-transitions: false`
  and the store in a separate repository. The commit contains the removal of
  `backlog/<p>/<child>` and the addition of `active/<child>`, and
  `git -C <store> status --porcelain` is clean for both paths.
- Re-run `tests/test_external_work_store.py` and `tests/test_non_git_writes.py`
  whole. They hold every existing claim-race test.

### Task 8 — Re-parenting: the live-parent rule and the web route

**Modify**

Task 6 already made re-parenting a field write with the existence and cycle
checks. This task adds the live-parent rule and the web surface.

- `tcw/store/fs.py`, `update_work`. Route the parent checks Task 6 added through
  `_require_live_parent(parent, moving=slug)`. Existence and the cycle walk run
  **for every item, resolved ones included**: a resolved item may not point at a
  missing parent or join a cycle either. The resolved-parent and
  resolved-ancestor refusals apply only when the item being re-parented is open.
  A resolved item may be filed under a resolved parent, because nothing open is
  hidden by that. Keep the Task 6 error texts ("no such parent",
  "itself or a descendant") so existing tests keep matching.

**Tests**

- `tests/test_work.py` (criterion 13, store half):
  - A `backlog` item given an `active` parent stays in `backlog/` with the field
    set.
  - Clearing an `active` child's parent leaves it in `active/` with no key.
  - A parent equal to the item, or to its field grandchild, is refused, both for
    an open item and for a `completed` item.
  - A missing parent is refused for a `completed` item too.
  - For an open item, a parent that is `completed`, or whose parent is
    `discarded`, is refused. For a `completed` item, a `completed` parent is
    accepted.
  - A legacy child re-parented moves to the top level and gains the field.
- `tests/test_serve_write.py` (criterion 13, web half): through the PATCH route
  (`tcw/serve/__init__.py:1161-1164`, fields `{"parent": ...}`), the same backlog
  case keeps its status. The cycle case returns an error status whose body names
  the reason.

### Task 9 — Deleting a resolved parent records its legacy children (risky)

**Modify**

- `tcw/store/fs.py`:
  - **`delete_resolved` (`:5131`).**
    - **Which children to record.** Take the list of legacy children from git,
      not from the folder: `git -C <store_git_root> ls-tree -r --name-only HEAD
      -- <committed>`, where `committed` is the parent's committed path
      (`_committed_item_path`), keeping each `…/<slug>/state.yaml` below the
      parent's own. A rerun after the `rmtree` already happened still finds them,
      because `HEAD` holds the folder until the removal commit lands. After that
      commit there is nothing left to finish. Read each child's resolution from
      `git show HEAD:<path>` where the file has one; otherwise use the parent's
      resolution, since the child followed the parent.
    - **One graveyard write.** Change `_write_tombstone` (`:4793`) to accept a
      list of `(slug, resolution, resolved, location)` records and apply them in
      one read-modify-write, or add a `_write_tombstones` it delegates to. The
      parent and every nested slug are recorded in that single write, all with
      the parent's `location`. The removal commit already names the parent's
      committed path, which contains them.
    - **Resuming.** Extend `_graveyard_dirt_is_only(slug)` (`:4687`) to take a
      set of slugs, and `_require_writable_graveyard(slug, only_own_entry=...)`
      (`:4717`) to pass `{parent} ∪ nested slugs` from git. A resumed removal
      then accepts uncommitted graveyard entries for exactly those items and
      still refuses anyone else's.
  - Resolve `pending_removal` for a nested child the same way, through
    `_committed_item_path`. Needed so a rerun addressed at the parent recognises
    its own half-finished state.
  - **`_committed_item_path` (`:5036`) and `_commit_holds` (`:4974`).** When
    `<root>/<status>/<slug>` is not in the tree, look for a nested path by
    listing `git ls-tree -r --name-only <rev> -- <root>/<status>` and matching
    `…/<slug>/state.yaml`. Return that folder. Search only the resolved-status
    folders, as today.

**Tests**

- `tests/test_retention.py` (criterion 17): with `work.retain.completed: false`
  and the resolved-work ignore rules removed (as the existing tests in this file
  set up), complete a parent that holds a legacy child, then call
  `delete_resolved(parent)`. Assert:
  - both folders are gone;
  - `tombstone(child)` is not `None` and its `location` names a commit where
    `git ls-tree` finds `completed/<parent>/<child>/state.yaml`;
  - `resolve_qualified_work_ref(root, "completed/<child>")` resolves to the tombstone;
  - `test_delete_resolved_is_re_runnable_after_an_interrupted_removal` still
    passes.
- `tests/test_retention.py`, interrupted multi-child deletion (two legacy
  children under one parent):
  (Today's order in `delete_resolved` is: guard, `rmtree`, graveyard write,
  commit.)
  - **Failure after the `rmtree`, before the graveyard write** (make the write
    raise once). The folders are gone and nothing is recorded. A rerun of
    `delete_resolved(parent)` still lists both children from `HEAD`, records the
    parent and both children in one write, and commits.
  - **Failure after the graveyard write, before the commit** (make
    `git_commit_result` fail once). A rerun accepts the graveyard's uncommitted
    entries for the parent and both children, finishes, and records each exactly
    once.
  - **An unrelated uncommitted graveyard entry** (another slug) makes the rerun
    refuse, as today.
  - After a successful run, the graveyard file changed in exactly one commit, and
    `git log -p` on it shows all three entries added together.
- `tests/test_tombstone.py`: the archived description for the nested child says
  "last present in commit …", not "does not contain the item".

### Task 10 — Tests of the other surfaces

Tests only. If one fails, fix the code it exercises in this task, and name the
fix in the commit message.

- `tests/test_serve_write.py` (criterion 19): the complete route
  (`tcw/serve/__init__.py:970-985`) on a parent with an open field child returns
  a 4xx status, and the JSON body contains the child's slug. Assert on the
  status class `_map_store_error` gives a `ValueError` today, read from that
  function rather than guessed.
- `tests/test_projection.py` (criterion 19): an `active` parent with a `backlog`
  field child projects the child with `status: "backlog"` and
  `parent: "<p>"`.
- `web/client/src/model/tree.test.ts` (criterion 19): a parent with
  `status: "active"` and a child with `status: "backlog"` and `parent` set nests
  the child under the parent. Run with `pnpm test`.
- `tests/test_tracker_sync.py` (criterion 20), using `tests/tracker_fake.py`: a
  bound field child is found and synced after its own `start` and `submit`, and
  after its parent's `start`. A bound legacy child is found after its parent
  moves.

### Task 11 — Documentation Sync (one block, over the finished diff)

Each documentation entry that fires, and what it gets:

- **`docs/guide/<topic>.md` [Guide-Topic-Change]** — fires. In
  `docs/guide/work.md`:
  - Rewrite `:482-487` ("Decomposing an item"): a child records its parent,
    starts in `backlog`, has its own status, keeps its parent through its own
    moves, and blocks its parent's completion, discarding or dropping while
    open. Children made by earlier versions keep following their parent.
  - Fix the comment at `:236` ("nested inside the parent's folder").
  - Mention the new `tcw validate` pointer messages wherever that guide lists
    what `validate` reports.
- **`README.md` [Public-API]** — fires. At `:396`, "A child item lives inside its
  parent's folder and moves with it" becomes "a child item has its own status and
  keeps a link to its parent".
- **`skills/<component>/SKILL.md` [Skill-Driven-Component]** — fires for `work`.
  - `skills/work/SKILL.md:63`: "splitting one item into nested pieces" becomes
    "splitting one item into child items".
  - `skills/work/references/commands.md:24`: "nest a coupled piece" becomes
    "add a child item".
  - `skills/work/references/procedures/decompose.md`: rewrite the "What nesting a
    child does" list and "Which path?" as the spec's Design describes. `--parent`
    is local, needs no epic, has no start gate, and blocks its parent's
    completion. `--initiative` points at an epic, crosses nodes, gates `start` on
    the epic being active, and is followed by `reconcile`. Children may be
    created before or after the parent's `start`, and each is started on its own.
- **Also rewritten here** (same reason, no entry of their own):
  - `tcw/work/procedures/decompose.md` (the text
    `tcw work procedure prompt decompose` prints);
  - `docs/capabilities/work/decompose-a-work-item-into-children/description.md`
    (the capability change);
  - the `FsWorkStore` docstring (`tcw/store/fs.py:3768-3774`);
  - `docs/lifecycle/abstraction.md:28` ("the FS adapter records it; it derives it
    from nesting only for children made by earlier versions");
  - `tests/cli/scenarios/10-cross-node-epics-and-nesting.md`. Rows 1 and 2 say a
    child's `tcw work path` "resolves inside the parent's folder", which is now
    false. Row 4 inverts: an epic with an open `--parent` child is refused,
    naming it.
- **`docs/changelogs/upcoming.md` [Any-Code-Change]** — fires. Under **Changed**:
  children are top-level items with a `parent:` field; `_parent_slug` falls back
  to nesting; the new `parent_children` / `open_descendants` /
  `_follows_parent` / `_require_live_parent`. The open-descendant refusal on
  `complete` (outside `--force`), `drop`, epic readiness and the pre-merge check.
  Under **Fixed**:
  - a child created under an active parent was born active;
  - a child's own transition dropped its parent;
  - re-parenting changed status;
  - `validate` misreported legacy children carried to completion;
  - deletion recorded no tombstone for nested children.
- **`docs/release-notes/upcoming.md` [Public-API]** — fires. In plain language: a
  child item now starts in backlog and can be planned on its own even when its
  parent is already underway. A parent cannot be closed while its children are
  open. Existing children keep working as before.
- **`docs/guide/jira.md` [Tracker-Change]** — does not fire. No
  `tcw work tracker` command, no `work.tracker` key, and nothing a lifecycle
  command does to a bound ticket changes. A refused `complete` touches no ticket,
  exactly as any refused transition already does. Recheck this against the
  finished diff.
- **`skills/configure/references/*.md` [Configuration-Key-Change]** — does not
  fire. No configuration key is added or changes meaning. (`parent:` is an item
  field, not configuration.)

## Coverage check (acceptance criterion → task)

| Criterion | Task(s) |
| --------- | ------- |
| 1, 2      | 6       |
| 3         | 6       |
| 4         | 6       |
| 5         | 6       |
| 6         | 3       |
| 7         | 2, 3    |
| 8         | 2, 3    |
| 9         | 2, 3    |
| 10        | 7       |
| 11        | 5       |
| 12        | 4       |
| 13        | 6, 8    |
| 14        | 1, 2, 3 |
| 15        | 2       |
| 16        | 7       |
| 17        | 9       |
| 18        | 1       |
| 19        | 10      |
| 20        | 10      |
| 21        | 11      |
| 22        | 6       |

## Verification

What the suite cannot check, done by hand at the end of implementation:

1. **The original reproduction.** In a scratch repository under
   `/private/tmp/claude-501/`, with the worktree's `tcw` on `PATH`, rerun the
   spec's six steps:
   - `new --parent` under an active parent prints a `backlog/` path;
   - `stage gate spec <child>` passes;
   - the suggested `tcw work start <child>` works;
   - `submit` keeps the parent;
   - completing the parent while the child is open is refused, and succeeds once
     it is done.
2. **A real legacy board.** Copy the proposit-app work store
   (`/Users/brian/Projects/proposit-orchestration/docs/proposit-app-repo/work`)
   into a scratch git repository and run `tcw work list`, `tcw work show` on each
   of the four nested children, and `tcw validate`. The children read `active`
   under their parent, exactly as with 2.5.0, and `validate` reports nothing new.
   Read-only against the original: copy first, never point at it.
3. **The web app.** Run `tcw serve` on the scratch board from step 1 and open it
   in the dedicated Claude Chrome profile. Confirm that the child shows under its
   parent with a different status badge, that dragging the parent to completed
   shows the refusal naming the child, and that editing the child's parent in the
   form does not change its column.
4. **Prose.** Run `grep -rn -i "shares its parent's status\|carries its children\|de-nest\|promotes it to a top-level\|travel with" tcw/ skills/ docs/guide docs/capabilities README.md`.
   It returns nothing (criterion 21).
5. **CI.** After pushing, read the actual CI result (`gh run list`), not only the
   local suite.

## Notes

- `drop` refusing over resolved field children (spec rule 4) means a backlog
  parent whose child was completed cannot be dropped, only discarded. That is
  intended: a drop leaves no tombstone, and the child's pointer would dangle.
- Task 2's `_follows_parent` reads `state.yaml` again for nested items only. A
  board with no nested items pays nothing extra.
- If Task 6's full-suite run turns up more than a handful of tests that assumed
  nesting, stop and list them in the task's commit message rather than letting
  the task sprawl. Each one is a reader that treated nesting as the parent
  relation (spec Risk 3).
- The worktree pre-merge check reads the branch's copy of the store when it can
  (Task 5). When the worktree cannot be read, only the primary copy is checked,
  and a child that exists only on that branch is caught by the store's own check
  after the merge. `outcome.md` must say so.

# Plan — Record the branch a work item is being implemented on

Seven tasks. Tasks 1-2 add the two store operations and leave every existing
test green on their own. Task 3 is the behaviour change and the riskiest one, so
it lands after its infrastructure exists and after the golden fixtures that
would otherwise mask it have been re-pinned in task 4. Tasks 5-6 are
presentation. Task 7 is the documentation block.

`pytest` must pass at every task boundary.

---

## Task 1 — `WorkStore.set_fields`, and `set_field` through it

**Modifies** `tcw/store/base.py`, `tcw/store/fs.py`.

Add to `WorkStore` (`tcw/store/base.py`, beside `set_field` at line 2242):

```python
@abstractmethod
def set_fields(self, slug: str, fields: dict) -> None: ...
```

with a docstring saying it applies the whole map in one write, so a pair like
`owner`/`started` cannot be torn across two locations by a move landing between
them — the reason `_set_fields_at` already gives at `tcw/store/fs.py:5632-5633`.
Make `set_field` a concrete method on `WorkStore` that calls
`self.set_fields(slug, {key: value})`, and delete `set_field` from the abstract
block.

In `FsWorkStore` (`tcw/store/fs.py:5623-5624`), replace the `set_field`
override with:

```python
def set_fields(self, slug: str, fields: dict) -> None:
    self._set_fields_at(self._require_dir(slug), fields)
```

Leave `_set_fields_at` untouched.

**Proves it:** `pytest` green with no test changes — this task changes no
behaviour. Add `test_set_fields_writes_every_key_in_one_read_modify_write` to
`tests/test_external_work_store.py`: monkeypatch `FsWorkStore._set_fields_at` to
count calls, call `store.set_fields(slug, {"owner": "a", "started": "b"})`,
assert one call and both keys present in `state.yaml`.

---

## Task 2 — `WorkStore.current_branch`, with a filesystem override

**Modifies** `tcw/store/base.py`, `tcw/store/fs.py`.

Add to `WorkStore` a **concrete** method, not an abstract one, so an adapter
written against the current interface keeps working:

```python
def current_branch(self) -> str:
    """The branch the implementation is happening on, or "" when this
    adapter cannot answer."""
    return ""
```

Override it on `FsWorkStore`:

```python
def current_branch(self) -> str:
    return git_current_branch(self.node_root) or ""
```

`self.node_root`, not `self.store_git_root`: `branch` records where the code is,
and `add_worktree` creates `work/<slug>` in `node_root`
(`tcw/store/fs.py:761-766`, called from `tcw/work/cli.py:833`). `_warn_off_trunk`
uses `store_git_root` because it asks a different question — where the
transition commit lands — and is not touched here.

**Proves it:** add to `tests/test_external_work_store.py`:

- `test_current_branch_names_the_code_node_not_the_store` — the external-node
  fixture already builds a `code` repo and a separate `orchestrator` work repo
  (`tests/test_external_work_store.py:28`). Check out `feature-x` in `code`,
  leave the work repo on its own branch, assert `store.current_branch() ==
  "feature-x"`.
- `test_current_branch_is_empty_on_a_detached_head` — `git checkout --detach`,
  assert `""`.
- `test_current_branch_is_empty_outside_a_repository` — a node whose code root
  is not a git repo, assert `""` and no exception.

---

## Task 3 — `start` records the branch with the claim

**Modifies** `tcw/store/base.py`.

Rewrite both claim writes in `WorkStore.start`
(`tcw/store/base.py:2665`). The takeover path at lines 2673-2674 and the normal
path at 2692-2693 each become one call. Build the map, then write once:

```python
def _claim_fields(self, owner: str) -> dict:
    fields: dict = {"branch": self.current_branch()}
    if owner:
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        fields.update({"owner": owner, "started": now})
    return fields
```

- Takeover path: `self.set_fields(slug, self._claim_fields(owner))` in place of
  the two `set_field` calls. `owner` is already required there
  (`"takeover requires an owner"`), so the map always carries all three.
- Normal path: replace `if owner:` + two `set_field` calls with an
  unconditional `self.set_fields(slug, self._claim_fields(owner))` followed by
  `result = self._require(slug)`. Unconditional is the point: `tcw serve` starts
  items with no owner (`tcw/serve/__init__.py:870`), and the old guard skipped
  the write entirely, so an unclaimed start would record no branch.

`branch` is written even when `current_branch()` returns `""`, replacing any
value a previous start left. Both calls sit **after** `self.transition(...)`,
which is what makes the unborn-HEAD case record a real branch: the transition's
own auto-commit gives the repository its first commit before the branch is read.

Nothing else writes or clears `branch`. Do not touch `transition`
(`tcw/store/base.py:2614-2637`) — it clears `owner`/`started` on every move
touching `active`, and adding `branch` there would fire on `submit` and
`complete` and break the worktree merge-back that reads it.

**Proves it:** add to `tests/test_external_work_store.py`, and run each against
the unchanged `start` first to confirm it fails:

- `test_start_records_current_branch` — criterion 1.
- `test_start_on_detached_head_records_no_branch` — criterion 2; the start still
  exits 0 and the item reaches `active`.
- `test_restart_replaces_recorded_branch` — criterion 3; start on `feature-a`,
  submit, rework, check out `feature-b`, take over, assert `feature-b`.
- `test_unowned_start_records_branch` — criterion 5; `store.start(slug)` with no
  owner, assert `branch` set and `owner`/`started` empty.
- `test_take_over_rewrites_claim_and_branch` — criterion 6; extend the existing
  `test_takeover_replaces_claim_and_submit_clears_it`
  (`tests/test_external_work_store.py:551`) rather than duplicating its setup.
- `test_start_writes_claim_and_branch_once` — criterion 7; count `set_fields`
  calls through a monkeypatched spy, assert exactly one per claim.
- `test_start_in_an_unborn_repo_records_the_branch` — criterion 12; `git init`
  with no commit, start, assert `branch` is the repository's initial branch
  rather than `""`. Force `init.defaultBranch=main` in the fixture so the
  assertion does not depend on the developer's global git config.
- `test_transitions_preserve_branch` — criterion 11; `submit`, `rework` and
  `complete` each leave `branch` as the last start wrote it.

And one CLI-level test, in `tests/test_environment_hardness.py` beside the
existing `main(["work", "start", slug, "--worktree"])` cases at lines 690 and
708:

- `test_worktree_start_records_work_branch` — criterion 4; start with
  `--worktree` from a checkout on some other branch, assert `branch` reads
  `work/<slug>` and not the branch that was checked out. This is the one
  criterion the store-level tests cannot reach, because the overwrite happens in
  the CLI at `tcw/work/cli.py:790-791`, after `st.start(...)` returns.

---

## Task 4 — re-pin the two golden fixtures

**Modifies** `tests/fixtures/show_baseline/rich_fields.txt`,
`tests/test_show_json.py`, `tests/fixtures/non_git_reads/work-list.txt`.

Task 3 makes `st.start(...)` write a branch, so both goldens go stale. They are
re-pinned here, before the display tasks, so that a display bug in task 5 or 6
cannot be absorbed into a fixture regenerated afterwards.

`tests/fixtures/show_baseline/rich_fields.txt` gains a `branch:` line after
`started:`. **The value must be interpolated, not hardcoded.** The fixture's
`node()` helper runs a bare `git init` (`tests/test_show_json.py:22-29`), which
picks up the developer's `init.defaultBranch` — `master` on some machines,
`main` on others. Add `{branch}` to the fixture and pass
`branch=item.branch` in the existing `.format(...)` call at
`tests/test_show_json.py:175-176`, the way `{started}` is already handled.

`tests/fixtures/non_git_reads/work-list.txt` is a board listing produced outside
a git repository (`tests/test_non_git_writes.py:462`), so `current_branch()`
returns `""` there and no branch segment is emitted. Confirm that by running the
suite; if the golden does change, regenerate it deliberately and check the diff
holds nothing but the expected line.

**Proves it:** `pytest tests/test_show_json.py tests/test_non_git_writes.py`
green, and `git diff` on the two fixtures shows only branch-related lines.

---

## Task 5 — `show` and the board display the fields

**Modifies** `tcw/work/cli.py`.

In `_print_item` (`tcw/work/cli.py:128-163`), after the `started` block at lines
149-150, add:

```python
if item.branch:
    print(f"branch: {item.branch}")
if item.worktree:
    print(f"worktree: {item.worktree}")
```

In `_render_board_item` (`tcw/work/cli.py:377-406`), add a segment built like
the existing `tag_seg`:

```python
branch_seg = f" | branch: {it.branch}" if it.branch else ""
```

and place it immediately before `{claim}` in the f-string at lines 405-406. The
rule is status-independent: a `review` item is live work whose branch is worth
finding, and the two resolved statuses are already hidden from the default
board.

**Proves it:** `test_show_prints_branch_and_worktree` in
`tests/test_show_json.py` (criterion 8 — both lines present when set, both
absent when empty) and `test_board_row_shows_branch` in `tests/test_work.py`
(criterion 9), placed beside the existing board-rendering tests there.

---

## Task 6 — `tcw work list --branch`

**Modifies** `tcw/work/cli.py`.

Add to the `list` parser (`tcw/work/cli.py:1890-1898`), directly under `--tag`:

```python
pl.add_argument("--branch", action="append",
                help="only items on this branch (repeatable = match any)")
```

No `type=` normalizer: git branch names are case-sensitive and are matched
exactly, unlike tags, which normalize through `_tag`.

Thread `args.branch` through `_list` (`tcw/work/cli.py:499-507`) into
`_render_board` and `_render_descendant_boards` alongside `tags`, and apply the
predicate in `_visible_board_items` where the tag filter already lives — a
client-side filter over what `query()` returned, adding no store operation.

**Proves it:** in `tests/test_work.py`, beside the existing list tests:

- `test_list_filters_by_branch` — criterion 10; one branch, two branches
  match-any, and an unknown branch listing nothing at exit 0.
- `test_list_branch_filter_is_exact_and_cased` — criterion 10; an item on
  `Feature-X` is not listed by `--branch feature-x`.

---

## Documentation Sync

One block, after the code tasks, evaluated over the finished diff.

- **`README.md` — [Public-API], fires.** The public CLI surface gains
  `tcw work list --branch`, and `tcw work start` records something it did not
  record before. Update the `tcw work list` mention at line 321 and the section
  around line 87. Required, not optional:
  `tests/test_documented_cli_surface.py` parses every tracked Markdown file for
  `tcw`-prefixed invocations, so a flag written into the docs must exist — and
  the reverse gap, a flag that exists and is undocumented, is what this entry
  covers.
- **`docs/release-notes/upcoming.md` — [Public-API], fires.** One entry in plain
  language: starting a work item now records the branch it is being implemented
  on, `tcw work show` and the board show it, and the board can be filtered to
  one branch. No module names.
- **`docs/changelogs/upcoming.md` — [Any-Code-Change], fires.** Grouped entries:
  *Added* — `tcw work list --branch`; `WorkStore.current_branch`;
  `WorkStore.set_fields`. *Changed* — `tcw work start` records `branch` on every
  claim, not only under `--worktree`; `tcw work show` and the board display
  `branch` and `worktree`. *Fixed* — `start` wrote `owner` and `started` as two
  separate store calls, which a concurrent transition could tear across two
  locations; they are now one write.
- **`skills/<component>/SKILL.md` — [Skill-Driven-Component], fires.**
  `skills/tcw-work/references/commands.md` line 8 gains `[--branch <b>]` in the
  board row and line 12 gains a note that `start` records the branch. The
  component's model and CLI surface both changed, which is exactly this
  trigger's condition. `skills/tcw-work/SKILL.md` itself needs no change: it
  routes to `commands.md` for the command table and states no field list.

---

## Verification

What the suite cannot check, to be done by hand before `submit`:

1. **A real two-repository node.** The `work.path`-in-another-repository shape
   is the one place `node_root` and `store_git_root` diverge, and task 2 depends
   on picking the right one. `tests/test_external_work_store.py` builds it, but
   confirm once by hand: check out different branches in the code repo and the
   work repo, run `tcw work start`, and confirm the recorded branch is the code
   repo's.
2. **`--worktree` merge-back end to end.** Criterion 4 is pinned by
   `test_worktree_start_records_work_branch`, but the merge-back half of
   criterion 11 destroys a worktree and a branch, so run it once by hand: start
   an item with `--worktree` in this checkout, commit on the work branch, and
   `tcw work complete` it, confirming the merge-back still finds the branch and
   the worktree is torn down. Scenario
   `tests/cli/scenarios/09-worktree-isolation-and-merge-back.md` covers the
   shape; the recorded branch value is the new part.
3. **Board width.** Look at a real board with several branch-carrying items on
   an 80-column terminal and confirm the extra segment does not make the rows
   unreadable. This is the risk the spec accepted; it is a judgment nothing can
   assert.
4. **`tcw validate` and `tcw capabilities check`** both exit 0 on this
   repository after the change (criterion 13).

## Notes

- No blockers. This item does not depend on
  `2026-09-10-let-a-node-declare-its-own-work-item-state-fields`, and that item
  does not depend on this one; `set_fields` from task 1 is the only thing they
  are likely to share, and it lands here.
- The capability sidecar is already written
  (`capabilities.yaml`, three `changed:` entries). No capability status moves at
  completion, so `tcw work complete`'s ledger gate has nothing to flip — but the
  three descriptions do need their new sentences, which is part of the
  completion step rather than a code task.

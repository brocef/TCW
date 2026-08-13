# Plan — Roll back or reorder the pre-move set_field writes on a lost transition

Four tasks, each green at its commit boundary. Task 1 is the whole behavior
change and carries its own tests; task 2 is text that was true only because of
the old ordering; task 3 is the second, independent half (`None` through a
non-optional signature); task 4 is documentation, as one block at the end.

Task 1 before task 2 because the comments in task 2 describe the ordering task 1
establishes — written first, they would describe code that does not exist yet.
Task 3 is independent of both and could run first; it goes last of the code tasks
because it is the lower-risk half and the riskiest change belongs where it is
isolated, not where it is convenient.

## Task 1 — Field writes ride the transition

**Changes**

- `tcw/store/base.py`
    - `_effect_transition` (abstract, `base.py:997`) gains
      `fields: dict | None = None`.
    - `transition` (`base.py:1268-1276`) gains the same parameter, merges its
      `owner`/`started` blanking into it with `update` (the lifecycle-owned keys
      win over a caller's), and passes the merged dict down. It no longer calls
      `set_field`.
    - `complete` (`base.py:1371-1421`) drops `set_field(slug, "resolution", …)`
      at `base.py:1407` and passes `{"resolution": resolution}` on **both**
      routes — `transition(slug, dest, fields)` at `base.py:1421` and the
      `from_backlog_epic` direct `_effect_transition(slug, dest, fields)` at
      `base.py:1418-1419`.
- `tcw/store/fs.py`
    - New `_set_fields_at(self, d: Path, fields: dict) -> None`:
      `load_yaml` → `state.update(fields)` → `dump_yaml` → `self._stage`.
    - `set_field` (`fs.py:2956-2961`) becomes
      `self._set_fields_at(self._require_dir(slug), {key: value})` — same
      behavior, same `no such work item` error from `_require_dir`.
    - `_effect_transition` (`fs.py:2963-2992`) takes `fields` and applies it at
      `dst` **after** `self._mv(src, dst)` (`fs.py:2990`) and **before** the
      auto-commit (`fs.py:2991-2992`). Writing at `dst` directly, not by
      re-resolving the slug: a third rescan would reopen the window the move just
      closed. The call is wrapped so a `CalledProcessError` out of `git_stage`
      (`fs.py:287`, e.g. a held `index.lock`) re-raises as
      `TransitionCommitError` — the item moved and the git step did not, which is
      what that error already means and what `_ERRORS` (`cli.py:34`) already
      handles.
    - `start`'s take-over branch (`fs.py:2056-2057`) writes `owner` and `started`
      through one `_set_fields_at` instead of two `set_field` calls, so a
      competitor moving the item between them can no longer tear the pair across
      two folders. One line; not the reported defect, but the same primitive.
- `tests/test_external_work_store.py` — the three
  `lose_the_race_inside_the_transition` stubs (`:654`, `:698`, `:740`) take
  `fields=None` and pass it through, or they raise `TypeError`.

**Order within the task (fail first, then fix)**

1. Invert `test_lost_complete_leaves_its_resolution_written`
   (`tests/test_external_work_store.py:718`) **in place** — keep the name, rewrite
   the docstring from "a documented limitation, pinned" to the guarantee, and
   assert `item.resolution is None` alongside the unchanged
   `item.status == "review"`. Run it; it fails.
2. Add the sibling for the other write: a `submit` that loses the race leaves
   `owner` and `started` at their pre-call values (they are set by `start`, so the
   fixture must start with an owner). Run it; it fails.
3. Make the code change above. Both now pass.
4. Add the three positive pins, which must never have been failing:
    - a **successful** `complete` still writes `resolution`, and a successful
      `submit` from `active` still blanks `owner`/`started`, read back from a
      fresh `FsWorkStore.open(...)`;
    - for a **tracked** destination (`review/`, which is not gitignored),
      `git show HEAD:<dst>/state.yaml` after `submit` already carries the blanked
      `owner` — i.e. the field write is inside the transition commit, not left
      dirty behind it;
    - a `git_stage` patched to raise `CalledProcessError` during the post-move
      write surfaces as `TransitionCommitError` naming the item and destination,
      and the CLI reports it with exit 1 and no traceback.

**Verified by**

`pytest -q` whole-suite green, with particular attention to
`tests/test_work_autocommit.py::test_every_transition_commits_its_own_move`
(`:247` asserts `porcelain(root) == ""` after each of four drives — it fails if
the field write lands after the commit rather than before it) and
`tests/test_lifecycle_hooks.py::test_a_failing_pre_hook_writes_no_field` (`:77`,
must pass **unmodified**).

## Task 2 — Say what is now true

Text only; no behavior change. Its verification is that task 1's suite stays
green plus the greps below.

**Changes**

- `tcw/store/fs.py:2977-2981` — the lost-race message: "This process did not move
  it" becomes "This process changed nothing". No test asserts that clause (only
  `cannot move` and `is now in '<status>'`), so nothing else moves with it.
- `tcw/store/fs.py:2689-2693` — `_status_resolution_problems`' docstring drops "no
  code path can produce" a disagreement and names the three ways one can now
  arrive: a hand-run `mv`, a bad merge, and a transition interrupted between its
  move and its field write.
- `tcw/work/cli.py:508-510` and `934-936` — the two `pre`-hook comments keep the
  rule (no store mutation before the hook) and drop the rationale that
  `complete()` writes fields first, which task 1 makes false. (The `start` block
  is `508-510`; `511` is the `run_pre` guard itself and does not change.)
- `tcw/store/fs.py:317-319` — `git_mv`'s justification for `rm -f`: "the
  transition stages the item's own state before moving it, so the index
  legitimately differs from both HEAD and the worktree". Task 1 removes that
  staging. `-f` is still required — `create_work` stages a never-committed item
  (`fs.py:3201`) — so only the reason changes.
- `tests/test_lifecycle_hooks.py` — the module docstring (`:4-8`) and
  `test_a_failing_pre_hook_writes_no_field`'s docstring (`:78-84`) make the same
  claim about `complete()` writing before it moves. Same correction; the
  assertions do not change.

**Verified by**

`grep -rn "no code path can produce" tcw/` and
`grep -rn "did not move it" tcw/` both empty (excluding `docs/work/`, which is
archive); `pytest -q` green.

## Task 3 — A read-back that loses the race raises

**Changes**

- `tcw/store/fs.py` — module-level
  `_require_detail(detail, kind: str, ref: str)`: returns `detail`, or raises
  `ValueError(f"{kind} '{ref}' could not be read back: another process moved or "
  f"removed it. Re-read it.")`. A function, not a method: the three stores are
  sibling classes over one `FsTreeStore` and a mixin would cost more than five
  call sites. The message says nothing about the write landing — at `fs.py:3316`
  nothing was written — but it always names the ref, which is the only way a user
  whose `tcw work new` failed learns the slug of the item that now exists.
- Applied at the five returns that promise a value:
  `fs.py:3203` (`create_work`), `fs.py:3316` and `fs.py:3338` (`update_work`),
  `fs.py:1260` (`update_term`), `fs.py:1925` (`update_capability`).

**Tests** (`tests/test_external_work_store.py` for the work sites; the taxonomy
and capabilities sites next to their existing store tests)

- Five, one per site, each monkeypatching the matching detail reader
  (`get_detail` / `get_term_detail` / `get_capability_detail`) to return `None`
  and asserting `pytest.raises(ValueError)` rather than `AttributeError`. The
  early-out at `fs.py:3316` is reached by an `update_work` call that changes
  nothing and passes no `parent`.
- `tcw work new` with the same monkeypatch exits 1, prints
  `tcw work new: …` on stderr, and shows no traceback — proving the error lands
  in `_ERRORS` (`tcw/work/cli.py:34`) rather than escaping `main`.
- `POST /api/work` with the same monkeypatch returns **422** with a JSON body
  instead of the current `500 server error: 'NoneType' object has no attribute
  'item'` (`serve/__init__.py:787`, caught by the bare `except Exception` at
  `:797`). If the existing serve tests have no fixture for driving a POST with a
  monkeypatched store, assert the mapping through `_map_store_error` directly and
  say so in the test docstring rather than building one.

**Verified by**

`pytest -q` green; `grep -n "return self.get_detail\|return self.get_term_detail\|return self.get_capability_detail" tcw/store/fs.py` shows every remaining bare return is on a function whose signature is `| None`.

## Task 4 — Documentation Sync

Evaluated against `CLAUDE.md`'s Documentation Sync section; two of four triggers
fire.

- **`docs/changelogs/upcoming.md`** [Any-Code-Change] — **fires.** New subsection
  under `## Fixed`-style grouping: the `fields` parameter on `transition` /
  `_effect_transition` and why (transition-plus-fields is one operation, which a
  remote tracker realizes natively); the write-after-move-before-commit ordering
  and the `porcelain == ""` invariant that pins it; `_set_fields_at` as the shared
  primitive under `set_field`; the inverted test; `_require_detail` and the five
  sites; the corrected `_status_resolution_problems` docstring.
- **`docs/release-notes/upcoming.md`** [Public-API] — **fires.** Plain language, no
  module names: when two people close or move the same item at once, the one that
  loses now leaves the item completely untouched — previously its resolution (or
  its cleared owner) could end up stamped on the copy the other person moved, so
  an item could sit in `completed/` reading `wontfix` when it was completed as
  `done`. And: creating or editing an item that is moved at the same instant now
  reports a clear error saying the change was saved but could not be read back,
  instead of an internal error.
- **`README.md`** [Public-API] — does not fire. No command, flag, or documented
  behavior changes; the README does not describe error text.
- **`skills/<component>/SKILL.md`** [Skill-Driven-Component] — does not fire. The
  work component's CLI surface, model/fields, lifecycle, and guardrails are all
  unchanged; `tcw-work` teaches the lifecycle, not the store's write ordering.

**Verified by** reading the two files back and checking each claim against the
finished diff — the doc pass runs once, over the whole diff, after tasks 1-3.

## Verification

Beyond the suite:

- **The race itself is not proven by any test.** Every test here forces the
  interleaving with `monkeypatch`, because nothing about real files makes `get`
  succeed while `_find` fails. Inherited from the parent item and accepted on the
  same terms: the tests exercise the handlers, not the concurrency. Nobody should
  read a green suite as "the race was reproduced".
- **Dogfooding is the end-to-end check.** Driving this item through
  `tcw work start` → `submit` → `complete` exercises the reordered path on a real
  store. After each transition, `git status --porcelain` must be clean (no stray
  `state.yaml` edit left behind) and `git show --stat HEAD` must show the item's
  own state file in the transition commit — the thing task 1's unit test asserts,
  confirmed once on a real repository.
- **`tcw work validate`** on this repository after the transitions: no
  status/resolution problem reported for any item this work touched.
- **Blockers:** none. This item's only dependency
  (`2026-08-11-harden-effect-transition-against-a-lost-status-transition-race`)
  is already completed, so nothing to record with
  `tcw work edit --blocked-by`.

## Notes

- If review objects to task 3's taxonomy/capabilities half (two one-line changes
  in components this item does not otherwise touch), it is cleanly separable —
  drop `fs.py:1260` and `fs.py:1925` and their two tests, keep the three work
  sites. The spec's sweep rule is why they are in by default.
- The `fields` parameter is optional at every level, so an adapter that ignores it
  keeps compiling. Only `FsWorkStore` implements `_effect_transition`, and no
  caller outside `tcw/store/base.py` invokes `transition` — the other
  `.transition(` hits are `LifecyclePolicy.transition`, an unrelated method.

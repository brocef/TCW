# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category.

## Added

- Five capability declarations covering the cross-node recursion surface, which
  the standing ledger did not describe at all: `work/inspect-the-node-topology`,
  `work/coordinate-a-cross-node-epic`, `work/reconcile-an-epic-rollup`,
  `work/delegate-a-request-to-a-child-node`, and
  `work/escalate-a-request-to-the-parent-node`. Declared `Supported` at creation
  — they document behavior that already ships, so the usual `Missing` +
  `Planning doc` seeding would have misattributed it. `Subject` and `Feature`
  point at existing taxonomy entries (`node`, `work-item`,
  `connected-project-registry`, `work-inbox`); no taxonomy entry was minted.
  Documentation only — no file under `tcw/` changed.

### Work inbox intake

- `FsWorkStore._resolve_inbox_ref` resolves an inbox identifier in a fixed order:
  exact ref, then `<ref>.md`, then a unique `InboxEntry.title` from `inbox_list`.
  `inbox_show` and `inbox_accept` both route through it, so sibling commands take
  the same identifiers. Exact wins outright — a folder named `example` stays
  addressable as `example` with an `example.md` beside it. Ambiguity is reachable
  only at the title step and raises `ambiguous inbox entry: … matches …` rather
  than picking by iteration order; nothing is consumed.
- `inbox_accept` propagates a delegated `initiative` into the accepted item's
  `state.yaml` via `_inbox_initiative`, parsed before anything is created or
  consumed. Absent, null, or whitespace-only means no initiative and produces the
  same item shape as before (no key written); a structured value (list/dict/tuple/
  set) raises rather than being serialized into state. Only this one frontmatter
  key crosses from intake into model state.
- Extracted `FsWorkStore._frontmatter(content, label)` from `_plan_manifest`, which
  now calls it. Same behavior and messages for `plan.md`; the inbox parser is the
  second caller rather than a second implementation.
- `tcw work delegate`'s `child` argument help named a "child node path"; it
  resolves a canonical project ID (`registered_project_id` over `child_nodes`).
  Help string corrected — no behavior change. The prior tests could not catch it
  because `mk_node` derives the project ID from the directory name;
  `test_delegate_resolves_the_project_id_not_the_directory_name` breaks that
  coincidence.

### Stable reads across claims

- Split `FsWorkStore.get` into `_get_now` (one immediate probe) and a stabilizing
  `get`. `get` returns hits and evidence-free misses immediately, and only waits —
  50 × 10 ms, the existing publication window — when `_claiming_dirs(slug)` proves
  that exact slug is mid-flight. An abandoned claim raises the documented
  interrupted-claim `ValueError`. `.claiming/` is not exposed through `WorkStore`;
  the abstract contract is still "the current item or None", with the adapter free
  to settle a transient move first.
- `_get_now` re-probes once when `_find` returns a folder that `_item_from_dir`
  then finds gone. That window is *not* the claim window — an ordinary `git mv`
  transition opens it and there is no `.claiming/` evidence to key on — so it is
  closed in the probe rather than in `get`.
- Three call sites deliberately keep the immediate probe, each because its job is
  the unstable state: `_lost_the_claim` (else each of its 50 iterations nests
  another 500 ms wait), `start`'s take-over probe (the branch exists for the state
  `get` now raises on, so `--take-over` would have become unreachable), and
  `_effect_transition`'s lost-race message (which wants the raw state to describe).
- `WorkStore.unresolved_blockers` catches an adapter's refusal to settle and
  reports that blocker as a blocker. Raising there would answer "why can't I start
  B?" with an error about A. Storage-neutral: any adapter may fail to resolve a
  reference.
- `get_detail` is now a whole-snapshot read: `_detail_snapshot` raises the private
  `_Moved` (or a `FileNotFoundError` from a path inside the item) and `get_detail`
  restarts, bounded at 5 attempts. All-or-nothing on purpose — pairing the first
  item with files re-read from its new status would hand out revisions that never
  coexisted. Permission errors and malformed content still surface.
- `test_get_detail_lost_at_find_returns_none` is superseded by
  `test_get_detail_retries_a_transient_loss_at_find`: `None` was the honest answer
  only while nothing looked again. `test_get_detail_gives_up_when_the_item_never_settles`
  pins the bound.
- Sibling sweep over every `_find` call site in `tcw/store`, `tcw/serve`, `tcw/work`
  found no further vulnerable reader. `artifacts()` and `_validation_resources`
  already carry explicit vanish guards; the rest are transition/write logic that is
  conflict-aware by contract, or single path lookups that read nothing.

### Transition field writes ride the move

- `WorkStore.transition` and the `_effect_transition` primitive take an optional
  `fields` dict and apply it **as part of** the move; neither writes before it.
  `complete` passes `{"resolution": …}` on both routes (the `transition` call and
  the `from_backlog_epic` direct `_effect_transition`), and `transition` merges
  its own `owner`/`started` blanking over the caller's fields with `update`, not
  `setdefault` — clearing the claim is a guarantee a caller must not be able to
  defeat. Storage-neutral: a remote tracker's transition endpoint takes field
  updates in the same call for the same reason.
- `FsWorkStore._effect_transition` applies the fields at the destination after
  `_mv` and **before** `_commit_transition`. After, because the move is where the
  process learns it won; before, because the transition commit is scoped to `src`
  and `dst` and takes working-tree state — that ordering is what keeps
  `porcelain(root) == ""` (`tests/test_work_autocommit.py:247`) true. Writing at
  `dst` directly rather than re-resolving the slug avoids reopening the window
  the move just closed.
- New `FsWorkStore._set_fields_at(dir, fields)`; `set_field` is now a one-line
  face over it. Multi-key, so `start`'s take-over branch writes `owner` and
  `started` in one read-modify-write instead of two `set_field` calls that a move
  landing between them could tear across two folders.
- A `git add` refused during the post-move write (a held `index.lock`, which is
  what concurrent agents produce) raises `TransitionCommitError` rather than
  letting `CalledProcessError` — absent from `tcw/work/cli.py`'s `_ERRORS` —
  escape as a traceback. The item moved and the git step did not, which is
  exactly what that error already means to the CLI and to `serve._transition_ok`.
- `test_lost_complete_leaves_its_resolution_written` is **inverted in place**, as
  its own docstring instructed: same scenario, asserting `resolution is None`.
  Three `_effect_transition` monkeypatch stubs take the new parameter.
- `_status_resolution_problems`' docstring no longer claims no code path can
  produce a status/resolution disagreement. It names what remains: a hand-run
  `mv`, a bad merge, and a transition interrupted between its move and its field
  write. The two `pre`-hook comments in `tcw/work/cli.py` and `git_mv`'s `-f`
  justification cited the pre-move staging and were corrected; the hook's
  position in the CLI is unchanged and `test_a_failing_pre_hook_writes_no_field`
  passes unmodified.

### Composite writes no longer leak `None`

- `_require_detail(detail, kind, ref)` guards the five returns where a
  `-> … | None` read-back was handed through a non-optional signature:
  `create_work`, `update_work` (both returns), `update_term`,
  `update_capability`. Previously the `None` surfaced as an `AttributeError` at
  the first caller to dereference it — `FsWorkStore.create`, `tcw work new`
  (`work/cli.py:234`), and both `serve` write routes, where the bare
  `except Exception` rendered `500 server error: 'NoneType' object has no
  attribute 'item'`. Now a `ValueError` that `_ERRORS` and
  `serve._map_store_error` (→ 422) already handle.
- The message deliberately does not assert the write landed: `update_work`'s
  no-change early return writes nothing. It always names the ref, which is the
  only way a failed `tcw work new` tells the user the slug of the item that now
  exists.

### Reconcile commit reporting

- `reconcile` (`tcw/work/recursion.py`) commits through `git_commit_result`
  instead of `git_commit` and raises `ValueError` carrying git's output.
  `git_commit` raises `subprocess.CalledProcessError`, which is absent from
  `tcw/work/cli.py`'s `_ERRORS`, so a refused commit escaped `main` as a
  traceback. `_ERRORS` is deliberately **unchanged**: it guards 16 `except` sites,
  and widening it would swallow the `git_mv` raise-through that
  `tests/test_work_autocommit.py:311` exists to protect.
- Removed the `changed or auto_completed` guard on the commit. It existed only to
  avoid an empty commit back when that raised; `git_commit_result` answers
  "nothing to commit" benignly. Keeping it broke recovery: after a refused commit
  the rollup is already correct on disk, so a retry computed `changed=False`,
  skipped the commit, and exited 0 with the rollup still staged — a false success
  reached by following the documented retry. Idempotence is unchanged (an
  unchanged rollup with nothing else staged has nothing committable). One nuance:
  an unchanged reconcile now also commits unrelated work-store changes that were
  already staged, the same whole-store pathspec behavior a changed reconcile has
  always had.
- `git_commit` now has no production caller and is retained as a test helper
  (`tests/test_recursion.py`). Not dead code to delete.
- `tests/test_recursion.py`: `_refuse_commits` writes a rejecting `pre-commit`
  hook into the repository's own `.git/hooks/`, independent of `core.hooksPath`.
  `test_refusing_hook_fixture_actually_blocks_a_commit` guards the fixture itself,
  so an environment where hooks go inert fails there rather than letting the
  reconcile tests pass for the wrong reason.

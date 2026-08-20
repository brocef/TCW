# Outcome — Fail fast with clear errors on non-Git writes

## What shipped

Eight commits, in plan order, each with the suite green at its boundary.
Interleaved with three sibling items' planning commits on the same branch;
only the eight below touch code.

| # | Commit | Task |
| - | ------ | ---- |
| 1 | `c0b340e` | `require_repository` / `NOT_A_REPOSITORY` in `tcw/store/fs.py`, plus `FsTreeStore._require_repository`/`_write_git_root` and the `FsWorkStore._write_git_root` override. No call sites. |
| 2 | `b59ffbd` | `FsWorkStore`: Tier 1 on `_stage`/`_rm`/`_mv`, Tier 2 on eleven public write methods, and the rewritten pinned test. |
| 3 | `f324a96` | `FsTreeStore`/`FsTaxonomyStore`/`FsCapabilitiesStore`: Tier 1 plus nine Tier-2 sites. |
| 4 | `28ebf1b` | `main()`'s generic `subprocess.CalledProcessError` handler; `run_init` prints the shared constant. |
| 5 | `434cc27` | `tcw serve` write routes pinned (tests only — no serve code changed). |
| 6 | `d9c86c3` | The `_inbox_write` guard, the end-to-end CLI matrix, the read goldens, and scenario 14. |
| 7 | `b749779` | The three capability bodies named in `capabilities.yaml`. |
| 8 | `2285ce6` | Documentation Sync. |

**Guard sites: 20, not the 19 the plan predicted.** The twentieth is
`_inbox_write` in `tcw/work/recursion.py` — see "What the plan and spec got
wrong", item 1.

## Test result

```
$ python -m pytest -q
........................................................................ [ 96%]
............................................................             [100%]
1788 passed in 328.95s (0:05:28)
```

Baseline was 1763; the 25 new tests are in `tests/test_non_git_writes.py` (23,
one of them parametrized over the seven read commands) and
`tests/test_serve_write.py` (1), plus the rewritten one in
`tests/test_work_autocommit.py`.

Every test was watched red before the code that makes it pass. Two needed the
old tree to be red, and were checked against it rather than asserted:

- the `main()` handler test, red via `git stash push tcw/cli.py` — it exits as
  `CalledProcessError` without the handler;
- the serve-route test, red via `git checkout c0b340e -- tcw/store/fs.py` — every
  route answered **500**, which is what the spec measured.

## Acceptance criteria

| # | Where it is discharged |
| - | ---------------------- |
| 1 | `test_every_cli_write_refuses_with_one_wording_and_writes_nothing` — 28 commands in the parent node plus `escalate` from the child. |
| 2 | The same test's directory-inclusive manifest compare, taken around every command. |
| 3 | `test_start_leaves_the_item_in_backlog`, and by hand with the shipped binary (below). |
| 4 | `test_read_output_is_unchanged_outside_a_repository`, against goldens captured from `dbed08a`. |
| 5 | `test_non_git_graph_is_unaffected` passes unmodified. |
| 6 | `test_init_refuses_outside_git` passes unmodified; `test_init_refuses_with_the_shared_wording` pins the literal stderr. |
| 7 | `test_a_write_outside_a_repository_is_refused_before_it_writes` — renamed, docstring records the reversal. |
| 8 | `test_a_git_subprocess_failure_is_a_message_not_a_traceback` — one identical line through all three components, no source-text assertion. |
| 9 | `test_every_write_route_refuses_outside_a_repository` — nine routes, 4xx not 500, manifest unchanged. |
| 10 | `test_a_repository_removed_after_a_successful_write_still_refuses`. |
| 11 | Above. |

## Verification beyond the suite

**The shipped binary**, run by hand against the spec's Reproduction fixture
(`git init` → seed → commit → `rm -rf .git`), because every test drives `main()`
or the store API rather than the installed `tcw`:

```
$ tcw work start 2026-08-19-a-thing
tcw work: not inside a git repository. Run `git init` first.
rc=1
backlog: 2026-08-19-a-thing        # criterion 3 — still in backlog
active:

$ tcw work new "Another"
tcw work new: not inside a git repository. Run `git init` first.
rc=1                                # criterion 2 — backlog unchanged

$ tcw taxonomy add "Gadget" --slug gadget
tcw taxonomy add: not inside a git repository. Run `git init` first.
rc=1                                # docs/taxonomy/ still holds only widget

$ tcw init
tcw init: not inside a git repository. Run `git init` first.

$ tcw work list; tcw validate; tcw taxonomy list
2026-08-19-a-thing | backlog | - | - | A thing
validate OK
widget  [V] (local)                 # reads rc=0
```

**Perf**, which the plan required as a number rather than an assumption. Five
runs of `tcw work reconcile` over an epic with five slices, at HEAD and at
`dbed08a`:

```
HEAD (guarded):     880 ms total, 176 ms each
dbed08a (pre):      887 ms total, 177 ms each
```

No measurable regression. The spec's 6.6 ms per `git rev-parse` is real but
swamped by ~150 ms of interpreter startup per invocation, and a command makes
only a handful of guarded calls. Dropping memoization cost nothing.

**Not verifiable here, stated instead:** whether anyone runs TCW writes outside
a repository today and depends on the partial write surviving. Nothing in the
suite can prove nobody does.

## What the plan and spec got wrong

### 1. `delegate` and `escalate` did not traceback — they *succeeded*

The spec's Problem §1 filed them under "same class" as the other writes and its
Assumptions flagged them as inferred rather than measured. The inference was
wrong, and wrong in the more interesting direction. `tcw work delegate` outside
a repository exited **0** and wrote a complete request into the destination
node's inbox.

`_inbox_write` (`tcw/work/recursion.py`) is the only write in the adapter that
**never stages**, so it has no git dependency at all and the `_stage` guard
cannot reach it. Left alone it is a half-working feature, not a working one: the
note is untracked, no `git status` will show it, and the destination's own
`inbox accept` refuses it, so the request can never become work. Guarded at
`_inbox_write` — the single funnel behind both commands — against the
*destination* store's repository.

**The real defect was the plan's scoping, not its table.** The mutation walk was
declared over `tcw/store/fs.py`, and this write lives in `tcw/work/recursion.py`.
A walk bounded by one file cannot find the write in another. Found only because
the end-to-end CLI matrix ran `delegate` for real.

### 2. Three commands in the spec's own Problem table were mis-specified

All three were rows the spec marked "refused earlier in this fixture" and never
actually ran:

- **`tcw capabilities extends` is not `extends add`/`extends rm`.** Taxonomy
  takes subcommands; capabilities takes `extends <project_id> [--rm]`. The spec
  said "same as taxonomy's".
- **`tcw capabilities reset` cannot be reached** without a federated override —
  it refuses "not an override" on a local capability, before any git path. Its
  `git rm` is the one `remove` exercises. Dropped from the matrix with the
  reason in the test, and listed under "Explicitly not covered" in scenario 14.
- **`tcw work submit` needs a genuinely `active` item.** The legality gate runs
  before the store guard, so submitting a backlog item refuses with "not a legal
  transition" — a test that passes for the wrong reason. Cost one red run; now a
  note in scenario 14's implementer section.

### 3. Serve has no artifact `DELETE` route

Plan task 5 named `DELETE` on a work artifact among the routes to check. Serve's
only DELETE routes are `/api/work/<slug>` and `/api/work/<slug>/plan-stages/<id>`.
The plan-stage one was dropped too — it refuses "undeclared plan stage" before
any git path, and declaring one needs a plan manifest. Replaced with the
sidecar and plan-stage `PUT`s and the work `DELETE`.

### 4. `.claiming/` survives a successful `start`

Pre-existing, not caused by this change, but it invalidated the plan's proposed
assertion. `FsWorkStore.start` creates `docs/work/.claiming/` and nothing ever
removes it, so `assert not (root / "docs/work/.claiming").exists()` passes for
the wrong reason on any node that has ever started an item — and the shared
fixture starts one. The test now uses a node that never started anything, and
says why in its docstring.

The plan's insistence that manifests walk **directories** was right for exactly
this reason and is what caught it.

### 5. `SKILL.md` could not take the guardrail

The plan's Documentation Sync block said one line in `skills/tcw-work/SKILL.md`.
The router's body budget is 60 lines and `test_the_router_stays_within_its_line_budget`
enforces it, with the stated rule "extract, never grow". A refusal that only
appears in a non-git project is exactly the rare detail progressive disclosure
says to push down, so it landed in `references/commands.md`. The plan predicted
the right trigger and the wrong file.

### 6. The plan's golden-capture procedure is dangerous as written

It said to `git stash` the working tree and check out the old `tcw/`.
`git checkout <sha> -- tcw/` **stages** what it restores and silently discards
uncommitted work anywhere in that tree — it ate the in-progress `_inbox_write`
guard once, and the `&&` chain meant a failing capture skipped the restore, so
the tree sat on old code. The procedure that works, recorded so nobody repeats
it: `git stash push -q tcw/ <test files>` → `git checkout <sha> -- tcw/` → run →
`git checkout HEAD -- tcw/` → `git stash pop -q`, then verify the uncommitted
change is still there.

## Notes

### For whoever implements next in `tcw/store/fs.py`

Three sibling items land here after this one. Locate by symbol; every line
number in the spec and plan has moved by roughly +30. The overlaps the plan
predicted all held:

- `FsCapabilitiesStore.set` and `update_capability` each gained a first-line
  `self._require_repository()` — the capability-refs item edits both.
- `FsWorkStore.inbox_accept` gained one too, immediately above the
  `accepted_title` line the inbox-title item changes.
- `FsTreeStore` gained `_write_git_root` and `_require_repository` beside
  `_stage`/`_rm`/`_mv`, where the symlink item adds `_within_store`.
- No collision on `FsTaxonomyStore.add`/`FsCapabilitiesStore.add`, as predicted —
  this item guards `_write_node` underneath them.

The symlink item's `CalledProcessError` leak (its spec, Problem §6) is closed by
commit `28ebf1b`, whether or not that item has landed.

### Two deliberate redundancies, left in

- `FsCapabilitiesStore.set` probes git twice (its own guard, then
  `_write_meta`'s). `set` needs its own ahead of its `mkdir`; `_write_meta`
  needs its own so the funnel claim holds for a future caller. Two
  `git rev-parse` calls on one path, measured as noise.
- `_effect_transition` guards even though `_mv` does. It creates the destination
  status folder before the move.

### One thing observed and not fixed

`docs/work/.claiming/` is created by every `start` and never removed, so a node
accumulates an empty directory the first time anyone starts an item. Harmless,
pre-existing, and out of scope here — but it is the kind of thing a manifest
test will keep tripping over, so it is worth an item if anyone cares.

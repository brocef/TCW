# Spec — Roll back or reorder the pre-move set_field writes on a lost transition

## Capability changes

None. The node's ledger already declares the affected commands —
`work/complete-a-work-item`, `work/submit-a-work-item-for-review`,
`work/rework-a-reviewed-work-item`, `work/open-a-work-item` — all `Supported`,
and this change adds no ability and removes none. `complete-a-work-item`'s text
promises that "the resolution picks where it lands" and that "TCW commits the
status move itself"; both stay true, and neither says anything about a losing
writer, so no wording changes either.

(The parent item's spec recorded "this node has no capabilities component". That
was wrong — `tcw capabilities list` returns 40+ entries. The conclusion is the
same for a different reason.)

## Problem

Two field writes land *before* the move they belong to, and a move that loses a
race to a competing process leaves them behind:

- `WorkStore.transition` blanks `owner` and `started` when either end of the move
  is `active` (`tcw/store/base.py:1272-1274`), then calls `_effect_transition`
  (`base.py:1275`).
- `WorkStore.complete` stamps `resolution` (`base.py:1407`) before it calls
  `transition` (`base.py:1421`) — or, for a completable epic closing straight
  from `backlog`, `_effect_transition` directly (`base.py:1418-1419`).

`set_field` (`tcw/store/fs.py:2956-2961`) resolves the item by slug and writes
`state.yaml` wherever the item is *at that instant*. `_effect_transition`
(`fs.py:2963-2992`) then resolves it again and refuses when it has moved
(`fs.py:2969-2981`, the guard the parent item added). So on a lost race the write
has already landed in the folder the **winner** moved, and it travels with it.

The worst case, pinned today by
`tests/test_external_work_store.py:718` (`test_lost_complete_leaves_its_resolution_written`):
agent A completes an item as `done` and moves it to `completed/`; agent B, racing,
stamps `resolution: wontfix` and then loses the move. The item sits in
`completed/` reading `wontfix`. `FsWorkStore._status_resolution_problems`
(`fs.py:2687-2708`) detects exactly that disagreement, while its own docstring
(`fs.py:2689-2693`) still says "no code path can produce" one. That claim is
false.

### The ordering constraint is real but does not block the obvious fix

The request records the fix as blocked by the ordering documented at
`tcw/work/cli.py:934-939`. Reading it, it is not:

```python
    if (err := run_pre(policy, transition_id, st.node_root, bare, item.status)):   # cli.py:937
        ...
    st.complete(bare, args.resolution, dod_ack=checklist, force=args.force)        # cli.py:941
```

The `pre` hook runs in the **CLI**, before `st.complete()` is entered at all. The
same shape guards `start` (`cli.py:509-512`). Reordering writes *inside*
`complete()` cannot reach it: a failing hook still returns before any store call,
so `tests/test_lifecycle_hooks.py:77`
(`test_a_failing_pre_hook_writes_no_field`) keeps passing unmodified — more
robustly, since after this change there is no field write before the move to
strand. What the comments explain is why the hook may not be pushed *later* (e.g.
into the store); that rule survives, its stated rationale does not.

### Why rollback is the wrong branch of the fork

Restoring the pre-write values after a failed move is a lost update. B captured
`resolution: None` before writing `wontfix`; by the time B's move fails, A has
written `done` and moved. B's rollback resolves the slug again, finds the
winner's folder, and writes `None` over A's `done` — trading a wrong resolution
for a missing one, on an item B has no claim to. Every rollback ordering has this
shape, because the loser's rollback target is stale by construction.

Reordering has no such problem: the move is the point at which this process learns
it won, so writing after it writes only to an item this process moved.

### Also in scope: `None` escaping a non-optional signature

`get_detail` (`fs.py:3045-3061`) returns `WorkDetail | None` and gives up after 5
attempts. Five call sites return that value through a signature that promises a
value:

| Site           | Function                          | Declared              |
| -------------- | --------------------------------- | --------------------- |
| `fs.py:3203`   | `create_work`                     | `-> "WorkDetail"`     |
| `fs.py:3316`   | `update_work` (no-change early out) | `-> "WorkDetail"`   |
| `fs.py:3338`   | `update_work`                     | `-> "WorkDetail"`     |
| `fs.py:1260`   | `update_term`                     | `-> "TermDetail"` (`fs.py:1196`)       |
| `fs.py:1925`   | `update_capability`               | `-> "CapabilityDetail"` (`fs.py:1877`) |

The last two are the sibling half of the same defect: `get_term_detail`
(`fs.py:1179-1182`) and `get_capability_detail` (`fs.py:1861-1864`) return `None`
when the entry vanishes between the write and the read-back. They have no status
transitions to race, only a concurrent delete or rename, so they are rarer — not
different.

**The request's claim that "every present-day caller is safe" is wrong.** It
enumerated `get_detail`'s direct callers (`serve/__init__.py:588`, `624`, and the
stale-revision check at `fs.py:3215`), which do test for `None`. The escape route
is the *composite* callers, and four of them dereference unguarded:

- `FsWorkStore.create` (`fs.py:2953`) — `create_work(...).item`.
- `tcw work new` (`tcw/work/cli.py:222`, dereferenced at `234`).
- `POST /api/work` (`serve/__init__.py:773`, dereferenced at `787`) — the
  `AttributeError` falls to the bare `except Exception` at `797` and renders as
  `500 server error: 'NoneType' object has no attribute 'item'`.
- `PATCH /api/work/<slug>` (`serve/__init__.py:991`, dereferenced at `992`) —
  same, via the `except Exception` at `1005`.

(`tcw work edit` at `cli.py:778` discards the return value, so it is safe.)

Still not a regression — before the parent item's guard the same timing raised
`TypeError` inside `get_detail` — and still worth fixing here, because it is the
same question: *what does a write path that loses the race hand back?*

## Goals

1. A transition that loses the race changes **nothing** — not the folder, not a
   field. The error message may then say so instead of scoping its claim to the
   move.
2. Field writes that belong to a transition are committed with it, as today: no
   new dirt in the working tree after `tcw work complete` / `submit` / `rework`.
3. The `pre`-hook guarantee (a failing hook writes no field) is preserved, and the
   comments that explain it say something that is still true.
4. A write path whose read-back loses the race raises a handled error naming the
   item, rather than handing `None` through a signature that forbids it.
5. `_status_resolution_problems`' docstring describes the windows that actually
   remain.

## Non-goals

- **No claiming protocol for `submit`/`rework`/`complete`.** Inherited from the
  parent spec and still right: `.claiming/` exists because `start` has a genuine
  two-agent race. Building it here would be cost without evidence.
- **No new exception type.** `ValueError` is in `_ERRORS` (`tcw/work/cli.py:34`)
  and `serve`'s `_map_store_error` (`serve/__init__.py:180-199`) already maps it.
- **No widening of `create_work` / `update_work` / `update_term` /
  `update_capability` to `-> Detail | None`.** That pushes the ambiguity onto
  every caller to answer again, and "the item you just created does not exist" is
  not a truthful thing to return.
- **`FsWorkStore.start`** (`fs.py:2014-2108`). It overrides the base entirely and
  already does the right thing — it writes `owner`/`started` into a private
  `.claiming/` folder (`fs.py:2095-2098`) and then publishes with one atomic
  `os.replace` (`fs.py:2101`), so a loser's write never reaches the winner's item.
  `WorkStore.start`'s own post-transition writes (`base.py:1330-1332`) are
  unreachable under the FS adapter and land *after* a successful move anyway.
- **`update_work`'s write-then-re-parent ordering** (`fs.py:3263-3266`,
  `3335-3336`). Edits deliberately land in the current location before the rename.
  A failed rename strands them on an item that did not move — an intra-item edit,
  not a status/resolution disagreement, and the ordering is load-bearing for
  carrying nested children in one rename. Named here so it is a chosen exclusion.
- **Retry-on-loss.** Neither half re-attempts after losing; both report and let the
  caller decide, as the parent item established.

## Design

### 1. Field writes ride the transition

Give the adapter primitive the fields to apply:

```python
def _effect_transition(self, slug: str, to_status: str,
                       fields: dict | None = None) -> None: ...   # base.py:997
```

`WorkStore.transition` gains the same optional parameter, merges its own
`owner`/`started` blanking into it, and hands the result down:

```python
def transition(self, slug, to_status, fields: dict | None = None) -> WorkItem:
    item = self._require(slug)
    if (item.status, to_status) not in self.LEGAL_TRANSITIONS:
        raise IllegalTransition(...)
    merged = dict(fields or {})
    if item.status == "active" or to_status == "active":
        merged.setdefault("owner", "")
        merged.setdefault("started", "")
    self._effect_transition(slug, to_status, merged)
    return self._require(slug)
```

`complete` passes `{"resolution": resolution}` instead of calling `set_field`
first — on both routes, including the `from_backlog_epic` direct call
(`base.py:1418-1419`).

**Litmus test.** "Could a non-filesystem store apply field values as part of a
transition?" Yes, and more naturally than the split version: Jira's transition
endpoint takes a `fields` object precisely because transition-plus-fields is one
operation. This moves the model *toward* portability rather than away.

### 2. The adapter writes after the move, before the commit

In `FsWorkStore._effect_transition`, after `self._mv(src, dst)` (`fs.py:2990`)
and before the auto-commit (`fs.py:2991-2992`):

```python
self._mv(src, dst)
if fields:
    self._set_fields_at(dst, fields)
if self.auto_commit_transitions():
    self._commit_transition(slug, src, dst, to_status, item)
```

with `set_field` (`fs.py:2956-2961`) refactored onto the same helper:

```python
def _set_fields_at(self, d: Path, fields: dict) -> None:
    state = load_yaml(d / "state.yaml")
    state.update(fields)
    dump_yaml(d / "state.yaml", state)
    self._stage(d / "state.yaml")

def set_field(self, slug, key, value) -> None:
    self._set_fields_at(self._require_dir(slug), {key: value})
```

Writing at `dst` rather than re-resolving by slug is deliberate: this process just
moved the item there, so a third rescan would only reopen the window the move
closed.

Two mechanics make this land correctly:

- The transition commit is scoped to `src` and `dst` (`fs.py:3008-3010`) and a
  scoped `git commit -- <paths>` takes working-tree state, so the field write at
  `dst` is inside the commit. `tests/test_work_autocommit.py:247` asserts
  `porcelain(root) == ""` after every transition; that only keeps passing because
  the write precedes the commit. Writing after `transition()` returns — the naive
  reorder — fails it.
- `git_stage` drops ignored paths (`fs.py:280-287`), so staging `dst/state.yaml`
  under the gitignored `completed/` and `discarded/` is the same no-op it is
  today.

### 3. The error can now claim what it delivers

`_effect_transition`'s message (`fs.py:2977-2981`) currently says "This process
did not move it", deliberately narrow because the field writes had landed. With
no write before the move it becomes true that nothing was changed, so the sentence
becomes "This process changed nothing; re-read the item before retrying." The
`test_..._reports_where_the_item_went` assertions match on
`"is now in 'backlog'"`, not on this clause, so only the message text changes.

### 4. The remaining window, stated honestly

After the fix, a disagreement needs the process to die (or the write to fail on
I/O) between a successful move and the field write — microseconds, and on an item
*this* process legitimately owns. The result is a completed item with no
resolution, which `_status_resolution_problems` reports as "status 'completed'
with missing or invalid resolution" (`fs.py:2703-2704`) — loud and on the right
item, versus today's silent wrong answer. Its docstring (`fs.py:2689-2693`) is
rewritten to say that, replacing "no code path can produce" a disagreement.

### 5. `_require_detail` for the five read-back sites

```python
def _require_detail(detail, kind: str, ref: str):
    """A composite write's read-back lost the race. The write landed; the caller
    asked for a snapshot that no longer exists to take."""
    if detail is None:
        raise ValueError(f"{kind} '{ref}' was written, but reading it back failed: "
                         f"another process moved or removed it. Re-read it.")
    return detail
```

A module-level function, not a method: the three stores are separate classes over
one `FsTreeStore`, and one shared line per site beats a mixin. Applied at
`fs.py:3203`, `3316`, `3338`, `1260`, `1925`.

Downstream effects, all handled: `tcw work new` prints
`tcw work new: <message>` and exits 1 (`cli.py:232-234`); `FsWorkStore.create`
(`fs.py:2953`) propagates the same `ValueError`; both `serve` write routes hit
`_map_store_error` and return **422** with a JSON body instead of a 500 whose
text is `'NoneType' object has no attribute 'item'`. 422 over 409 because
`StaleRevision` owns 409 (`serve/__init__.py:189-190`) and this is not a stale
revision — and because adding a status code means adding an exception type, which
is a non-goal.

The message deliberately says the write **landed**. It did: the item exists, and
`tcw work new` returning non-zero for a created item is only defensible if the
message says so.

### Sibling sweep

Repo-wide, both defect shapes.

**Store mutations preceding a move.** All 13 `set_field` call sites in `tcw/`:

| Site                          | Verdict                                                        |
| ----------------------------- | -------------------------------------------------------------- |
| `base.py:1273-1274`           | The defect (transition). Fixed.                                 |
| `base.py:1407`                | The defect (complete). Fixed.                                   |
| `base.py:1233`, `1248`        | `add_blocker` / `remove_blocker` — standalone, no move follows. |
| `base.py:1312-1313`, `1330-1332` | `WorkStore.start` — after the move, and dead under FS.       |
| `fs.py:2056-2057`             | Take-over — writes then commits; no move.                       |
| `cli.py:539-540`              | `--worktree` fields — after `start`, committed at `cli.py:545+`. |

Non-`set_field` writes-before-a-move: only `update_work`'s re-parent
(non-goal above). No other `_mv` in `tcw/store/fs.py` is preceded by a write to
the moving item.

**`None` through a non-optional signature.** Every `-> "*Detail"` return in
`tcw/store/fs.py` (the table under Problem) — five vulnerable, all fixed; there is
no `create_term` / `create_capability` to check.

## Acceptance criteria

1. `store.complete(slug, "done", [])` that loses the race (`_find` monkeypatched
   to `None` at the move, as the existing tests do) leaves `resolution` exactly
   as the competing process left it, and still raises `ValueError` matching
   `cannot move`. `tests/test_external_work_store.py:718` is **inverted** in
   place — same name is fine, docstring rewritten from "a documented limitation"
   to the guarantee — not deleted.
2. The same for the `owner`/`started` pair: a `submit` that loses the race leaves
   both fields at their pre-call values.
3. A **successful** `complete` still writes `resolution`, and a successful
   `submit` from `active` still blanks `owner`/`started` — asserted from a fresh
   store read, so the reorder cannot silently drop the write.
4. `tests/test_work_autocommit.py::test_every_transition_commits_its_own_move`
   passes unmodified (`porcelain(root) == ""` after each of the four drives), and
   a new test asserts that for a **tracked** destination (`review/`) the
   transition commit itself carries the field change — `git show HEAD:<path>` of
   the destination `state.yaml` has the blanked `owner`.
5. `tests/test_lifecycle_hooks.py::test_a_failing_pre_hook_writes_no_field` passes
   unmodified. The comments at `tcw/work/cli.py:509-511` and `934-936` no longer
   justify the hook's position with "complete() writes the resolution first" —
   they state the surviving rule (no store mutation before the hook) with a
   rationale that matches the code.
6. `FsWorkStore._status_resolution_problems`' docstring no longer contains "no
   code path can produce", and names the interrupted-between-move-and-write
   window alongside the hand-run `mv` and the bad merge.
7. Each of the five read-back sites raises `ValueError` — not `AttributeError` —
   when its detail read returns `None`, driven by monkeypatching `get_detail` /
   `get_term_detail` / `get_capability_detail`. Five tests, one per site
   (`update_work` has two reachable returns; the early-out at `fs.py:3316` needs a
   no-change call to reach).
8. `tcw work new` surfaces that as `tcw work new: <message>` on stderr with exit
   1 and no traceback; `POST /api/work` returns 422 with a JSON body, not 500.
9. `grep -n "set_field(" tcw/store/base.py` shows no call that precedes a
   `transition`/`_effect_transition` in the same method.
10. Full suite green locally and both CI legs green.

## Risks

- **Changing the signature of an abstract primitive.** `_effect_transition` and
  `transition` both gain a parameter. Only `FsWorkStore` implements the former,
  and no caller outside `base.py` invokes either (`grep -rn "\.transition("` finds
  only `base.py:1329`, `1344`, `1369`, `1421` — the rest are
  `LifecyclePolicy.transition`, a different method). The tests that monkeypatch
  `_effect_transition` with a two-argument replacement
  (`tests/test_external_work_store.py:654`, `698`, `740`) must be updated or they
  fail with a `TypeError` — which is the desired kind of breakage, loud and local.
- **A new window replaces the old one.** Moved-but-not-stamped is reachable if the
  process dies between the two steps. It is narrower, it is on an item this
  process owns, and `validate` reports it — but it is not zero, and criterion 6
  exists so the docstring stops pretending otherwise.
- **Proof-by-monkeypatch, again.** No arrangement of real files reproduces the
  interleaving; the tests exercise the handlers, not the race. Inherited from the
  parent item and accepted for the same reason: the alternative is no test.
- **`tcw work new` can now exit 1 for an item that exists.** Strictly better than
  `AttributeError: 'NoneType'`, but a script that treats non-zero as "nothing was
  created" would be wrong. The message is the mitigation; anything better needs a
  distinct exception type, which is a non-goal.
- **Touching `update_term` and `update_capability` in a work-store bug fix.** Two
  one-line changes, and the sweep rule is repo-wide by default — but they widen
  the diff into two other components. Separable if review objects.

## Notes

- Documentation triggers expected at implement time: `docs/changelogs/upcoming.md`
  (Any-Code-Change) and `docs/release-notes/upcoming.md` (a lost race no longer
  strands a resolution; a losing write path now reports instead of erroring
  opaquely). `README.md` — no CLI surface change. `skills/tcw-work/SKILL.md` — no
  lifecycle, guardrail, or command-surface change.
- The parent item's spec (`docs/work/completed/2026-08-11-harden-effect-transition-against-a-lost-status-transition-race/spec.md`,
  §Design 3) is the direct input; its §Risks entry "the honest framing at closeout
  is 'the loser no longer crashes', not 'the race is handled'" is what this item
  closes.

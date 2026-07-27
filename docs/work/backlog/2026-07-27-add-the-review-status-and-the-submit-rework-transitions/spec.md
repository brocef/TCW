# Specification

Child 1 of [the lifecycle epic](tcw://W/2026-07-27-redefine-the-tcw-work-lifecycle-explicit-stages-transitions-and-hooks).
The epic spec fixes the contract; this one fixes the implementation.

Scope is **the state machine and the model**. Nothing about config, commits,
hooks, or documentation of methodology — those are children 2–4.

## Capability changes

Planned ledger changes only; records are written during implementation.

- **Changed:** `work/start-a-work-item`, `work/complete-a-work-item`,
  `work/view-the-board` — all three learn a fifth status.
- **New:** submit a work item for review; send a reviewed item back for rework.

## Current state

Verified against the code, not assumed:

- `WORK_STATUSES` is a 4-tuple at `tcw/store/base.py:434`; `LEGAL_TRANSITIONS`
  at `:446` holds four forward edges and no reverse edge.
- `transition()` (`base.py:948`) checks the edge and delegates the move to
  `_effect_transition()`, which the FS adapter implements in two lines
  (`fs.py:2183`) as `git_mv`.
- `git_mv` (`fs.py:268`) runs `git mv` directly. **`git mv` fails when the
  destination's parent directory does not exist**, so a `review/` folder that
  was never scaffolded is a hard failure, not a silent one.
- Item discovery globs `self.root / status` for every status (`fs.py:1552`).
  `Path.rglob` on a missing directory yields nothing rather than raising —
  confirmed by execution — so *reading* a node without `review/` is already
  safe. Only the *write* path needs work.
- `RESERVED_PROJECT_IDS` is derived, not literal: `{"t","c","w","local",
  *WORK_STATUSES}` (`store/project.py:16`). Adding a status silently reserves a
  project id.
- `WorkItem.phase` (`base.py:531`) is read at `fs.py:1785` with a default and
  written as `""` at three creation sites (`:2124`, `:2169`, `:2289`). No code
  path ever assigns a non-empty value. It is displayed by `work/cli.py:97` and
  by the reconcile table (`work/recursion.py:127,134`).
- The TypeScript mirror (`web/client/src/model/types.ts:5`) carries a comment
  pointing at `WORK_STATUSES` and nothing that enforces it. `tree.ts:9` holds a
  separate `WORK_STATUS_ORDER` display-precedence map. `tree.test.ts:17`
  already iterates `WORK_STATUSES` to assert the sorter knows every status — so
  the TS side is self-consistent; it is the **Python↔TypeScript** link that is
  unguarded.
- `tcw/serve/` hardcodes no status literal, so the web API needs no change
  beyond the shared model.

## Design

### `review` is an unresolved status

```python
WORK_STATUSES = ("backlog", "active", "review", "completed", "discarded")
RESOLVED_STATUSES = ("completed", "discarded")   # unchanged
```

Ordering within the tuple is presentation-adjacent (`_item_dirs` sorts by path,
`init` scaffolds in order), so `review` is placed after `active` to read in
lifecycle order.

`RESOLVED_STATUSES` deliberately does not change. An item in `review` is not
finished, so it still blocks its dependents, still counts as an open initiative
child, and still appears on the default board.

Four edges are added:

```python
("active", "review"),        # submit
("review", "completed"),     # complete --resolution done
("review", "active"),        # rework
("review", "discarded"),     # complete, any other resolution
```

`(review, discarded)` is not optional flavor: `complete` maps every non-`done`
resolution onto `discarded` via `resolution_status()`, so without that edge an
item in `review` could not be abandoned at all.

### `submit` and `rework`

Both are thin, and deliberately so — `transition()` already owns edge checking.

```python
def submit(self, slug: str) -> WorkItem:
    return self.transition(slug, "review")

def rework(self, slug: str) -> WorkItem:
    ...  # refuses while refined-outcome.md is present
    return self.transition(slug, "active")
```

`submit` carries **no gate**. The epic spec lists `outcome.md` present as a
*soft* check; soft means the agent's judgment, and per the epic's terminology
rule that is not a gate and the CLI must not refuse on it. It is not
`[prompted]` either, because nothing here obliges the CLI to emit a reminder.

`rework` **fails closed while `refined-outcome.md` exists**. That artifact
asserts the work was verified; after a rejection the assertion is false. TCW
does not delete it — deleting a user's document to unblock a transition is the
wrong shape — so the refusal names the file and the required action:

```
tcw work: cannot rework <slug>: refined-outcome.md still asserts this work was
verified. Delete it (and write rework.md describing what remains) before
sending the item back.
```

The check asks the store for the artifact through `artifacts(slug)`, which is
the bounded registry accessor, **not** a direct path probe. That keeps the gate
in the model where a Jira adapter could honor it by looking up its own
equivalent attachment.

**`rework` is the only transition this file gates.** `complete` from `review`
is unaffected by it, on either resolution. A present `refined-outcome.md` says
verification happened and passed, which is precisely the normal path into
`complete --resolution done`; and abandoning verified work as `wontfix` is a
legitimate decision, not a contradiction. Only `rework` — which asserts the
opposite of what the file says — conflicts with it.

### `complete` from `review`

`complete` remains **one** transition with two legal sources. The legal-edge
check at `base.py:1000` needs no change beyond the new edges. The compressed
`active → completed` path keeps working, and gains a warning:

```
tcw work: completing <slug> directly from active; the verify stage was skipped
```

Written to stderr by the CLI, exit status unchanged. Per the epic's execution
model this is `[prompted]`, which in that vocabulary means **the tool is
obliged to emit a reminder and the caller may ignore it** — it does not mean an
interactive prompt. Concretely: no `[y/N]`, no second `--confirm`, no extra
input read, and no change to exit status. `complete` succeeds whether or not
anyone reads the line. `[prompted]` is worth distinguishing from `[judgment]`
only because it puts a testable obligation on the CLI, which is why it appears
in the acceptance criteria at all.

**Placement:** the warning is emitted by `work/cli.py`, not by
`WorkStore.complete()`. The store is a library; a Jira adapter has no stderr and
the web API at `tcw/serve/` would have nowhere to put the text. Advisory output
is a CLI concern. `complete()`'s signature and behavior are untouched.

### The `pr` field

`pr: str = ""` on `WorkItem`, beside `worktree` and `branch`, which it belongs
with — all three record where an item's code lives. Persisted in `state.yaml`,
settable via `tcw work edit --pr <url>`, shown by `show` when non-empty.

Nothing consumes it in this child. It is the durable place for a pull-request
URL so that child 2's `complete --already-integrated` and any future verify-stage
tooling have a field to read rather than a convention to guess. Adding it here
costs one field and avoids a second `state.yaml` shape change.

### Deleting `phase`

Removed entirely: the dataclass field, the read at `fs.py:1785`, the three
`"phase": ""` writes, the `show` line, and the reconcile column.

**This is a no-op migration and the child must prove it.** Every existing
`state.yaml` carries `phase: ""` — verified across the repo's own 60+ items —
and no code path writes anything else, so no information is lost. Removal is
safe in both directions:

- *Old file, new code:* the loader builds `WorkItem` from named keys and ignores
  unknown ones, so a lingering `phase:` key is dropped on the next write.
- *New file, old code:* `fs.py:1785` read it with a `.get("phase", "")` default,
  so a downgrade would not crash either.

The reconcile table loses its column rather than blanking it. A column that is
`-` on every row of every rollup is worse than no column: it implies a fact
exists and is merely unset.

### Lazy `review/` creation

`init` scaffolds from `WORK_STATUSES`, so new nodes get `review/` for free.
Existing nodes do not, and `git mv` will not create it.

Fix in the FS adapter's `_effect_transition`, which is the one place that knows
a destination folder is about to be needed:

```python
def _effect_transition(self, slug: str, to_status: str) -> None:
    (self.root / to_status).mkdir(parents=True, exist_ok=True)
    self._mv(self._find(slug), self.root / to_status / slug)
```

This is an **adapter detail, not a model operation** — "make sure a directory
exists" has no abstract analog, and per the prime directive belongs exactly
here. It also covers every status, not just `review`, which makes the adapter
robust against a hand-deleted folder rather than special-casing one upgrade.

No `.gitkeep` is written: the folder is immediately non-empty because the item
lands in it. An empty `review/` is not needed and would only add a file to
every node.

### The parity guard

The named deliverable of this child, and the only guard that does not exist
today.

`tests/test_status_parity.py` reads `WORK_STATUSES` from
`web/client/src/model/types.ts` by regex and asserts set equality with the
Python tuple. Python-side, so it runs in the normal `pytest` sweep with no
Node.js toolchain required — a TS-side test would only run when someone runs
the web suite, and the failure mode being guarded is a Python change that
forgets the mirror.

It must be demonstrated to fail: the test is worthless unless removing `review`
from either side turns it red. That demonstration is part of this child's
verification, not an implementation detail.

`WORK_STATUS_ORDER` in `tree.ts` gains `review` at index 1 (after `active`,
before `backlog`), matching the lifecycle-progress ordering the map already
uses. `tree.test.ts` already asserts the map covers every status, so that half
is self-guarding once `types.ts` is updated.

## Out of scope

Stated because each is adjacent enough to drift in:

- Auto-committing the `submit` / `rework` moves — child 2.
- Any `work.lifecycle` configuration or hook binding — child 2.
- What `rework.md` and `post-mortem.md` must *contain* — child 4. This child
  only adds the names to `WORK_ARTIFACTS` so the files are addressable.
- Documenting the new transitions in `skills/tcw-work/` beyond the minimum
  needed to keep the shipped docs accurate — child 4 restructures them.
- Any change to `verify`-stage behavior or the `tcw-verifier` agent.

## Acceptance criteria

Each is checkable; none is prose.

1. An item traverses `active → review → active → review → completed`.
2. `tcw work submit` on a `backlog` item raises `IllegalTransition`.
3. `tcw work rework` refuses while `refined-outcome.md` is present, names the
   file, and leaves the item in `review`; it succeeds once the file is gone.
4. `tcw work complete --resolution done` works from `review`.
5. `tcw work complete --resolution wontfix` works from `review` → `discarded`.
6. `complete` from `active` still succeeds and writes the verify-skipped warning
   to stderr; completing from `review` does not.
7. An item in `review` still blocks a dependent's `start`, and still holds its
   epic open.
8. A node whose `docs/work/` has no `review/` folder accepts a `submit` and
   creates the folder; a node whose folder was hand-deleted behaves the same for
   any status.
9. An item whose `state.yaml` still contains `phase:` loads without error, and
   the key is absent after the next write.
10. `grep -rn phase` over `tcw/` and `web/client/src/` returns no work-model hit.
11. `tests/test_status_parity.py` passes as shipped and fails when either
    status list is edited alone.
12. `tcw work edit --pr <url>` round-trips through `state.yaml` and `show`.
13. A node configured with project id `review` fails validation with a message
    naming the collision.
14. `tcw validate` passes on this repo.
15. README, release notes, changelog, and `skills/tcw-work/SKILL.md` describe
    `submit`, `rework`, and the `review` status.

## Risks

- **`review` becomes a reserved project id** the moment `WORK_STATUSES` grows,
  via the derived `RESERVED_PROJECT_IDS`. No node in this repo uses it, but a
  consumer might, and their failure would surface as a confusing validation
  error at upgrade time rather than at configuration time. Criterion 13 requires
  the message to name the collision. This is the only genuinely breaking change
  in the child and belongs in the release notes.
- **Status-set changes ripple wider than the constant.** `_item_dirs`,
  `init` scaffolding, status-path locators (`fs.py:212`), and the qualifier
  guard (`fs.py:246`) all read `WORK_STATUSES`. All are derived and should
  absorb the change for free — but "should" is why criteria 1 and 8 exercise
  paths rather than inspect the constant.
- **The parity test is a regex over another language's source.** It is coarse,
  and it breaks if `types.ts` is reformatted. That is the accepted cost of not
  requiring Node.js in the Python suite; the failure is loud and the fix is
  obvious.

## Notes

`RESOLVED_STATUSES` staying a 2-tuple is the decision most likely to be
second-guessed later, so the reasoning is recorded here: `review` means "work
finished, acceptance pending". Treating it as resolved would let a dependent
start against work that verification may yet reject, which is the exact failure
the `rework` edge exists to make representable.

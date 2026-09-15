# Spec: Flag / auto-advance an epic as completable when all children resolve

Source: GitHub #2. Work-axis (epic coordination) change; no web surface.

## Capability changes

- **Changed:** `work/complete-a-work-item` — an epic whose initiative-children are
  all resolved can be completed **directly from `backlog`** (no "start just to
  complete" dance), and `reconcile` can auto-complete it behind a flag. Body
  updated at completion.
- **Changed:** `work/view-the-board` — `tcw work list` annotates a completable epic
  row as `ready-to-close`.

Recorded in this item's `capabilities.yaml`. (No dedicated reconcile capability
exists in the ledger; the rollup enhancement rides under the epic story.)

## Problem

When an epic's `initiative`-children all reach `completed`, the epic doesn't
advance — it sits where it was (often `backlog`), so the board shows finished
coordination as pending. To close it you must `start` the epic into `active`
purely so `complete` (which refuses from `backlog`) will run. Separately, the
`<!-- tcw:rollup -->` "Next:" line can read "all blocked or complete" while the
completable state isn't called out, and its signal must not diverge from the
`complete` blocker/children gate.

Current mechanics (read):
- `WorkStore.complete` (`base.py:841`) refuses unless `(status,"completed")` is a
  legal transition — i.e. only from `active`; and for `type == "epic"` refuses if
  any `initiative_children` is not `completed`.
- `FsWorkStore.initiative_children` (`fs.py:1525`) already scans **this node +
  child nodes** — the cross-node source of truth.
- `reconcile`/`_render` (`recursion.py:70,92`) writes the rollup; `_tasks_for`
  scans the same cross-node set.
- `_render_board`/`emit` (`work/cli.py`) prints board rows with a blocked-by suffix.

## Goal

1. **Flag completable** — `reconcile` and `list` surface an epic whose children are
   all resolved as "ready to close," printing the exact `complete` command.
2. **Complete from backlog** — allow `tcw work complete <epic>` directly from
   `backlog` when the epic is completable, so coordinator epics that never had
   their own spec/plan don't need a throwaway `start`.
3. **Opt-in auto-complete** — `tcw work reconcile <epic> --complete-when-ready`
   completes a ready epic after writing the rollup.
4. **One source of truth** — the completable signal uses the same cross-node
   `initiative_children` the `complete` gate uses, so rollup and gate can't disagree.

## Decisions (locked)

- **Predicate:** `WorkStore.epic_completable(item) -> bool` (concrete, base) =
  `item.type == "epic"` **and** `item.status != "completed"` **and** it has ≥1
  `initiative_children` **and** all of them are `completed`. Requiring ≥1 child
  means a brand-new empty coordinator epic is **not** flagged (nothing resolved
  yet). Built on `initiative_children`, so it's cross-node by construction and
  any adapter with that relation gets it (litmus: passes).
- **Complete-from-backlog** is gated *only* by completability — no new flag. A
  non-epic, or a non-completable epic, still cannot complete from `backlog`.
  `--force` does not relax the from-backlog rule (it overrides blockers, not
  state-machine legality — unchanged).
- **Auto-complete** is opt-in (`reconcile --complete-when-ready`); it runs the
  normal `complete` (DoD ack auto-supplied, capabilities gate still enforced), so
  it can't bypass a `Missing` declared capability.
- **No global transition change:** `(backlog, completed)` is *not* added to
  `LEGAL_TRANSITIONS` (that would let any item skip `active`). The
  completable-epic case is a scoped exception inside `complete`.

## Proposed behavior

### `tcw/store/base.py`

- `epic_completable(self, item: WorkItem) -> bool` as above (concrete).
- `complete(...)`: compute `completable = item.type == "epic" and
  self.epic_completable(item)`. Permit the completion when
  `(item.status, "completed")` is legal **or** (`item.status == "backlog"` and
  `completable`). When taking the backlog exception, effect the move via
  `_effect_transition` directly (bypassing `transition()`'s own legality check).
  The existing open-children and blocker gates stay.

### `tcw/work/recursion.py`

- `reconcile(node_root, epic_slug, commit=False, complete_when_ready=False)`:
  after rendering, compute `store.epic_completable(epic_item)`; when true and
  `complete_when_ready`, run `store.complete(epic_slug, "done",
  store.dod_checklist())` and note it. `_render` emits, when completable, a
  `**Ready to close:** all N children resolved — run \`tcw work complete <epic>
  --resolution done --confirm\`` line (replacing the generic "all blocked or
  complete" tail for that case).

### `tcw/work/cli.py`

- `_render_board`/`emit`: append ` | ready-to-close` to a row when
  `st.epic_completable(it)` (only evaluated for `type == "epic"` items).
- `reconcile` subparser: add `--complete-when-ready` (auto-complete a ready epic).

## Affected surfaces

- `tcw/store/base.py` — `epic_completable`; `complete` backlog exception.
- `tcw/work/recursion.py` — `reconcile` flag + "Ready to close" rollup line.
- `tcw/work/cli.py` — board annotation; `reconcile --complete-when-ready`.

## Acceptance criteria

1. Epic with ≥1 child, all `completed`: `list` shows `ready-to-close` on the epic
   row; `reconcile` rollup shows "Ready to close" + the exact `complete` command.
2. `tcw work complete <epic> --resolution done --confirm` succeeds from `backlog`
   for a completable epic (DoD gate still applies); the epic moves to `completed`.
3. Complete-from-backlog is still refused for (a) a non-epic, (b) an epic with an
   open child, (c) an epic with zero children.
4. `reconcile --complete-when-ready` completes a ready epic; is a no-op (rollup
   only) when the epic isn't ready.
5. Cross-node: an epic with an open child in a **descendant** node is not flagged
   completable, and `complete`-from-backlog is refused — rollup and gate agree.
6. Existing tests pass; new tests cover the predicate, complete-from-backlog
   (allow + the three refusals), the reconcile flag, and the cross-node case.

## Risks / open items

- `epic_completable` calls `initiative_children`, which shells git per child dir;
  the board evaluates it only for `type == "epic"` rows (few), so cost is bounded.
  Note the ceiling; revisit only if epic counts explode.
- Auto-complete supplies the DoD ack automatically — acceptable because the
  capabilities gate and blocker gate still run; documented as an opt-in shortcut
  for coordinator epics.

## Documentation sync (expected)

- `README.md` [Public-API] — epic complete-from-backlog + `reconcile
  --complete-when-ready` + the `ready-to-close` board marker.
- `docs/release-notes/upcoming.md` — "epics close themselves when their children
  are done."
- `docs/changelogs/upcoming.md` — Added/Changed entries.
- `skills/tcw-work/SKILL.md` [Skill-Driven-Component] — epic lifecycle: completable
  flag, complete-from-backlog, `--complete-when-ready`.

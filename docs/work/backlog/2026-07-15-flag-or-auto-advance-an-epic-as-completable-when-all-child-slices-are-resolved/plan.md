# Plan: flag / auto-advance a completable epic

Derived from `spec.md`. Work-axis, TDD. Single-threaded (`base.py` predicate is the
barrier; reconcile + CLI build on it).

## Phase 1 — predicate + complete-from-backlog (`tcw/store/base.py`)

1. `epic_completable(self, item: WorkItem) -> bool` (concrete, near `board`):
   `item.type == "epic"` and `item.status != "completed"` and
   `children = self.initiative_children(item.slug)` non-empty and every child
   `status == "completed"`.
2. `complete(...)`: after `_require`, compute
   `completable = item.type == "epic" and self.epic_completable(item)`.
   Replace the hard `(status,"completed") not in LEGAL_TRANSITIONS` refusal with:
   allow when legal **or** (`status == "backlog"` and `completable`). Keep the
   open-children + blocker gates. When taking the backlog exception, effect the
   move with `self._effect_transition(slug, "completed")` directly (bypassing
   `transition()`'s own legality check); otherwise keep `self.transition(...)`.

**Verify:** `pytest tests/ -k "epic and (completable or complete)"`;
`python -c "import tcw.store.base"`.

## Phase 2 — reconcile flag + rollup line (`tcw/work/recursion.py`)

1. `reconcile(node_root, epic_slug, commit=False, complete_when_ready=False)`:
   resolve the epic item, compute `completable = store.epic_completable(epic)`,
   pass it into `_render`. When `complete_when_ready and completable`, after the
   rollup write run `store.complete(epic_slug, "done", store.dod_checklist())`
   and append a note to the returned block ("auto-completed").
2. `_render(epic_slug, tasks, completable=False)`: when `completable`, replace the
   `**Next:** all blocked or complete` tail with
   `**Ready to close:** all N children resolved — run \`tcw work complete
   <epic> --resolution done --confirm\``.

**Verify:** `pytest tests/ -k "reconcile"`.

## Phase 3 — CLI (`tcw/work/cli.py`)

1. `_render_board`/`emit`: `ready = " | ready-to-close" if it.type == "epic" and
   st.epic_completable(it) else ""` appended to the row (compose with the existing
   blocked-by suffix).
2. `reconcile` subparser: add `--complete-when-ready` (`action="store_true"`);
   `_reconcile` passes it through and, on auto-complete, prints/commits as today.

**Verify:** `pytest tests/ -k "cli and (reconcile or board or epic)"`; manual:
epic + resolved child → `list` shows `ready-to-close`; `complete` from backlog works.

## Phase 4 — capability + docs

- Update `docs/capabilities/work/complete-a-work-item/description.md` (epic
  complete-from-backlog + auto-complete) and `work/view-the-board`
  (`ready-to-close` marker) at completion; record `changed:` in `capabilities.yaml`.
- `README.md`, `docs/release-notes/upcoming.md`, `docs/changelogs/upcoming.md`,
  `skills/tcw-work/SKILL.md` per spec.

## Tests (`tests/test_recursion.py` + a new `tests/test_epic_completable.py`)

Mirror `mk_node`/child-node fixtures:
- `epic_completable` true/false: all-children-completed, an open child, zero
  children, a non-epic, an already-completed epic;
- complete-from-backlog: allowed for a completable epic; refused for a non-epic,
  an epic with an open child, an empty epic (criteria 2–3);
- `reconcile --complete-when-ready` completes / no-ops (criterion 4);
- cross-node: open child in a descendant node → not completable, complete refused
  (criterion 5);
- rollup renders the "Ready to close" line when completable.

## Verification (full)

- `pytest` green; `tcw validate` + `tcw capabilities check` clean.
- Manual: build an epic + child, complete the child, confirm `list`
  `ready-to-close`, `reconcile` rollup line, and `complete` straight from backlog;
  test `--complete-when-ready`.

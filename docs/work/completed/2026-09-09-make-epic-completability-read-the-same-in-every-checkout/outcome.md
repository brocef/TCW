# Outcome — Make epic completability read the same in every checkout

## What changed

- **The record names the epic.** `Tombstone.initiative`, written when an item
  is resolved and kept by retention deletion (and its retry), nested items, and
  `tombstone add` (from the item where it is still present).
- **`WorkStore.resolved_initiative_children(epic)`** → `(node, slug)` of
  children known only from their record. Default `[]`; `FsWorkStore` reads the
  graveyard of this node and every node below, a present item winning.
- `epic_children_all_resolved` counts them, so an epic whose children are all
  resolved and absent can close from `backlog`, and shows `ready-to-close` in
  `list`; `check_type_change` counts them, so such an epic cannot be demoted.
- **`incomplete_graph_note(below=True)`** — only missing projects declared as
  children here or below. Used by `epic_completable`, `complete`'s epic gate
  and `check_type_change`; `start` keeps the full note.
- `update_work` refuses to change a resolved item's `initiative`.
- `reconcile` lists record-only children (`node | slug | completed | -`) and
  counts them in "Ready to close".
- Docs: the `Tombstone` docstring, `skills/work/references/epic-deltas.md`
  (recovery for records that predate the field), `docs/guide/work.md`, the
  `work/coordinate-a-cross-node-epic` capability (declared `changed`),
  changelog, release notes.
- Tests: `tests/test_epic_completability_across_checkouts.py` (17). Against
  the code before this item, 12 fail and 5 pass — the four "must stay not
  completable" cases and the present-child reconcile count, which should pass on
  both; the retention test fails if deletion drops the field.

## Verification

- By hand, with a real `git clone`: in the clone (no `completed/` folder) the
  epic shows `ready-to-close` and completes from `backlog`. With the record's
  epic removed (an old record), the epic refuses from `backlog` with or without
  `--force`, and `start` then `complete` (no `--force`) closes it — as
  documented.
- Full suite: see the verify notes.

## Autonomous decisions

- **Rollup, grow the record, or read the retained commit?** Codex and Opus:
  grow the record. The rollup erases itself — `reconcile` rebuilds it from a
  live query, so the first run in a clone without the folders overwrites it
  with "No tasks…" (Opus) — and is written only on demand; reading the retained
  commit is git-only and misses gitignored completions. Taken.
- **Where it counts** — both: `epic_children_all_resolved`,
  `check_type_change`, `reconcile`'s table; not `open_descendants`. Pairs, not
  bare slugs, and the present item wins (Opus). Taken.
- **Old records** — both: leave them; no backfill from history. Codex: `--force`
  does not reach the backlog rule, so recovery must be documented. Documented
  (start, then complete).
- **Missing parent** — both: a descendant-only note, keeping the full note for
  `start`. Opus proposed a `relation` field on `UnreachableProject`; the
  registry already answers "declared as a child by whom", so the filter uses
  that and no field was added (spec amended).
- **Editing a resolved child's epic** — the spec said keep the record in step;
  refused instead, because the rewrite would leave the graveyard dirty and the
  next resolution refuses a dirty graveyard (spec amended).
- **Review, accepted**: `tombstone add` never recorded the epic (fixed; test);
  demotion advice pointed at the now-refused edit (fixed; test); recovery docs
  asked for an unneeded `--force` (fixed; checked through the CLI); spec and
  plan brought in line with the code.
- **Review, separate change**: epics matched by slug alone across nodes —
  filed as `2026-09-27-match-an-epic-s-children-by-the-epic-s-node-as-well-as-its-slug`.
- **Verifier, accepted**: `work/reconcile-an-epic-rollup` also changed (its
  rollup lists record-only children) — described and declared; the changelog
  names the new rollup rows; stale test counts and a leftover spec line fixed.
- **Rejected**: none.

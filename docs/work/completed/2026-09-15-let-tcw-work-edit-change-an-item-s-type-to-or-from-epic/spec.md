# Spec: Let tcw work edit change an item's type to or from epic

## Capability changes

- **changed:** `work/coordinate-a-cross-node-epic` — an existing item can be made an
  epic with `tcw work edit <slug> --type epic`, and an epic made plain again with
  `--type ""`, which refuses while any item names it as its initiative or while
  part of the project graph is out of reach.
- **changed:** `work/require-tracker-backed-work` — under strict mode,
  `tcw work edit --type` refuses, because the type decides which ticket gates apply.

## Problem

`tcw work new --epic` (`tcw/work/cli.py:432`) is the only supported way to set
`type: epic`. `tcw work edit` (`tcw/work/cli.py:1946-1993`, parser `:3215-3234`)
has no type option, and `WorkStore.update_work` (`tcw/store/base.py:3115-3136`,
filesystem `tcw/store/fs.py:6278`) has no `type` keyword. An item that turns out to
be an initiative must be recreated under a new slug, left plain, or hand-edited —
the last being what the skills tell agents never to do.

What the type decides today:

- the epic completion shortcut and `ready-to-close` (`epic_children_all_resolved`,
  `tcw/store/base.py:3345-3363`; board `tcw/work/cli.py:541`) and board grouping of
  `initiative:` children under their epic (`tcw/work/cli.py:611`);
- the completion gate over open initiative children and an unreachable project
  graph (`tcw/store/base.py:3500-3520`);
- **strict tracker mode**: `new` allows `--epic` without a ticket but refuses a
  plain item (`tcw/work/cli.py:417`); `_strict_refusal` exempts epics from
  submit/rework/complete gating (`:356-362`); `start` skips the claim for an epic
  (`:1007`); the web app mirrors this (`tcw/serve/__init__.py:215-231`).

So a type change under strict mode is not a descriptive edit. Promotion lifts an
item's ticket gates; demotion produces a plain item with no ticket, which `new`
refuses to create.

`initiative_children` in the filesystem store includes descendant projects
(`tcw/store/fs.py:5116-5128`); `incomplete_graph_note()` (`:5075`) reports projects
this checkout cannot reach.

## Goals

- `tcw work edit <slug> --type epic` promotes; `--type ""` demotes.
- `update_work` accepts `type`, validated like `create_work`'s
  (`tcw/store/fs.py:6200-6201`: only `""` or `"epic"`).
- Demotion never orphans a child and never decides that from a partial graph.
- Strict mode cannot be bypassed by a type change.

## Non-goals

- The web app. Its field whitelist (`tcw/serve/__init__.py:1112-1120`) already
  rejects `type` with 400 "unknown work field", which fails closed.
- Rules for promoting resolved items, items that are themselves initiative or
  nested children: none exists for other edits, `create_work` accepts
  `--epic --initiative/--parent`, and no code path depends on it.
- Reassigning or clearing children's `initiative:` as part of a demotion.
- A `--force` for the demotion refusals.

## Design

**Store contract.** `update_work` gains `type: Any = _UNSET`. The abstract docstring
states: `""` or `"epic"`, anything else `ValueError`; changing `epic` → `""` raises
`ValueError` when `initiative_children(slug)` is non-empty (any status — a resolved
child still points at the epic, and an epic whose children are all resolved should
be completed), or when `incomplete_graph_note()` is non-empty. Setting the type the
item already has is not a change and runs no check. Both checks run before any write.
Storage-neutral: `type` is an ordinary field, `initiative_children` and
`incomplete_graph_note` are abstract relation queries. Litmus: a tracker adapter
can set an issue type field and query children — yes.

The validation is a concrete helper on `WorkStore` (`_check_type_change(item,
new_type)`) so every adapter applies the same rule; `FsWorkStore.update_work` calls
it with the other pre-write validation.

**CLI.** `tcw work edit` gains `--type {epic,""}` (help: `set the item type: "epic",
or "" for a plain item`). `_edit`:

1. under `st.tracker_strict()`, refuses any `--type` through `_strict_says_no`,
   saying promotion would lift the item's ticket gates and demotion would leave a
   plain item with no ticket, and pointing at `tcw work new --epic`;
2. runs the type check **before** the blocker writes, which today happen before
   `update_work` (`tcw/work/cli.py:1972-1979`), so a refused type change changes
   nothing at all;
3. passes `type` to `update_work`.

## Acceptance criteria

1. `tcw work edit <plain> --type epic` exits 0 and `tcw work show` reports
   `type: epic`; `--type ""` on a childless epic exits 0 and the type is plain.
2. `update_work(slug, type="story")` raises `ValueError` and writes nothing.
3. Demoting an epic with one initiative child — open, and separately one that is
   completed — refuses with a message naming the child, exit 1, and the item stays
   `epic`.
4. Demoting an epic whose child lives in a descendant project refuses.
5. Demoting an epic when `incomplete_graph_note()` is non-empty refuses and says
   which projects are missing.
6. `tcw work edit <epic-with-child> --type "" --blocked-by other --title New`
   exits 1 and changes neither blockers nor title.
7. Under strict mode, `tcw work edit <slug> --type epic` and `--type ""` exit 1 and
   leave the type unchanged; the refusal names `tcw work new --epic`.
8. After promotion, an item whose `initiative:` names it is grouped under it on
   `tcw work list --include-descendants` (the only board view that groups), and it is `ready-to-close` once that child is resolved.
9. The full suite passes.

## Risks

- The strict refusal is coarse: it also refuses a harmless promotion of a backlog
  item never bound to a ticket. Accepted — that set is nearly empty under strict
  mode, since plain items there come from `tracker import`.
- A store adapter overriding `update_work` without calling the helper would skip the
  rule; the abstract docstring names the rule so an implementer sees it.

## Notes

Design questions settled by the advisors (see `outcome.md`, "Autonomous decisions"):
strict mode refuses outright; any child blocks demotion; a partial graph blocks
demotion; resolved items get no special rule.

# Make drop and its discard advice account for a parent's children

## Capability changes

None. `drop` still refuses the same items, and discarding is unchanged. Only the
point at which a refusal is shown and what it advises change.

## Problem

Two v2.5.1 changes meet in `_drop` (tcw/work/cli.py ~3818-3860):

- The drop-refusal fix refuses a non-backlog item before the `--confirm` gate and
  advises `tcw work complete <slug> --resolution wontfix --confirm`.
- Children with their own status make `WorkStore.drop` (tcw/store/base.py ~3996)
  refuse while any independent descendant exists, open or resolved. They also
  make `complete` refuse, for either resolution, while any descendant is open
  (`open_descendants`, base.py ~3670).

The result: (1) a backlog parent with a child is told "Would delete …", then
refused after `--confirm`. (2) An active or review parent with an open child is
advised to run a discard that `complete` refuses. And the store's message says
"Drop, discard or re-parent them first" even when every child is already resolved,
when neither dropping nor discarding them can work and the CLI has no re-parent
verb.

Separately, `tcw work new --parent`'s help (cli.py:4235) still says "create as a
child nested under this item's slug".

## Goals

1. A backlog item with independent descendants is refused before the `--confirm`
   gate, naming them. No "Would delete" line.
2. The refusal advises dropping or discarding the children only if some are open.
   When all are resolved, it advises discarding the parent instead
   (`tcw work complete <slug> --resolution wontfix --confirm`). Resolved items can
   be neither dropped nor discarded, the CLI has no re-parent verb, and a discard
   keeps the record the children's `parent:` names.
3. An active or review item with open descendants gets the discard advice plus
   the open children's names, which must be finished or discarded first.
4. `--parent` help describes a child as an item recording its parent.

## Non-goals

Changing what `drop` or `complete` refuse. The web API. Findings 4–6 of the
combined review (filed separately).

## Design

In `_drop`, after the existing status block, for a backlog item:
`beneath = st.independent_descendants(bare)`. If non-empty, print one line,
`tcw work drop: <slug> cannot be dropped; these items name it as their parent:
<slugs>. …advice…`, and return 1 before the `--confirm` gate. The store's own
refusal message gets the same open/resolved distinction, since the web API
reaches it directly. In the non-backlog branch, `open_descendants(bare)` non-empty
appends "First complete or discard the items still open beneath it: <slugs>."

## Acceptance criteria

1. A backlog parent with a backlog child: `tcw work drop <parent>` (no `--confirm`)
   exits 1. stderr names the child and contains no "Would delete". Nothing is
   deleted.
2. The same with every child resolved: stderr names the discard command for the
   parent, does not say "Drop, discard", and that command succeeds.
3. An active parent with an open child: `tcw work drop <parent>` exits 1 and stderr
   contains both the `tcw work complete <parent> --resolution wontfix --confirm`
   advice and the child's slug.
4. `tcw work new --help` no longer contains "nested under".
5. The existing drop tests and tests/test_child_status.py pass.

## Risks

`independent_descendants` walks the whole board. That's one read, the same walk
`st.drop` already does.

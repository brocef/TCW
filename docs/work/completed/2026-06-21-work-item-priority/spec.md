# Spec — Work item priority

## Goal

A work item can carry an **integer priority** (higher int = higher priority).
Settable at creation and via `edit`. Default is **unspecified** (`None`).

## Behavior

- `tcw work new "<title>" --priority N` — create with priority `N`.
- `tcw work edit <slug> --priority N` — set/replace priority on an existing item.
- Default unspecified: items with no priority keep creation order.
- `tcw work list` (the board): specified-priority items sort **above**
  unspecified ones, descending by integer; unspecified items keep creation
  order among themselves.

## Ordering decision (board × blockers)

Priority does not replace the topological board order — it **feeds** it.
`board()` = `topo_order(priority_order(query()))`: priority sets the input
order, the existing stable topo sort then guarantees a blocker still precedes
what it blocks. A soft preference (priority) never overrides a hard constraint
(you cannot do a blocked item before its blocker). No priorities set →
`priority_order` is identity → existing order/tests unchanged.

## Model / litmus

`priority: int | None` on `WorkItem` + the abstract `WorkStore` (creation arg).
Passes the litmus test — Jira et al. have a native priority field, so it
belongs in the model, not the FS adapter. `FsWorkStore` persists it in
`state.yaml`; the generic `set_field` path covers `edit` (no new abstract
method). No bounds/validation beyond int parsing (argparse `type=int`);
negatives are legal.

## Capability deltas (recorded for the completion ledger flip)

- **New:** `work#prioritize-a-work-item` — "Prioritize a work item" (Missing → Supported).
- **Changed:** `work#view-the-board` — ordering now honors priority.
- **Changed (surface):** `work#open-a-work-item` gains `--priority`; the edit
  capability gains `--priority`.

Recorded in `capabilities.yaml` (work→capability back-pointer). No semantic
contradiction with the standing ledger (`tcw capabilities search priority` empty).

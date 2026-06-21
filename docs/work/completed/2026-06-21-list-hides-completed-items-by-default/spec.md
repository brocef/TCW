# Spec — List hides completed items by default

## Behavior

- `tcw work list` (no `--status`) → live columns only: inbox, backlog, active.
  `completed` items are hidden.
- `tcw work list --status <s>` → exactly that status (so `--status completed`
  still shows completed items).
- `tcw work list --all` → the full board including completed (the old default).

## Where

CLI presentation only (`_list` in `tcw/work/cli.py`). `board()` / `query()`
keep full semantics — hiding a terminal status is a list default any store
could apply, so it does not belong in the store interface (litmus). Filtering
the board *after* `board()` is safe: a topo edge counts only when both endpoints
are in the set, so dropping completed items can't misorder the rest, and a
completed blocker already reads as resolved.

## Capability delta

- **Changed:** `work#view-the-board` — default scope is now the live columns;
  `--status` / `--all` documented. Recorded in `capabilities.yaml`.

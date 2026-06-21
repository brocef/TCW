# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category, with commit hash ranges so entries trace back to source.

## Added (7df591a..c2eaa51)

- Work items carry an optional integer **priority**. `priority: int | None` on
  `WorkItem` and the abstract `WorkStore.create(...)` (litmus-clean — a remote
  tracker has a native priority field). `FsWorkStore.create` persists it in
  `state.yaml`; `get` reads it; the generic `set_field` path covers edits.
- `priority_order(items)` in `tcw/store/base.py`: stable sort, specified
  priorities (higher int first) above unspecified (creation order preserved).
- CLI: `tcw work new --priority N` and `tcw work edit --priority N` (`type=int`);
  `tcw work show` prints `priority:` when set.

## Changed (7df591a..c2eaa51)

- `WorkStore.board()` is now `topo_order(priority_order(query()))` — priority is
  the input order to the existing stable topological sort, so it sorts the board
  while a blocker still precedes what it blocks. No priorities set → identity.

## Changed (f58af86..531e0e5)

- `tcw work list` hides `completed` items by default (live columns only).
  `--status` is honored as-is (`--status completed` still lists them); new
  `--all` flag re-includes completed. Filtering is in the CLI `_list` layer;
  `WorkStore.board()`/`query()` semantics are unchanged.

## Changed (7772066..693df43)

- `tcw work list` rows gain a **priority** column between `phase` and `title`
  (`slug  status  phase  priority  title`); shows the int or `-` when
  unspecified. CLI presentation only.

## Changed (352b5e6..48b0798)

- `tcw work list` rows are now ` | `-delimited instead of tab-separated
  (`slug | status | phase | priority | title [| blocked-by: …]`), so field
  boundaries are unambiguous. CLI presentation only.

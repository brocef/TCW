# Make the capability gate honor a configured ledger, and keep one bad capabilities.yaml from breaking the board

Two defects in how an item's `capabilities.yaml` reaches the Definition-of-Done
gate:

1. `capability_gate` looked for a literal `docs/capabilities` folder, so a
   ledger moved by `capabilities.path` or kept in another repository was never
   checked.
2. One item's unreadable `capabilities.yaml` — not valid UTF-8, a folder of
   that name — makes `tcw work list` exit 1 with no rows for any item. A small
   hand-written file of nested YAML anchors makes `tcw work show --json` run
   without end.

## Notes

- From the intake (Jira TCW-11), triaged 2026-09-15. Written during an
  unattended run (2026-09-26); no requester to ask. References: asked; none
  beyond the intake.
- Part 1 was fixed on main by commit `61a298b9` (`_open_ledger` in
  `tcw/work/recursion.py`, test `test_a_ledger_at_a_configured_path_is_gated`),
  after this item was filed. This item records that and fixes part 2.

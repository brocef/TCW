# Make the capability gate find a configured ledger and survive an unreadable capabilities.yaml

## What is wanted

An item's capability declarations (`capabilities.yaml`) should be checked by the
completion gate on every node that has a capabilities ledger, and one bad
`capabilities.yaml` should be reported on its own item rather than break anything
else.

1. **The gate ignores a ledger that lives elsewhere.** `capability_gate` in
   `tcw/work/recursion.py` decides whether a node has a ledger by testing for
   `<node root>/docs/capabilities`. A node that sets `capabilities.path`, or keeps
   its ledger in another repository with `capabilities.repository`, fails that test,
   so the gate passes without reading the item's declarations: a `new:` capability
   still `Missing`, a `changed:` path that no longer resolves, or a `removed:` path
   that still exists all go through.
2. **An unreadable `capabilities.yaml` takes down the board.** `FsWorkStore._read_item`
   catches only YAML parse errors. A file that is not valid UTF-8 makes `tcw work list`
   exit 1 with no rows at all; a directory of that name, a file without read
   permission, or deeply nested content should fail the same way. The tracker binding
   already solved this shape by turning each read failure into a problem reported on
   that item, and `capabilities.yaml` already has a parse-error marker the gate treats
   as a failure.

## Constraints

- The gate must still **fail closed** on a declaration it cannot read: an unreadable
  file must not become "no declarations".
- `skills/capabilities/SKILL.md` already says never to build a store path from the
  node root; the fix should follow that rule, not add another hard-coded path.

## Also worth checking

- `_json_safe` in `tcw/work/projection.py` walks a `capabilities` value for
  `show --json`; a chain of YAML anchors could expand exponentially and hang
  `show --json` and `tcw serve`. Not reproduced.

## Notes

- Merged at triage from two inbox entries, because both concern how an item's
  capability declarations reach the Definition-of-Done gate; both kept verbatim in
  `intake.md`.
- Checked at triage on `main`: both defects are present (`recursion.py` tests
  `st.node_root / "docs" / "capabilities"`; `_read_item` catches only
  `yaml.YAMLError` for this file while the neighbouring `tracker.yaml` read catches
  `OSError` and `UnicodeDecodeError`).
- Reference material: asked; none provided.

## References

- `docs/lifecycle/implementation.md` — describes the same "store path composed from
  the node root" mistake for the work store (GitHub issues #15 to #18).

## Added 2026-09-21

From the spec review of
`2026-09-21-let-a-work-item-on-a-board-with-no-capabilities-ledger-declare-deltas-against-its-child-nodes-ledgers`
(autonomous run, advisors Codex and Opus both concurring): **part 1 of this item,
the gate ignoring a ledger set by `capabilities.path` or `capabilities.repository`,
moves to that item.** It has to rewrite the same early return in
`tcw/work/recursion.py` (`capability_gate`'s `<node root>/docs/capabilities` test)
to find child ledgers, and doing it twice would conflict. That item's criteria
cover both configured forms, crediting this item's regression idea.

This item narrows to **part 2**: an unreadable `capabilities.yaml` (not valid UTF-8,
a directory of that name, no read permission, deeply nested content) is reported on
its own item instead of taking down `tcw work list`, and the `_json_safe` check.

## Scope narrowed (2026-09-24 backlog cleanup)

Part 1 (the completion gate finding a ledger configured with `capabilities.path` or `capabilities.repository`) shipped with `2026-09-21-let-a-work-item-on-a-board-with-no-capabilities-ledger-declare-deltas-against-its-child-nodes-ledgers` (commits 6939d75a, f1d4d16e); `capability_gate` now calls `_open_ledger`. What remains is part 2: one unreadable `capabilities.yaml` (not UTF-8, a directory, no read permission) must be reported on its item instead of failing `tcw work list` — the sidecar read in `tcw/store/fs.py` catches only `yaml.YAMLError`. The unreproduced `_json_safe` sub-point is dropped. Title changed to match.

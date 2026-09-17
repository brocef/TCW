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

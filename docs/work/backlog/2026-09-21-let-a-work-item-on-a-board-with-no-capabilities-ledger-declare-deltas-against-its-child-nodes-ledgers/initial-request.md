# Let a work item on a board with no capabilities ledger declare deltas against its child nodes' ledgers

## Request

A work item on a board whose own node has no capabilities ledger, such as
proposit-app's repo-root node, should be able to declare the capability changes it
makes in its child nodes' ledgers. The completion gate should then check them.

The requester chose **node-qualified paths** on 2026-09-21. The item's
`capabilities.yaml` names paths such as `proposit-shared/authoring/x`, and the
completion gate resolves each one through `connected-projects.children` and checks
it against that child's ledger (`new:` exists and is no longer Missing,
`changed:` resolves, `removed:` is gone). Handing each path to the child's own
gate was the alternative, and was not chosen.

## Constraints

- v2.5.1 (the release carrying v2.5.0's contents, whose tag never reached PyPI) is
  held until all five items filed from the proposit-app reports on 2026-09-21 are
  fixed and accepted. This is one of them.

## Notes

- Asked for reference material, deadlines and exclusions on 2026-09-21: none
  beyond the reporter's account in `intake.md` and the related items it names.

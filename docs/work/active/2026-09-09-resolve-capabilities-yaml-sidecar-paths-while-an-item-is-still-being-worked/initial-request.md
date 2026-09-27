# Resolve capabilities.yaml sidecar paths while an item is still being worked

A work item's `capabilities.yaml` names capability paths under `new:`,
`changed:` and `removed:`. A path that does not resolve — the `shared/…`
shorthand is the common case — passes `tcw validate` and `tcw capabilities
check`, and surfaces only at `tcw work complete`, after the sidecar has often
been copied into sibling slices of the same epic. Report such a path, with its
file and line, while the item is still being worked.

**Scope set by the reporter:** never check sidecars of completed (or discarded)
items — they record what was true when they shipped, and checking them would
make `tcw validate` noisier with every completed item.

## Notes

- From GitHub #27 (filed 2026-09-02). Written during an unattended run
  (2026-09-26) from `intake.md`; no requester to ask. References: asked; none
  beyond the intake.
- The intake also floats resolving `shared/` to a unique connected project id.
  Both advisors: a separate item, since it changes resolution for every command.

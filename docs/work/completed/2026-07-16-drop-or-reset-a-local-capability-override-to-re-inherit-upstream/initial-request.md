# Drop or reset a local capability override to re-inherit upstream

Follow-up from `2026-07-15-capabilities-set-rejects-inherited-capability-paths-that-show-list-accept`
(GitHub issue #3). Surfaced by that item's plan review and code review.

## Product changes

That item made `tcw capabilities set <inherited-path>` *create* a local override
for a federated capability. But there is no command to *drop* one and revert to
the upstream value:

- `remove` refuses anything inherited (correctly — it must not imply deleting the
  upstream entry), and an override addresses an inherited path.
- So the only way to revert is deleting the local override folder by hand — the
  same "hand-edit the store" complaint issue #3 set out to eliminate, one level
  down.

Wanted: a first-class way to drop an override. Candidate shapes (decide at
planning):

- `tcw capabilities reset <path>` — remove the local override, re-inherit upstream;
- or `tcw capabilities remove <path> --override` — teach `remove` to target the
  override rather than refusing.

## Constraints / non-goals

- Must never touch the upstream node.
- Must refuse (or no-op clearly) when there is no local override at the path.
- Abstraction litmus: dropping a local delta keyed by upstream id is
  store-implementable (a Jira/graph adapter deletes its own delta record) — belongs
  in the `CapabilitiesStore` interface, not just the FS adapter. Note the existing
  `remove` is already on the interface.

## Open questions

- Single verb (`reset`) vs. a flag on `remove`? Leaning `reset` for clarity, since
  `remove` semantically means "delete a local capability".
- Should it also clear a partial override (drop just a body delta vs. the whole
  override folder)? Probably whole-override only; field-level revert is already
  expressible via `set ... --field K=<inherited value>`.

## Related

- `2026-07-15-capabilities-set-rejects-inherited-capability-paths-that-show-list-accept`
  (the item that created the override-write path).

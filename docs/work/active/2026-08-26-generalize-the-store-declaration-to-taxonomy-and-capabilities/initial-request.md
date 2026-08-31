# Generalize the store declaration to taxonomy and capabilities

## The request

Make the taxonomy and capabilities trees reachable from a machine that has never
seen them, exactly the way the work store now is.

This is child B of
[the store-home-repository initiative](tcw://W/2026-08-26-declare-a-component-store-s-home-repository-so-a-fresh-checkout-can-provision-it).
The requester's original ask covered all three component trees, not the work
store alone — "its work items and their lifecycle artifacts first, and its
taxonomy and capabilities trees as well." Child A delivered the work store and
the unblock it was scoped for. This item is the rest of that sentence.

## Why it is not simply "the same thing again"

The work store already had a configurable location before any of this began:
`work.path` in `tcw-config.yaml`, resolved by `FsWorkStore.open`. Child A's
declaration mechanism was layered onto an existing locator.

Taxonomy and capabilities have no such locator. `FsTreeStore.open` is one line —
`cls(node_root / "docs" / cls.COMPONENT)` (`tcw/store/fs.py:1044-1045`) — and it
takes no configuration at all. So this item carries two user-facing changes
rather than one:

1. **A local path.** `taxonomy.path` and `capabilities.path`, doing for those
   trees what `work.path` already does: keep the tree somewhere other than
   `docs/<component>`, no remote involved. Useful on its own, and required
   anyway, because the resolution ladder's first rule is "the store already
   present here, when it is usable".
2. **A home repository.** The `repository` block from child A, beside those
   paths, resolved by the same ladder and materialized by the same
   `tcw provision`.

## What "done" means

Criterion 4 of the initiative spec: criteria 1-3 hold identically for a declared
taxonomy store and a declared capabilities store. Concretely — an unprovisioned
declared taxonomy store makes `tcw taxonomy list` fail with an actionable message
naming the remote and `tcw provision`; `tcw provision --component taxonomy`
obtains it; a second run contacts nothing. The same for capabilities.

## Decisions taken with the requester

Both were left open by the initiative spec and settled before this item's spec
was written:

- **One Feature, renamed.** `configurable-work-store-location` becomes
  `configurable-component-store-location`, covering all three trees, and the
  existing work capability re-points at it. This matches
  `provisioned-component-stores`, which child A already registered
  component-generically. The alternative — keeping the work Feature and adding a
  sibling for the tree stores — was rejected as two Features describing one
  mechanism.
- **The local path is its own capability.** `taxonomy.path` and
  `capabilities.path` are a real config surface a user can adopt without any
  remote, so they are declared and documented as capabilities in their own right
  rather than left as an undocumented means to the declaration. The initiative
  spec already anticipated this, naming
  `taxonomy/configure-the-taxonomy-store-location` and
  `capabilities/configure-the-capabilities-store-location`.

## Constraints

Inherited from the initiative, and binding here:

- **Declaration and provisioning stay separate.** No command reaches the network
  on its own; only `tcw provision` does, and it says what it will contact first.
- **The CLI carries the requirement**, not a Claude hook — a Codex user must be
  able to finish the same job.
- **A declaration is a fallback, never an override.** A tree already present is
  used untouched, so one config serves a laptop that has it and a checkout that
  does not.
- **Nothing existing may break.** A project with no `taxonomy.path` and no
  `repository` keeps resolving `docs/taxonomy` exactly as it does today.

## Out of scope

- **The provisioning verb's own contract.** `tcw provision`, `--dry-run`,
  `--refresh`, the failure semantics, and where a checkout lands were all settled
  by child A. This item widens `--component` to accept the two new values and
  supplies their adapters; it does not redesign the verb.
- **Publishing writes back to a remote.** That is child C
  ([Publish provisioned-store writes to their remote](tcw://W/2026-08-26-publish-provisioned-store-writes-to-their-remote)),
  and the two are parallel with no dependency between them.

## Notes

- Child A restricted `tcw provision --component` to `work` deliberately, after a
  review found it accepting taxonomy and capabilities while only the work-store
  layout was implemented — a declaration was cloned and then rejected for missing
  work statuses. Widening that tuple is this item's job, and it must arrive
  together with the adapters that make the values honest, not before them.
- A store layout check is what made child A's provisioning safe: the tree stores
  need their own answer to "is this directory actually a taxonomy store?", and it
  will not be the work store's status-folder check.
- Carried forward from child A's verification, as a spec-writing instruction
  rather than a nicety: **state each acceptance criterion as a property, with
  examples as illustration.** Three of five review passes on child A found the
  same defect shape — a criterion written as an enumeration got tested to its
  enumeration and the property went unchecked.

## References

The initiative recorded "asked; none provided — the code is enough", and that
answer stands for this item. The material that matters is in the repository:

- `tcw/store/fs.py` — `FsTreeStore.open` (the seam being lifted, 1044-1045) and
  `FsWorkStore.open` (the resolution ladder to mirror, 2720-2775). _Why:_ this
  item's whole job is making the first look like the second.
- `tcw/store/base.py` — `RepositoryDeclaration`, `StoreProvisioner`,
  `StoreNotProvisioned`, `StoreDeclarationError`. _Why:_ the vocabulary child A
  defined and this item consumes unchanged.
- `tcw/store/fs.py` — `FsStoreProvisioner`. _Why:_ it knows only the work-store
  layout today; the tree stores need theirs added beside it.
- `tests/test_store_provisioning.py` — 74 cases. _Why:_ the shared provisioning
  tests this item extends rather than duplicates.

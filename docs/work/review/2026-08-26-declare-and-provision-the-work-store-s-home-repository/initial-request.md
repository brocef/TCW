# Declare and provision the work store's home repository

## The request

Give a project a way to record, in `tcw-config.yaml`, the **repository** that
holds its work store — and give the CLI an explicit command that fetches it — so
a machine that has only the code checkout can obtain the store instead of
reporting that the project has no work component.

This is child A of
[the store-home-repository epic](tcw://W/2026-08-26-declare-a-component-store-s-home-repository-so-a-fresh-checkout-can-provision-it),
and it is the child that resolves the reported problem on its own. The epic's
spec and plan are the authority on why; this item is the authority on the work
store's half of it.

## What it must deliver

- A declaration beside the existing `work.path` naming the store's home
  repository, portable enough for any machine to act on.
- Resolution precedence in which an existing local store still wins, so a
  checkout that already has the store keeps using it untouched.
- One explicit, idempotent command that materializes declared-but-absent stores,
  defaulting to a per-machine location outside the code checkout.
- Error surfaces that say *declared but not provisioned* — today the reason is
  swallowed and `tcw work list` misdirects the user to `tcw init`.

## Boundaries

- **Does not touch `FsTreeStore.open`.** Taxonomy and capabilities are child B,
  but the seam this item builds must not be work-shaped, because child B consumes
  it.
- **Writes nothing to a remote.** Publishing transitions is child C.
- **Manages no credentials.** Provisioning inherits the environment's Git
  authentication and stores nothing.

## Notes

- No user was asked at this stage, and none needed to be: the request derives
  from the epic's committed plan, whose own `request` stage collected the four
  design constraints (explicit provisioning, configurable checkout target
  defaulting to a cache directory, all three component trees eventually, and
  publication in child C) directly from the requester.
- Anything this item leaves open is a decision for its own `spec`, not a
  question outstanding with the requester.

## References

- `tcw://W/2026-08-26-declare-a-component-store-s-home-repository-so-a-fresh-checkout-can-provision-it`
  — the epic's spec fixes this child's boundary and acceptance criteria; its plan
  names the files expected to change.

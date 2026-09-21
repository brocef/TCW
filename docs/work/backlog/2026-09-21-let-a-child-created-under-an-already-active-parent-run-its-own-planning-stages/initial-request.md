# Let a child created under an already-active parent run its own planning stages

## Request

A `--parent` child created after its parent was started should be able to run its
own request, spec and plan stages, as the decompose procedure's "thin umbrella"
model describes. Today it is born `active` and those gates refuse it.

The requester chose on 2026-09-21: **children get their own status.** A child
created under an active parent starts in `backlog` and moves through the lifecycle
on its own, rather than taking its status from the top-level folder its parent
sits in. The alternatives offered were letting spec/plan run on any active item,
telling the plan stage to create children before `start`, and documenting nested
children as implement-only. The requester did not choose them.

## Constraints

- v2.5.1 (the release carrying v2.5.0's contents, whose tag never reached PyPI) is
  held until all five items filed from the proposit-app reports on 2026-09-21 are
  fixed and accepted. This is one of them.

## Notes

- Asked for reference material, deadlines and exclusions on 2026-09-21: none
  beyond the reporter's account in `intake.md` and the related items it names.
- The requester was told this changes how the work store derives a nested child's
  status (today `_status_of` in `tcw/store/fs.py` reports the top-level status
  folder), and chose it anyway. The abstraction test in
  `docs/lifecycle/abstraction.md` applies: a status per child must be something a
  non-filesystem store could hold too.

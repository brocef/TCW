# Refined outcome: child-qualified capability paths on a board with no ledger

## Decision

**Accepted** on 2026-09-21 in an autonomous run. The requester had authorized the
batch to be finished, self-reviewed, verified and released while they were away. The
verify decision was taken by the coordinating session, on the evidence below.

## Evidence

- Full suite, run as CI runs it (bare `pytest`, no git identity): **3918 passed**
  at `6ab2b1d0`. After the verify fold-ins, the gate tests plus `tests/test_work.py`
  gave 369 passed. The full suite runs again on main after the batch merge, before
  release.
- `tcw:verifier`: 20 of 21 criteria met outright; the remaining two wording gaps
  (C1 remedy naming the child, C12 docstring) were fixed at verify.
- `adversarial-code-reviewer`: DONE. Its one confirmed defect (a malformed
  `meta.yaml` raising `yaml.YAMLError` and blocking a discard) was fixed with a test.
- Hands-on check in a scratch repository (root work board plus child ledger). A
  Missing child capability refused completion, naming the child. An unqualified path
  refused, naming the child to qualify it with. Completion passed once the child
  capability was Supported. `wontfix` only warned.
- Read-only check against the real proposit-app layout (by the implementer):
  child-qualified `changed:` paths passed; a Missing `new:` refused; an unqualified
  path and an unknown prefix refused, listing the three children.

## Capability ledger

The item's `capabilities.yaml` declares the new capability. The gate itself passes
on completion.

## Deferred

- Combined review of `tcw/work/recursion.py` and `tcw/work/cli.py` with the other
  v2.5.1 items: done once all of them are merged, before release.
- No GitHub issue is attached to this item.
- Follow-ups named in `outcome.md` stay out of scope (show/set with child paths,
  #30, #27).

## Closeout

`tcw work complete` merges `work/<slug>` into `main` locally. The push happens with
the v2.5.1 release after the batch's combined verification.

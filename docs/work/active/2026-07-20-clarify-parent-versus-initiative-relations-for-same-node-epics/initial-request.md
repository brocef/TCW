# Clarify parent versus initiative relations for same-node epics

## Product changes

None. This corrects agent-facing lifecycle guidance without changing TCW's
runtime behavior or public CLI surface.

## Technical changes

Clarify the semantic distinction between the two same-node relationships:

- `--parent` decomposes one item into nested pieces that transition together;
  independently transitioning a child intentionally de-nests it.
- `--initiative` relates independently scheduled tasks to an epic and is valid
  within one node as well as across registered nodes; epic reconciliation follows
  this relation.

Update the `tcw-work` router and relevant epic/decomposition references so they
route by scheduling semantics rather than repository locality. Preserve the
existing CLI behavior; `edit --parent` and broader reconciliation changes are
out of scope.

## Meta changes

Origin: GitHub issue https://github.com/brocef/TCW/issues/6. The user approved
addressing this documentation issue after repository issue triage and deferred
the separate capability-first lifecycle proposal in issue #5.

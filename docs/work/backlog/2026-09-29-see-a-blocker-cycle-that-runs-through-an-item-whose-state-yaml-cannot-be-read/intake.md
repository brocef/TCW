# See a blocker cycle that runs through an item whose state.yaml cannot be read

From the combined review of branch `bug-run` (2026-09-29). This was left out of
`2026-09-29-keep-a-child-whose-state-yaml-cannot-be-read-visible-to-its-parent-s-completion-gate`.

The board reads a damaged `state.yaml` as `{}` (`FsWorkStore._safe_yaml`),
which leaves the damaged item with `blocked_by: []`. When a new blocker edge
is checked for cycles (`_reaches`), the check cannot follow edges through
that item, so a cycle that runs through it is not reported. Nothing resolves
wrongly because of this: `start` still refuses the damaged item itself
through `_require_readable_state`. The cycle only shows up once the file is
fixed.

Wanted: a blocker edit whose cycle check passes through an unreadable item
should say so, rather than accept the edit silently.

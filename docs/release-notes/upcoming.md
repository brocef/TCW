# Upcoming

User-facing release notes for the next version. Plain language — no jargon or
internal module names.

## New

- **Undo a capability override.** After overriding a capability inherited from
  another project, you can now revert it to the upstream value with
  `tcw capabilities reset <path>` — no more hand-deleting files. It only removes
  your local override (never the other project's copy) and tells you clearly when
  there's nothing to undo.

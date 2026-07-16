# Upcoming

User-facing release notes for the next version. Plain language — no jargon or
internal module names.

- Finishing a work item now checks that the capabilities you said it would change
  were actually updated. If you declared a new capability and left it marked
  "Missing", `tcw work complete` stops and tells you which one — so shipped work
  can't quietly leave the capability list out of date. Flip it, mark it as
  deliberately not built, or force past the check with a note. (Work done on a
  separate branch is checked after it merges back, so branch-side updates count.)
- New `tcw capabilities drift` command shows capabilities that have drifted from
  reality: ones your project inherits from another project but has never ruled on
  locally, and ones that were declared for a finished work item but never flipped
  off "Missing". It's read-only and exits with an error code when it finds drift,
  so you can run it in CI.

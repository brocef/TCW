# Improve descendant epic display and tag workflows

## Product changes

- Make `tcw work list --include-descendants` render initiative children indented
  beneath their owning epic, including children from registered descendant nodes.
- Add `-i` and `--incl-desc` aliases for `--include-descendants`.
- Ensure planning guidance selects and applies relevant registered tags to new
  work items, registering missing project tags through the existing
  `tcw work tags add <tag>...` command when appropriate.
- Teach backlog-audit guidance to recommend and, after approval, apply relevant
  tag additions/removals.

## Technical changes

- Extend aggregate board rendering to relate items globally by `initiative`, not
  only locally by nested `parent`, while retaining project-qualified descendant
  identifiers.
- Add parser aliases and regression coverage for all three spellings.
- Expand the `tcw-work` skill with conceptual tag guidance and update the two
  prompt-command files.

## Meta changes

The user requested compact planning followed by implementation and explicitly
approved a patch release after the completed bundle. The requested "new tag
registration command" already exists as `tcw work tags add`; do not introduce a
duplicate CLI surface.

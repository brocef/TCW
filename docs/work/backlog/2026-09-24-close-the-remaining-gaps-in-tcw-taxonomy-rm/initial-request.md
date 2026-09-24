# Close the remaining gaps in tcw taxonomy rm

## What is wanted

`tcw taxonomy rm <term>` should never succeed in a way that leaves the project
worse off. Two gaps remain after
`2026-09-15-make-tcw-taxonomy-rm-refuse-nested-terms-and-live-references`:

1. **A capability still names the term.** Removing a term that a local
   capability names in `Subject` or `Feature` succeeds today, and
   `tcw capabilities check` then starts failing. The user's decision: **refuse**
   the removal and list the capabilities that name the term, the same way `rm`
   already refuses when other taxonomy terms reference it.
2. **An unstaged child term.** A child written by hand and never staged
   (`zed/kid/meta.yaml`) does not block `rm zed`. `git rm -rf` removes the tracked
   files, prints "Removed term zed", and `zed` still lists with `kid` under it.
   The user's decision: **refuse**, and say to stage or delete the unstaged child
   first. `rm` must never print "Removed" for a term that still lists.

## Constraints

- The capabilities guard must protect every caller of the store, not only the
  CLI: the web app and other store callers remove terms too. The capabilities
  store opens the taxonomy store (`FsCapabilitiesStore._taxonomy()`), not the
  other way round, so where the cross-component check lives is a spec decision.
- The spec must also say what happens when the capabilities store is absent or
  unreadable.
- The git-based check for nested terms (`ls-files`) exists so that an untracked
  leftover folder cannot leave `rm` stuck. The refusal in point 2 must name the
  way out, because a plain `rm` of the unstaged child fails inside `git rm`.

## Notes

- Merged from two inbox entries filed 2026-09-17 (see `intake.md`), during the
  2026-09-24 backlog cleanup.
- Reference material: asked; none provided beyond the intake.
- Related: `2026-09-16-add-a-rename-verb-to-tcw-capabilities-and-tcw-taxonomy`
  touches the same references, but not the same work.

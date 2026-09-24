## Inbox manifest

- `2026-09-17-tcw-taxonomy-rm-does-not-check-capabilities-that-name-the-term.md`

## Inbox body

# tcw taxonomy rm does not check capabilities that name the term

## Desired outcome

Removing a taxonomy term that a local capability names in `Subject` or `Feature`
is refused (or at least reported), so `tcw capabilities check` does not start
failing because of a removal that succeeded.

## Context

Left out of `2026-09-15-make-tcw-taxonomy-rm-refuse-nested-terms-and-live-references`
on purpose: that item made `rm` refuse nested terms and references from other
taxonomy terms (`relatesTo`, `vocabulary`). Both advisors consulted there agreed the
capabilities reference is a separate change: the capabilities store opens the
taxonomy store (`FsCapabilitiesStore._taxonomy()`), not the other way round, and a
check only in the CLI would leave the web app and other store callers unprotected.

## Notes

- Needs a decision about where a cross-component guard lives, and what happens when
  the capabilities store is absent or unreadable.

## Folded in: inbox entry 2026-09-17-tcw-taxonomy-rm-reports-removed-while-an-unstaged-child-keeps-the-term-listed

_Merged here during the 2026-09-24 backlog cleanup; the entry was removed from the inbox._

## tcw taxonomy rm reports removed while an unstaged child keeps the term listed

### Desired outcome

`tcw taxonomy rm <term>` never prints "Removed term <term>" while that term still
appears in `tcw taxonomy list` and `show`.

### Context

Found by verification of
`2026-09-15-make-tcw-taxonomy-rm-refuse-nested-terms-and-live-references`.

`remove` now asks git which nested terms exist (`ls-files`), so that an untracked
leftover folder cannot block removal. A consequence: a child term written by hand and
never staged (`zed/kid/meta.yaml`) does not block `rm zed`. `git rm -rf` removes
`zed`'s tracked files, leaves `zed/kid/` on disk, prints "Removed term zed", and `zed`
still lists with `kid` under it. Not a regression — the command before that change
left the same state — and nothing tracked is lost.

### Notes

- Options: after `_rm`, say what was left on disk; or refuse when an untracked child
  holds a `meta.yaml`, with a message saying to stage or delete it (plain `rm` of the
  unstaged child fails in `git rm`, which is the stuck state the git-based check
  avoided).

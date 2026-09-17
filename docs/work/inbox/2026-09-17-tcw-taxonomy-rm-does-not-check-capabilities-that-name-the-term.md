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

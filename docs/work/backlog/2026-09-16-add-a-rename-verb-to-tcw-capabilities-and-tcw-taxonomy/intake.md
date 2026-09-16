# Add a rename verb to `tcw capabilities` and `tcw taxonomy`

Neither axis can re-key an entry. `tcw capabilities` offers
`init, list, show, path, add, set, reset, rm, search, extends, check, drift` and
`tcw taxonomy` is the same shape: to rename one entry you add a new one, copy its
body across by hand, re-apply every metadata field with `set`, and `rm` the old
one.

## Why now

This is the **second** time a rename has had to be done that way. The first was
the skill restructure recorded in
`2026-09-14-consolidate-the-setup-skills-into-a-single-tcw-setup-skill`, which is
why every skill capability carries that planning pointer. The second was
`2026-09-15-drop-the-tcw-prefix-from-the-plugin-s-skill-and-agent-names`, which
migrated 15 Features and 15 capabilities as three ordered passes of
`add` + `set` + `rm`. Three things that item had to deal with are all consequences
of the missing verb:

- **Ids do not survive.** `skills/tcw-work`'s `cap-f533ba` became `skills/work`'s
  `cap-0ebf25`, and every one of the 30 entries was re-keyed. Nothing reads those
  ids today, so the loss is currently invisible — but ledger identity is exactly
  the thing an id exists to preserve, and a tracker-backed store would have to
  answer for it.
- **The body is copied by hand.** `description.md` has no command that writes it,
  so the one file per entry that carries the actual content is moved outside the
  interface the skills otherwise insist on.
- **Ordering becomes the caller's problem.** Removing a Feature while a capability
  still points at it leaves `tcw taxonomy check` failing after a command that
  reported success, and `tcw taxonomy rm` only _warns_ about a dangling
  `relatesTo`, so the caller has to sequence three passes correctly and run `check`
  after every single removal to keep a mistake attributable. One entry's
  `relatesTo` named another renamed entry, which constrained the removal order
  further.

## Proposed shape

A verb that re-keys an entry in place, carrying its id, metadata, body and
inbound references:

```
tcw capabilities mv <old-path> <new-path>
tcw taxonomy mv <old-slug> <new-slug>
```

## Abstraction litmus test

**Passes.** Re-keying an entry is something a non-filesystem store can do — a
tracker can move an issue's key, and a table can update a primary key or a slug
column. It is not a filesystem trick; what the previous items avoided was the
filesystem trick (`git mv` on a store folder plus a hand-edited `meta.yaml`),
which is precisely why they went the long way round instead.

## Questions for the spec

- **Inbound references.** A `tcw://` ref naming the old path breaks on a rename.
  The prefix-drop item hit this: `tcw validate` resolves refs inside a capability
  body, and re-pointing one before its target existed turned `validate` red. Does
  `mv` rewrite inbound refs, refuse while any exist, or leave them and let
  `check` report them?
- **`relatesTo` and `Feature` pointers**, which are the same question inside the
  stores rather than in prose.
- **Whether `mv` may cross a namespace**, or only re-key a leaf.
- **Nested entries.** `tcw taxonomy rm` deletes nested terms silently (filed as
  `docs/work/inbox/tcw-taxonomy-rm-deletes-nested-terms-without-a-word.md`), so
  `mv` has to say what happens to children rather than inherit that behaviour.

## Origin

Filed at the completion of
`2026-09-15-drop-the-tcw-prefix-from-the-plugin-s-skill-and-agent-names`, whose
spec and plan both name it as a follow-up to file rather than fold in: it changes
the CLI surface and needs its own spec.

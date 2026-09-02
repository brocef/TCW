# Upcoming

User-facing release notes for the next version. Plain language — no jargon or
internal module names.

### Links to finished work are no longer reported as mistakes

A link to a work item you have completed or discarded used to be reported in
exactly the same words as a link to something that never existed —
`no such work item` — so finishing work slowly filled `tcw validate` with
complaints about work that went fine. Those links now resolve. A link to a slug
your project never had is still an error, which is the distinction that was
missing.

Completing or discarding an item records its slug, so links to it keep working
after its documents leave the tracked tree. The web viewer shows such a link as
finished work rather than as broken.

### `tcw validate` now gives the same answer on every machine

This is the part worth knowing even if you never write links between items.
Resolved items are kept out of the tracked tree by default, but they stay in the
working directory of whoever resolved them — so `tcw validate` passed for that
person and failed for everybody else, at the same commit. If you gate anything
on `tcw validate`, it could pass locally and fail in CI for reasons nobody could
see. A reference to a resolved item now answers the same way everywhere, because
the record behind it is tracked. Validation still scans the working tree rather
than only what is committed, so a mistyped reference inside a resolved item's own
documents remains visible only where those documents are.

### Recording work you finished before this release

Existing projects need one step to benefit, because work resolved earlier left
no record behind:

```
tcw work tombstone add <slug> --resolution done --resolved 2026-09-01
```

Run it for each slug `tcw validate` still complains about. Both flags are
optional — omit them when nobody kept the detail. It refuses a slug that is
still a live item, and commits what it writes.

This adds one file, `graveyard.yaml`, next to your status folders. It is small —
two lines per resolved item — and it is deliberately always tracked: a record
that could be ignored would be missing from exactly the checkouts that need it.

### One thing it deliberately does not do

The record says a slug existed and how it was resolved. It does not say where
the item's documents went. A recorded location would be a promise that they are
still retrievable there, and that promise does not survive squashing, rebasing,
or a shallow clone — a pointer that quietly stops working is worse than none.

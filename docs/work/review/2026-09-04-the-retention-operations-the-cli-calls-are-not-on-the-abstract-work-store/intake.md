Found by a third adversarial review, 2026-09-04.

`WorkStore` gained `incomplete_graph_note`, `epic_children_all_resolved` and
`Tombstone.location` during this work, and `tombstone`/`record_tombstone` — the
immediate neighbours of the retention feature — are already declared abstract.
These are not:

- `pending_deletion`
- `pending_removal`
- `delete_resolved`
- `describe_location`
- `retention`, `retention_problems`, `retention_conflicts`

All seven are defined only on `FsWorkStore`, and the storage-neutral CLI calls
them — `tcw/work/cli.py` at the completion path and the delete path, and
`tcw/validate.py`. A non-filesystem adapter driven through `tcw work complete`
raises `AttributeError`.

`docs/lifecycle/abstraction.md` states the rule as "**Yes** → it belongs in the
model / the abstract store interface", and each of these answers yes in its own
docstring — `parse_retention`'s says outright that "a tracker-backed store can
honor 'do not retain resolved items' by closing and dropping the ticket". So this
is an inconsistency *inside one feature*, not a pre-existing convention to
follow.

`st.path()` has the same shape and is deliberately out of scope: it predates this
branch.

What each would mean for a non-filesystem adapter is the design question to
settle rather than assume — `describe_location` in particular renders a handle
the `Tombstone` docstring calls opaque and never-parsed, so its abstract form has
to be "render this for a reader", not "resolve this commit".

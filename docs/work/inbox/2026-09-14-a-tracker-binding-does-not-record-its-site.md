# A tracker binding does not record which Jira site its ticket belongs to

Found by the combined review of
`2026-09-14-inherit-work-tracker-from-parent-nodes-key-by-key` and
`2026-09-12-claim-an-external-tracker-ticket-and-bind-it-to-a-work-item`, which
ship together. Not fixed by either.

## What happens

A binding in `tracker.yaml` is identified by project id, provider, ticket id and
part (`Bound.key()`, `tcw/tracker/intake.py`). The Jira site is not part of it.
When a node's `base-url` changes, existing bindings still match by ticket id, so
an unrelated ticket on the new site that happens to have the same numeric id is
treated as already bound. Reproduced by the reviewer with two fake sites where
site A's OLD-6 and site B's NEW-9 both have id 10052:

- `import NEW-9`, with NEW-9 assigned to this account, exits 0 and reports the
  site A item as "already bound".
- With NEW-9 unassigned, it exits 1 with a message about the site A binding.
- `link <new-item> NEW-9` refuses because the ticket "is already bound".

Nothing is written to the tracker in any of these cases.

Editing a node's own `base-url` already caused this. Tracker inheritance widens it:
one edit to a parent's `base-url` moves every inheriting child to the new site at
once, and whoever makes that edit may not see the children's bindings.

Not verified against real Jira: that issue ids from two sites collide in practice
(ids are numbered per site), and that an account id is shared across sites.

## Suggested direction

Every binding already stores `ticket.url`, which contains the site, so no format
change is needed. In `find_binding`, when a binding has the same ticket id but its
`ticket.url` does not start with the current `base-url`, refuse and name the item
rather than treating it as a match or a miss. Do **not** simply add the site to the
key: after a site rename, every existing binding would look new and imports would
create duplicates.

`tests/tracker_fake.py` ignores `base_url`, so a test written with a single fake
would pass without testing anything. Use two fakes chosen by site.

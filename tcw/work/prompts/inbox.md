# Stage: inbox

**Purpose.** Turn a raw drop in the work inbox — a pasted request, a delegation
from another node, an escalation from a child — into a tracked work item. It is
the only stage that runs before an item exists, so it takes no work item
reference.

**Inputs.** The raw entry, read with `tcw work inbox show <entry>`; an entry may
be one file or a folder with attachments. Repository discovery is unrestricted —
read whatever helps you understand the request well enough to title it.

**Produce** no lifecycle artifact — this stage creates the *item*.
`tcw work inbox accept` preserves the entry as its `intake.md`: body, resource
manifest, attachments. Shaping that into a request document is `request`'s job,
so an accepted item has an intake and not yet a request.

## Steps

1. `tcw work inbox list`, then `tcw work inbox show <entry>` for anything
   unfamiliar.
2. Decide whether the entry is one item or several. A drop describing three
   unrelated changes becomes three items; one describing a change with three
   parts becomes a single item that a later stage may split.
3. Inspect the node's tag vocabulary with `tcw work tags list` and choose every
   materially applicable tag. Register a new one only if it earns its place
   beyond this item.
4. `tcw work inbox accept <entry>`. The item is named after the entry's first
   `# ` heading, or its filename minus the `YYYY-MM-DD-` prefix (kept when
   stripping it would leave nothing). Pass `--title "<clear title>"` when that
   heading is missing or poor. The command consumes the entry, creates the item
   and prints its slug; it refuses an entry that does not exist.
5. Apply tags and estimates with `tcw work edit`. Where the entry carried links
   or attachments, confirm they survived into the item, gathered under a
   `## References` heading with one line of *why it matters* each.
6. Do **not** ask for more detail here. Whoever filed this is usually an issue
   reporter or another node, not someone present to answer; `request` asks.
7. Commit the new item.

## Exit badly

- *Too vague to title.* Do not invent scope. Accept it under the clearest title
  the text supports and leave the questions for `request`, or leave the entry
  where it is and say why.
- *Already tracked.* Do not accept a second item for it. Record the overlap on
  the item that exists, then remove the entry.
- *Really several items.* Accept the primary one and open the rest with
  `tcw work new`, linked with `--blocked-by` wherever order matters.

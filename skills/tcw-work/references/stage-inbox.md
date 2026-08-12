# Stage: inbox

## Purpose

Turn a raw drop in `docs/work/inbox/` — a pasted request, a delegation from
another node, an escalation from a child — into a tracked work item. This is the
only stage that runs before an item exists.

A **GitHub issue is the same shape from a different source**: someone else's raw
text, accepted or rejected. The `tcw-triage-issues` skill sweeps a project's open
issues and reuses the judgment below for the ones it accepts; what it adds is
GitHub-specific — reaching the issues, and replying to the reporter.

## Inputs

The raw inbox entry, read with `tcw work inbox show <entry>`. An entry may be a
single file or a folder with attachments.

Repository discovery is unrestricted: read whatever code, docs, or history helps
you understand the request well enough to title it.

## Produce

**No lifecycle artifact.** This stage creates the _item_; `tcw work inbox accept`
preserves the entry as its `intake.md` — body, resource manifest, attachments —
and the `request` stage is what shapes that into a request document. Accepting an
entry does not write one, so an accepted item shows `i` and not `R`.

## Steps

1. `tcw work inbox list`, then `tcw work inbox show <entry>` for anything
   unfamiliar. — agent `[judgment]`
2. Run `tcw work lifecycle --stage inbox` and honor any binding it reports.
   — agent `[judgment]`
3. Decide whether the entry is one item or several. A drop describing three
   unrelated changes becomes three items; one describing a change with three
   parts becomes one item that `decompose.md` may later split. — agent
   `[judgment]`
4. Inspect the node's tag vocabulary (`tcw work tags list`) and choose every
   materially applicable tag. Register a new one only if it will be useful beyond
   this item. — agent `[judgment]`
5. `tcw work inbox accept <entry> --title "<clear title>"`. The tool consumes the
   entry, creates the item, and prints its slug; it refuses an entry that does
   not exist. — agent `[gated]`
6. Apply tags and estimates with `tcw work edit`. If the entry carried links or
   attachments, make sure they survived into the item — collect them under
   `## References`, one line of _why it matters_ each, rather than leaving them
   buried in pasted text. Do **not** ask for more here: the requester is usually
   a GitHub issue reporter or another node, and is not present. The `request`
   stage asks. — agent `[judgment]`
7. Commit the new item. — agent `[judgment]`

## Exit

**Well:** the entry is gone from `inbox/`, a backlog item exists with a title
that reads as a change rather than a symptom, and the `request` stage can begin.

**Badly:**

- _The entry is too vague to title._ Do not invent scope. Accept it with the
  clearest title the text supports and let the `request` stage ask the user, or
  leave it in the inbox and say why.
- _The entry duplicates an existing item._ Do not accept it. Note the overlap on
  the existing item and remove the entry.
- _The entry is really several items._ Accept the primary one and create the
  others with `tcw work new`, linking them with `--blocked-by` where order
  matters.

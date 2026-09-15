# Follow-ups the README rewrite found

## Desired outcome

Three defects found while rewriting the README are fixed. None was in that
item's scope, and each is small.

## Context

Found during `2026-09-15-rewrite-the-readme-to-a-new-outline`, which edited no
source code. Verified at that item's work branch.

1. **`tcw validate` fails in a fresh checkout of this repository.**
   `docs/work/backlog/2026-09-09-distinguish-a-blank-artifact-from-an-absent-one-in-the-web-ui/initial-request.md`
   links `tcw://W/2026-08-18-reconcile-read-artifact-with-the-canonical-presence-rule`.
   That item is completed, and completed folders are gitignored, so the link
   resolves only in a checkout that still has the folder on disk. It has no
   record in `docs/work/graveyard.yaml`. In the primary checkout `tcw validate`
   passes; in the worktree `tcw work start --worktree` created, it reports
   "no such work item". A `tcw work tombstone add` for that slug (and a sweep for
   other completed items referenced without a record) should make the answer the
   same everywhere. Worth checking whether CI has the same blind spot.

2. **An example in `docs/guide/taxonomy-and-capabilities.md:25` fails as written.**
   `tcw taxonomy add Permission -p admin` refuses with "parent term does not
   exist: admin" unless `admin` was added first. The README's copy of this example
   was fixed by adding `tcw taxonomy add Admin "…"` before it; the guide still has
   the broken sequence.

3. **A source comment cites README text that does not exist.**
   `tcw/store/fs.py:4964` says a retention backfill is "the migration the README
   describes". The README has not described it since before the rewrite (the old
   README only named `work.retain` once, in the strict-mode limits). Point the
   comment at the document that does describe it (`docs/guide/work.md`,
   "What happens to resolved work"), or reword it.

## Constraints

Item 3 edits `tcw/`, so under this repository's rules it is recorded here rather
than done in a documentation-only item.

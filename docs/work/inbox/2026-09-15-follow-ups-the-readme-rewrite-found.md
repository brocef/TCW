# Follow-ups the README rewrite found

## Desired outcome

The open defects found while rewriting the README are fixed. None was in that
item's scope, and each is small.

## Context

Found during `2026-09-15-rewrite-the-readme-to-a-new-outline`, which edited no
source code. Verified at that item's work branch.

1. **Resolved on `main` before this entry was triaged; no action needed.** `docs/work/graveyard.yaml` now records the slug below, and `tcw validate` passes in a fresh worktree. Kept for the record. **`tcw validate` failed in a fresh checkout of this repository.**
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

4. **`tcw work tracker link --help` contradicts the code.** Its epilog says
   "Nothing moves the ticket for you afterwards — do that in the tracker
   yourself." But `tcw work start` claims a linked ticket, and later lifecycle
   moves send the ticket to the mapped statuses (`tcw/tracker/sync.py:166-167`,
   the `start` path in `tcw/work/cli.py`). `README.md` and `docs/guide/jira.md`
   describe the code correctly; the help text is what drifted. Found by the
   verifier; the rewrite's sweep of `link` descriptions covered documents and
   skills, not CLI help.

## Constraints

Items 3 and 4 edit `tcw/`, so under this repository's rules they are recorded
here rather than done in a documentation-only item.

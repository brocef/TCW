# Fix the guide's taxonomy example and a stale README citation

## Request

Two small corrections found while rewriting the README, both verified still live
at `632f023`. Neither was in that item's scope: it edited no source code, and the
guide defect needs a sentence changed rather than a heading inserted.

1. **The guide's taxonomy example does not run.**
   `docs/guide/taxonomy-and-capabilities.md:25` reads
   `tcw taxonomy add Permission -p admin`, but nothing in the example adds `admin`
   first, so the command refuses with "parent term does not exist: admin". The
   README hit the same defect in its copy of this example and fixed it by adding
   `tcw taxonomy add Admin "…"` ahead of it; the guide still has the broken
   sequence. A reader following the guide in order gets a refusal from the second
   command they run.

2. **A source comment cites README text that no longer exists.**
   `tcw/store/fs.py:4964` describes a retention backfill as "the migration the
   README describes". The README has not described it since before the rewrite —
   the old one named `work.retain` only once, in the strict-mode limits. The
   comment should point at whatever document actually describes it, or be
   reworded so it does not send the reader somewhere that has nothing to say.

## Notes

- **Two of the four parts of the originating entry need no work**, and this item
  is the remaining two. Part 1 was resolved on `main` before triage
  (`docs/work/graveyard.yaml` carries the slug). Part 4 — the
  `tcw work tracker link --help` epilog contradicting the code — was fixed when
  `--sync-status` landed in pull request #45; the epilog now reads "In the
  tracker: nothing, unless `--sync-status` is passed", so the sentence the entry
  quotes is gone. Both confirmed by running the help and checking the graveyard at
  `632f023`. The intake records this too.
- Part 2 edits `docs/guide/taxonomy-and-capabilities.md`, which
  `2026-09-15-repair-sentences-references-and-headings-in-the-guides` also edits,
  at `:53-54`. Different defect, same file: that item is about prose that reads
  wrongly, this is an example that does not run. Whoever takes either should check
  the other is not in flight.
- Part 1 of this request is a documentation change and part 2 edits `tcw/`. Under
  this repository's rules that is why the originating entry was recorded in the
  inbox rather than folded into the README rewrite, which was documentation-only.
- Reference material was not separately solicited; both parts name their own file
  and line, and neither had an open question worth taking to the requester.

## References

- `docs/guide/taxonomy-and-capabilities.md:20-30` — the example block, and the
  `tcw taxonomy add Invoice` line above it that shows the shape a working example
  takes.
- `README.md` — carries the already-corrected copy of the same example, so the fix
  for part 1 is to match a sequence that is known to run rather than to invent one.
- `tcw/store/fs.py:4964` — the comment itself.
- `docs/guide/work.md`, "What happens to resolved work" — the entry's suggestion
  for where the comment should point, to be confirmed rather than assumed.
- `2026-09-15-rewrite-the-readme-to-a-new-outline` (completed) — the item that
  found all four parts; its scope is why they were recorded instead of fixed.

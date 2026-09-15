# Refined outcome — Unify raw intake into a single artifact

## The acceptance decision, stated accurately

**Closed on the requester's instruction to drive the whole initiative through
without stopping per slice, with verification deferred to the end of the epic.**
This is not a per-item acceptance and should not be read as one. The requester's
words: "Continue to complete all slices and parts of the work, we'll verify at
the very end."

So the honest record is: C1's *implementation* is complete and independently
assessed; C1's *acceptance* is pending, and will be given — or refused — when the
initiative is verified as a whole. If that verification rejects something in C1,
the item is completed and will need a new item rather than a `rework`. That is a
consequence of the instruction, recorded here so it is a known cost rather than a
surprise.

## What was independently assessed, and by whom

The third round's rejection came from a read-only verifier that re-ran every
acceptance bullet against a scratch node through the real CLI rather than through
the suite. Its findings on the *behavior* were unambiguous and are worth carrying
forward as the evidence this closure rests on:

- A fresh epic reconciles to `rollup.md` with no `initial-request.md`, asserted by
  listing the folder. Board line shows no `R`.
- Migration works with prose on both sides of the block, and leaves no empty file
  when the block was all the request held.
- Idempotence holds; a third `--commit` with nothing changed creates no empty
  commit.
- The refused-commit path was exercised with a real pre-commit hook: exit 1, no
  traceback, rollup left staged, and the retry after removing the hook commits.
- No composed `store.path(...) / "<file>"` remains in the reconcile flow, and no
  code path in `tcw/` writes `initial-request.md` outside the `request` stage.

The three defects it found were all in the reporting layer, and all four items it
raised were fixed in the round that followed (`5429702`, `8c40cc2`, `b6dfabf`).
Nothing found after that round has been re-verified by anyone but the implementer
— which is precisely what the end-of-initiative verification is for.

## Evidence at closure

1314 Python tests, 52 web unit tests, 14 end-to-end tests, `tcw validate` OK,
`tcw capabilities check` OK, `tcw capabilities drift` clean, and
`pnpm check:build` clean with the bundle rebuilt and committed.

## Deferred, deliberately

**A read-only viewer for generated sidecars in the web app.** `rollup.md` is
listed and labelled `generated`, and offers no Edit button — but it is not
readable in the app either, because the Edit modal was the only surface that
rendered sidecar content. Before this item the rollup was readable in the Request
tab, because it *was* the request, so this is a small real regression. The release
note points at `tcw work reconcile <epic>` and `tcw work path` instead. Worth its
own item if the web app is meant to be a complete reading surface.

**No `tcw work sidecar` read verb.** The CLI can print the rollup only by
re-running `reconcile`. That is adequate — it is idempotent and prints the current
block — but it is a command that writes, used as a command that reads.

## Closeout choices

- **Version:** deferred to the end of the initiative rather than cut here. The
  requester's earlier standing decision was a minor bump at C1's completion; with
  every slice now in flight, one cut at the end describes the release better than
  eight. `docs/{changelogs,release-notes}/upcoming.md` keep accumulating until
  then.
- **Merge/PR route:** deferred with it. All slices land on
  `epic/polymorphic-work-lifecycle`.
- **Follow-up items:** the two deferrals above, to be filed at the initiative's
  verification rather than now, so they can be judged against the finished
  lifecycle instead of against C1 alone.

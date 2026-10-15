# Refined outcome — TCW-77: the web viewer

**Accepted** on 2026-10-15 under the TCW 3.0 epic's rule: a child item is
approved at verify when it passes a bounded adversarial review (the owner,
2026-10-02, restated 2026-10-13: "I'm going to do my own review and
verification after all slices are completed, not after each one"). The
confirming round ended `DONE`.

## What was accepted

Everything in `outcome.md`:
- **One process:** `tcw serve` is a Python `ThreadingHTTPServer` that serves
  the API and the packaged client. Node.js, Fastify and the sidecar are gone.
- **The work API:** the project, the board (with a fallback to item folders
  when the backend cannot list), one item, its files with a revision check,
  properties, comments, blocks, create, tickets and adopt, and suggestions.
- **Record edits:** taxonomy and capability edits refuse an inherited entry
  and a subject that is not a vocabulary entry.
- **The client:** the 3.0 board, item page, file editor and forms, with
  autocomplete in refuse, warn or allow mode on every reference field, and
  `tcw://` completion in the Markdown editor.
- **Guards, browser tests and a Jira-mode fixture**, the capability and
  taxonomy records, the rewritten `docs/guide/web-viewer.md`, and the release
  entries.

## Reviews

**Round 1** used three Claude reviewers, split by area: server, client, and
records. Every finding was checked against the code before it was fixed; none
was wrong. The fixes are in `outcome.md`'s "Review round 1" section. The ones
that mattered most:

- **A Jira item could not be shown** when reading it worked but listing the
  other items failed (S1). Only TCW's own usage errors are 400 now.
- **Any folder counted as an item** (S2). Each backend now says which folders
  are its items (`is_item_folder`).
- **Adopting a ticket skipped the request stage's hooks** (S3). It runs them
  now, as the CLI does, and the client shows what failed.
- **Refused text vanished from a field, and some ways off a page lost unsaved
  work without asking** (C2, C6).
- **The Jira assignee was not checked** against Jira's assignable users (R3).

**Rebase.** TCW-74 completed while round 1 was being fixed. The branch was
rebased onto its tip (`0e30fca5`) without conflicts, and the confirming round
reviewed the combined change as well.

**Confirming round:** `DONE`. It found no interaction with TCW-74 and
confirmed the round-1 fixes. Three small findings belonged to this change and
were fixed in place (`b881aea6`, `5b0dcf95`), each with a test that goes red
without its fix:
- N1: three hand-sent requests that S1 had turned into 500s answer 400 again.
- N2: typing in the sidebar filter no longer loses the record of unsaved work.
- N3: the adopt failure message no longer follows the browser's Back.

One finding needed a separate change (2.x text in the configure skill's
reference files). It is item 8 in TCW-75's `notes-from-tcw-74-and-tcw-77.md`.

## Follow-ups

- `docs/work/inbox/2026-10-15-tidy-what-tcw-74-and-tcw-77-s-reviews-left-elsewhere.md`.
- TCW-75's `notes-from-tcw-74-and-tcw-77.md`: 2.x `tcw serve` text in the
  README and guides, the retired `Planning doc` field on capability records,
  and the configure skill's references.

## Deferred, by the owner's instructions for this epic

- **The full suite** runs near the end of the epic. Here: `tests/serve/`, the
  standing guard files, the backend contract, Jira, layout and filesystem
  backend tests, and the record and store-name tests (1778 passed, 10
  skipped, before round 2; 326 after it). `pytest --collect-only -q` is clean.
- **Playwright** (`pnpm test:e2e`), the refresh of the three snapshots, and a
  run of `jira.spec.ts` against the launcher.
- **This repository's `tcw-config.yaml` is still 2.x**, so the board is driven
  with the installed 2.8.1 until TCW-76.

## Capabilities

The records were written on the branch. They reach `main`'s ledger only when
the epic merges, so the item is completed by hand, as TCW-69 to 74 were.

## Closeout route

The branch `work/2026-10-01-tcw-77-…` fast-forwards `epic/tcw-3.0`, and its
worktree and branch are then removed. `main` receives 3.0 only when the epic
ends. No GitHub issue originated this item; it came from Jira.

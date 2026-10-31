---
verdict: accepted
judges: 4
---

# Review round 4 — TCW-109

Reviewed by a separate read-only agent (the `tcw:reviewer` agent) on
2026-10-24 in a frozen worktree at `73a86216`, over `25ca7f40..73a86216`,
against the qa rejection that implement round 4 answers: the web client
crashed when `/api/project` answers the tags as unavailable. The earlier
rounds' results carry forward.

## Checks run

- The full suite as CI runs it, run by the dispatching session at `a60555de`
  in two halves by folder: `1985 passed, 2 skipped` and `4358 passed,
  111 skipped`, recorded in `implement/round-4.md`.
- By the reviewer: `pnpm test` `195 passed`; `tsc --noEmit`, `pnpm lint` and
  `pnpm check:build` exit 0; the end-to-end suite with every `TCW_*` variable
  unset and scratch home folders, `18 passed`, the three new missing-parent
  tests among them.
- The four new client tests run against the four source files put back to
  `25ca7f40`: all four fail, the form tests with `project.tags.map is not a
  function`.

## The qa rejection

- `TProject.tags` is typed as the server sends it, `string[] | TUnavailable`.
  The only readers of the project's tags, `TagsInput` and the board's filter,
  both check for the unavailable answer first; the other `.tags` readers read
  an item's own tags. No other field this item made answerable as
  unavailable reaches the client.
- With the tags unavailable, the new-item form sends no tags and the edit
  form sends only the changed properties, so an item's tags stay as they
  are; the reason is shown where the field would be, as the command line
  stops `--tag` with exit 7 and keeps everything else working (Design 3.4).
- The Tags filter shows the reason; with a list it behaves as before, and the
  existing end-to-end filter test passes.
- The new end-to-end spec's port, 8895, is its own; the suite runs one
  worker.
- The changelog and release-notes lines describe what the code does.

No finding belongs to this change.

## Needs a separate change

Kept on the 4.0 run's list of small follow-ups, decided by the dispatching
session:

- The end-to-end specs' readiness check would accept another server already
  listening on the spec's port; this is true of all three specs.

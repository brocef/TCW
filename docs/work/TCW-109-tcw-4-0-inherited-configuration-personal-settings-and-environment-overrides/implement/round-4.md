# Implement round 4 — TCW-109

Answers the qa rejection of 2026-10-24 (scenario 3, the web app). Built on
the branch `v4`, in the worktree `.claude/worktrees/v4`, with the code under
test run from that worktree's own virtual environment. `.venv/bin/tcw` was
never run with this repository as the project; the hand checks and every
`tcw serve` ran in scratch projects with `HOME`, `XDG_CONFIG_HOME` and
`XDG_CACHE_HOME` set inside them and every `TCW_*` variable unset. The
lifecycle was not driven by any CLI: the dispatching session makes every
move, so no ticket was moved and nothing was posted. This round gives no
verdict.

## The defect

With a parent that is not on this machine, `GET /api/project` answers
`tags: {"unavailable": <why>}` (Design 3.4, `_registered_tags` in
`tcw/serve/work.py`), but the web client typed `tags` as a list of strings
and called `project.tags.map` in the new item form and the properties form,
so "+ New item" and an item's "Edit" replaced the page with
`t.tags.map is not a function`. The board's Tags filter showed
`none available` instead of the reason.

`tags` is the only field TCW-109 made answerable as `{"unavailable": …}`:
the other uses of `unavailable(` in `tcw/serve` (`degrading` and the Jira
create screen's `createFields`) were there before this item, and the client
already handles both.

## What was done

All in `774e98e6`.

- `TProject.tags` is now `string[] | TUnavailable`
  (`web/client/src/model/types.ts`), so the type checker finds every reader.
  It found exactly the three the qa findings name.
- The two forms share a new `TagsInput` (`web/client/src/ui/work-forms.tsx`).
  With the tags readable it is the Tags field as before. With them
  unavailable it shows, where the field would be, "No tag can be chosen,
  because the project's tags could not be read: <why>", preceded in the
  properties form by "Tags <the item's tags> are kept as they are." when the
  item has any. No tag can be chosen, so the forms send none: the new item
  form sends no tags, and the properties form sends only the properties
  that changed, so the item's tags are left alone.
- The board's Tags filter passes the reason to `FacetPopover`
  (`web/client/src/ui/content-views.tsx`, new `unavailable` prop), which
  shows "could not be read: <why>" in place of the options.
- The built client (`tcw/serve/dist/`) is rebuilt with `pnpm build`.
- The changelog and release-notes `upcoming/` entries for TCW-109 each gain
  a paragraph on the web app's behaviour.

## Decisions

1. **The tags field shows the reason and offers nothing, rather than
   refusing on save** (decided by the implementing agent). The command line
   stops `--tag` with exit 7 and leaves every other part of `tcw work new`
   and `tcw work edit` working; the closest web form is one in which no tag
   can be chosen and everything else can be saved. A field that accepted a
   tag and then refused the save would let a person fill in a value that
   could never be kept. The item's existing tags are shown, so the edit form
   does not look as though the item had none.
2. **The Tags filter offers no checkbox and says why.** The board's tag
   query reads the registered tags on the server (`tcw work list --tag`
   stops with exit 7 in the same project), so offering a tag there would
   lead only to an error.

## Tests and their results before and after

Before means the four changed source files put back to their state at
`25ca7f40` with the new tests kept; after means this commit.

| Test | Before | After |
| --- | --- | --- |
| `work-forms.test.tsx` › the new item form shows the reason, offers no tag, and creates without one | failed, `TypeError: project.tags.map is not a function` | passed |
| `work-forms.test.tsx` › the properties form keeps the item's tags and saves other changes without them | failed, the same `TypeError` | passed |
| `app.test.tsx` › the Tags filter says the tags could not be read, and why | failed, no "could not be read" text | passed |
| `app.test.tsx` › + New item and Edit open their forms, with the reason for the tags | failed | passed |
| `web/e2e/missing-parent.spec.ts` (new): `tcw init --id app`, `parents: [core]` with no `core` anywhere, `tcw serve` | against the old built client: the summary test passed, and "an item is created and edited" failed (the form never showed); the suite runs in serial, so the filter test did not run | all 3 passed |

The end-to-end test checks that `/api/project` answers `tags.unavailable`
containing `(work.tags)`; that "+ New item" shows the reason, has no Tags
combobox and creates an item; that "Edit" on it shows the reason and saves a
new priority; that no page error was raised; and that the Tags filter shows
the reason and not `none available`. Its port is 8895, as 8893 was held
during this round by a server another session had started.

Checks run on this commit:

- `pnpm build`, then `pnpm check:build`: exit 0.
- `pnpm test`: 15 files, 195 tests passed.
- `pnpm exec tsc --noEmit`: no errors. `pnpm lint`: exit 0.
- `pnpm exec prettier --check` on every changed `.ts` and `.tsx` file: clean.
- `pnpm test:e2e` with every `TCW_*` variable unset and `HOME`,
  `XDG_CONFIG_HOME`, `XDG_CACHE_HOME` and `TMPDIR` in scratch: 18 passed.
- `.venv/bin/pytest -q -p no:cacheprovider tests/serve`: 375 passed.

Every server started for this round was stopped; `lsof` showed none of
them listening afterwards.

## The suite

The full Python suite was not run in this round: the dispatching session
runs it, as CI does, on this tree.

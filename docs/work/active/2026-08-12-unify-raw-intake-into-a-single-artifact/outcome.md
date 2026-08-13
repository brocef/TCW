# Outcome — Unify raw intake into a single artifact

> **Second pass.** Rejected at `verify` and reworked — see the "After the
> rejection" section at the end. The body of this document describes the first
> pass and stands as written.

All thirteen plan tasks shipped. Suite green at 1245 passed (baseline before this
item: 1229). Every acceptance criterion is met; criterion 12's `Missing` →
`Supported` flip is the completion gate's and has not run yet.

## What shipped, task by task

| # | Task | Commit |
| - | ---- | ------ |
| 1 | Register `intake` in `WORK_ARTIFACTS` | `099f118` |
| 2 | One presence rule (`_present` / `_resolve_body`) | `befe3f2` |
| 3 | Core revision hashes the resolved artifact name | `8112d8f` |
| 4 | `intake` creation argument; request template deleted | `3e2dce8` |
| 5 | `tcw work new` pipes stdin into intake | `5254e31` |
| 6 | `inbox_accept` writes intake | `818f1e3` |
| 7 | The write contract and `WorkDetail.promoted` | `39e47ac` |
| 8 | The `i` board letter, in lifecycle order | `1adcc79` |
| 9 | Capability ledger | `92307c7` |
| 10–13 | Documentation Sync (all four triggers) | `b8a76c2` |

## What the plan and spec got wrong

**Task 1 was not inert.** The plan claimed adding a name to `WORK_ARTIFACTS`
would pass the existing suite unmodified. `test_artifacts_report_bounded_presence_and_locator`
asserts the presence dict exactly, so it failed — correctly. A test that
enumerates a registry is *supposed* to fail when the registry grows; that is the
test doing its job, not a mis-prediction worth avoiding. Fixed in place.

**There is no `tcw work edit --body`.** The spec's criterion 8 and the plan's task
7 both described the CLI printing a promotion notice on stderr. The CLI has no
body-write path at all: `tcw work edit` sets title, estimates, tags, and blocking
links, and `update_work`'s only caller is `serve`'s PATCH handler. Adding a
`--body` flag to make the criterion true would have been scope nobody asked for,
so the contract lives where the writes actually go — `WorkDetail.promoted`,
surfaced by `serve`. The spec and plan are corrected in place with the reasoning
recorded, in the same commit as the code (`39e47ac`).

On the filesystem the common case is an agent writing `initial-request.md`
directly, outside the store. Promotion there needs no announcement — the file
appearing *is* the announcement — and the presence rule handles it correctly.
Verified by hand.

**`body_path` gained a crash path, and it was closed.** The plan treated the
`body_path` change as pure resolution. It also made the method *read files* for
the first time, so a folder claimed by another process mid-read would raise
`FileNotFoundError` where the old lexical implementation could not. `_resolve_body`
now treats a vanished file as absent, preserving the property
`test_board_artifact_flags_survive_a_concurrent_claim` exists to defend.

**Six existing tests, not "any test asserting `## Product changes`".** The plan
predicted breakage from tests asserting the template's *text*. No test asserted
the text; six asserted the template's *existence* — they needed a file to read
(`test_cli_edit_title_keeps_slug_and_body`), to hash
(`test_get_detail_returns_full_revision_map`), to fail a write on (the two
`_failure_leaves_no_directory` rollback tests), to time
(`test_modified_timestamp_tracks_only_bounded_work_resources`), or to conflict a
merge on (`test_complete_aborts_on_merge_conflict`, which used `git commit -am`
on a file that is now untracked). Each now creates the file it needs. None of
them was testing the template; all of them were relying on it.

**The router has a line budget, and the docs had to respect it.**
`test_the_router_stays_within_its_line_budget` caps `skills/tcw-work/SKILL.md` at
60 body lines with the rule "extract, don't grow". The plan's task 13 assumed the
router would carry a paragraph about intake. It cannot: the intake orientation
went to `references/commands.md` (a new "The body surface" section),
`stage-request.md`, and `stage-inbox.md` instead, and `SKILL.md` is byte-identical
to before. That is the test working as designed.

## Not changed, deliberately

**`tcw work reconcile` still writes into `initial-request.md`.** For an epic with
no request, reconciling creates one containing only the rollup block — a code path
that produces an `initial-request.md` without the `request` stage running. It is
not a synthesized *template*: the rollup is real content, and `epic-deltas.md`
already declares that file the managed target for the rollup. Criterion 4's grep
is clean. Flagged here because it is the one remaining path that can light up `R`
on an item nobody wrote up, and `verify` may reasonably want it as a follow-up
item rather than a silent acceptance.

## Verified by hand

Everything the plan listed as unverifiable by the suite, except one:

- **`tcw work new` with and without piped input**, in a scratch node. No stdin →
  the folder holds `state.yaml` alone and no `→ edit:` line prints. Piped → the
  text lands in `intake.md` verbatim and the hint points at it. Reads as intended
  rather than as a missing file.
- **The board through all four states** — `-`, `i`, `iR`, and a legacy `R`.
- **`tcw work inbox accept` on a folder entry with a binary sibling** — manifest,
  `— accepted from INDEX.md` suffix, attachment preserved, no request written.
- **Promotion by direct file write** — `show` switches from intake to request,
  the board goes `i` → `iR`, and the intake is unchanged.
- **Not done: clicking through `tcw serve`'s editor.** The PATCH handler is
  tested directly (`test_body_edit_on_intake_only_item_promotes_and_preserves_intake`),
  including the `"promoted"` payload, but nobody has watched the UI render it.
  The web app is where a user would meet this first. Left for `verify`.

## Notes

- The abstract surface came out smaller than the epic's plan implied. `read_artifact`
  and `write_artifact` were already bounded by `WORK_ARTIFACTS`, so registering
  `intake` made it readable and writable with no new interface method. The only
  genuinely missing operation was *create an item whose starting content is
  intake*, which is one keyword argument. Worth carrying into C2: the epic's
  child descriptions may be sized against an interface that does not need to grow.
- Every existing item's core revision changes on first read after this lands. The
  token is compared within a session and never persisted, so the effect is nil;
  recorded so it is not rediscovered as a bug.

## After the rejection

`verify` rejected the first pass on `rework.md`: the store, the CLI, and the API
learned about intake and the web app did not. All three items are addressed.

| # | Task | Commit |
| - | ---- | ------ |
| 1 | The request tab gates on the artifact, not the body | `9e0de85` |
| 2 | The core editor seeds `body` from the request only | `9e0de85` |
| 3 | The save reports a promotion | `9e0de85` |
| 4 | Regression tests, component and end-to-end | `38a79df` |
| 5 | Documentation Sync — README, changelog, release notes | `607a891` |

**The rework document under-described the defect, and clicking through found the
rest.** It named the tab's *rendering* — raw intake shown under the request's
label. Fixing the rendering and re-running the by-hand check showed the same
fallback reaching the **editor**: "Edit Initial Request" opened pre-filled with
the intake text, so saving copied the intake into the request that is supposed to
replace it, and the intake was preserved only in the sense that a copy of it now
existed in two places. `enterCore` seeds `draft.body` from `item.body`, which is
the same fallback one layer further in. Both now read the `initial-request`
artifact's `present` flag, which is the resolved fact rather than a resolution of
it.

This is the one finding that would not have come from any amount of reading, and
it is exactly the check `outcome.md`'s first pass deferred and `rework.md`
re-listed as task 4. The lesson generalizes past this item: `serve` has an API
and a client, and a criterion satisfied at the handler says nothing about the
client, because the client is free to ignore what the handler returns — which is
literally what `promoted` was doing.

**No new tab for intake.** `content-views.tsx:393-431` already renders every
present artifact outside the three-tab set as a button row, so `intake` was
reachable the whole time under its own name. Confirmed rather than rebuilt.

**Where the checks went.** The tab logic is a component test
(`work-document-tabs.test.tsx`) because that is where the fallback lives. The
editor seeding and the promotion notice are end-to-end
(`parity.spec.ts`) because they only exist as a round trip through the API. The
new e2e case is **last in the file, deliberately**: it creates a work item, and
every screenshot baseline above it encodes the tree as it stands at that point.

**`tcw/serve/dist` is tracked, and a stale build is how this shipped.**
`pnpm check:build` compares the committed bundle against a fresh one; it was
never run against the first pass. Rebuilt and committed with the fix.

### Re-verified after the merge with `main`

The branch was 99 commits behind `main` (v0.21.1 released in between) and was
merged forward before any of this. Two conflicts, both in code this item wrote:
`_detail_snapshot`'s missing-directory branch, where `main`'s `raise _Moved`
retry supersedes this item's `return None`, and `update_work`'s return, where
`main`'s `_require_detail` and this item's `promoted` flag compose. One test
`main` added after the divergence
(`test_inbox_accept_keeps_the_original_markdown_in_the_body`) asserted the
accepted entry lands in `initial-request.md`; it reads `intake.md` now.

Every acceptance criterion re-checked by hand in a scratch node after the merge —
all three inbox shapes, all four board states, both promotion paths, and the
both-absent and empty-request-beside-real-intake cases. Suite green at 1310
Python tests, 51 web unit tests, and 14 end-to-end tests.

### Still deferred

**`tcw work reconcile` writes `initial-request.md`** for an epic with no request.
Raised in the first pass, held out of the rework as a reconcile defect rather
than an intake one, and still the one path that can light `R` on an item nobody
wrote up. For `verify` to file as its own item.

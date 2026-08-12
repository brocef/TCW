# Outcome — Unify raw intake into a single artifact

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

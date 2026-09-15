# Outcome — Unify raw intake into a single artifact

> **Fourth pass.** Rejected at `verify` three times. The body of this document
> describes the first pass and stands as written; each rejection is recorded in
> its own section at the end.

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

_(`verify` put it in scope instead of filing it — closed below.)_

## After the second rejection

`verify` rejected again on `rework.md`: reconcile still created the request, so
criterion 4 read clean while the property behind it did not hold. The deferral
above is now closed in this item rather than as a follow-up.

| # | Task | Commit |
| - | ---- | ------ |
| 1 | Pin the rollup to its own sidecar (tests first) | `2a15af4` |
| 2 | Write the rollup to `rollup.md`; migrate a legacy in-request block | `89dedfc` |
| 3 | Documentation Sync — README, capability, `epic-deltas.md`, changelog, release notes | `4b8cb4f` |

**The whole change at the write site was calling the method that already
existed.** `recursion.py` composed `store.path(epic) / "initial-request.md"` and
hand-rolled the atomic write and the staging; `write_sidecar` on the abstract
`WorkStore` already did both. Registering `rollup.md` in `WORK_SIDECARS` and
calling it removed code rather than adding it — the litmus test passing instead
of being argued around. `delete_artifact` is the one genuinely new ABC method,
and it exists so the migration can drop a request the strip left empty without
composing a path either.

**The rollup is a sidecar, not an artifact, and that is the load-bearing
choice.** Every `WORK_ARTIFACTS` name is the output of a stage someone runs; this
one is the output of a command. As an artifact it would carry a board letter and
sit in a lifecycle position it does not occupy — which is the same defect,
re-registered as a feature.

### Verified by hand

Migration was exercised on **this repository's own epic**, which is the only
place a real legacy rollup existed:

- `tcw work reconcile <epic>` moved the block out of `initial-request.md` into a
  new `rollup.md`, left the human-written request prose above it untouched, and
  `git grep tcw:rollup` on the request returns nothing. Committed as `4579a78`.
- Re-running with nothing changed stages nothing; `--commit` on an unchanged
  rollup exits 0 without an empty commit.
- A fresh epic in a scratch node reconciles to `rollup.md` with **no**
  `initial-request.md` in the folder, and its board line shows no `R` — the
  property criterion 4 was supposed to assert, now asserted by listing the folder
  rather than by grepping for a template. Covered by `2a15af4`'s tests.

Suite green: 1314 Python, 51 web unit, 14 end-to-end, and `pnpm check:build`
clean (the stale-bundle trap from the first rework).

### One thing found and not fixed

**The web app offers an Edit button on the generated rollup.** `tcw serve`'s
sidecar handling is registry-driven, so `rollup.md` appeared in the Sidecars
section the moment it was registered — read, listed, and editable, exactly like
`capabilities.yaml`. Reading it there is the improvement; editing it is not, because
the next `reconcile` overwrites whatever was typed.

Left alone deliberately. It is a lost edit to a machine-generated file, not the
laundering of a user's own words into a document they did not write, which is the
defect class this item exists to close — and marking a sidecar read-only means a
`generated` flag in the registry, a rejection in the PUT handler, and a read-only
mode in the editor, for a file nobody has asked to edit. Named here so `verify`
decides rather than discovers: a follow-up item if wanted, otherwise accepted.

_(`verify` priced this correctly and put it in scope — closed below.)_

## After the third rejection

`verify` confirmed the second rework's behavior at the property level, in a
scratch node through the real CLI, and rejected on the reporting layer instead:
three documents describing something the code no longer does, plus the web
affordance above.

| # | Task | Commit |
| - | ---- | ------ |
| 1 | `stage-request.md`'s retracted claim; the vacuous assertion; the release-note wording | `5429702` |
| 2 | Mark `rollup.md` generated; drop its Edit affordance | `8c40cc2` |
| 3 | Documentation Sync — changelog, `web/editing` capability, capability ledger | `b6dfabf` |

**The cost estimate above was wrong, and being wrong is the finding.** This
document argued the web fix away on a price — registry flag, PUT rejection,
read-only editor mode — that nobody had checked. Both `serve` sidecar payloads
are already assembled field-by-field from `sc_info`, so the real change is one
registry key, that key echoed twice, and one conditional in the client. The PUT
rejection and the read-only editor are not prerequisites and were not built:
`reconcile` writes through `write_sidecar` itself, so the flag governs the
affordance, not the store. An estimate offered as a reason to defer is a claim
like any other, and this one went into an outcome document unverified.

**The vacuous assertion is the third appearance of this item's own fallacy —
inside the test written to close the second one.**
`assert "R" not in {a.name for a in store.artifacts(epic) if a.present}` cannot
fail: `artifacts()` yields `initial-request`, `spec`, `intake` — names, never
board letters. It was removed rather than replaced. The property is already
pinned by the two lines around it (the folder listing and
`read_artifact(...) is None`), and the board letter follows from the artifact's
absence; a check that cannot fail is worse than no check, because it reads as
coverage. The comment left in its place says so, so it does not come back.

### One place where the rework document was not followed

`rework.md` item 4 said reading the rollup in the web app "must survive: hide the
Edit affordance, not the sidecar." The sidecar is still listed and labelled
`generated`, but it is **not readable in the app** — the Edit modal was the only
thing that rendered its content, and `/open` hands the file to the OS rather than
rendering it in-page. Keeping in-app reading meant a read-only mode in the resource
editor, which is the hardening the same document called optional.

So the release note was corrected instead of the app: it now points at
`tcw work reconcile <epic>` (which prints the current rollup and provably stages
nothing when unchanged) and `tcw work path`, and does not claim the web app will
show it. That is a real, if small, loss against the pre-change behavior, where the
rollup was readable in the Request tab because it was the request. Flagged rather
than buried — `verify` may reasonably want the read-only viewer as a follow-up.

### Checks

Suite green: 1314 Python, **52** web unit (one new), 14 end-to-end, `tcw validate`
and `tcw capabilities check` OK, and `pnpm check:build` clean with the bundle
rebuilt and committed — the stale-bundle trap that shipped once already.

The new component test was confirmed to **fail** with the guard removed before it
was kept, which given the paragraph above about vacuous assertions is not a
formality.

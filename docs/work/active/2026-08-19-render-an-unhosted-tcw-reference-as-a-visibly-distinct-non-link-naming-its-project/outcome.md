# Outcome: Render an unhosted tcw:// reference as a visibly distinct non-link naming its project

Every plan task shipped. The visual check (Task 4) passed on a fixture, but only
after the plan's chosen surface turned out to be broken by a defect that predates
this change — the largest thing the plan got wrong, detailed below.

## What shipped

| Task                             | Commit               | What landed                                                                                                        |
| -------------------------------- | -------------------- | ------------------------------------------------------------------------------------------------------------------ |
| 1 — capability back-pointer      | `5ecdb9a`            | `capabilities.yaml` declaring `changed: [web, cli/reference-a-tcw-object]`                                         |
| 2 — `/api/resolve` failure shape | `f74268e`            | `tcw/serve/__init__.py` + 4 extended/added tests in `tests/test_serve_resolve.py`                                  |
| 3 — three appearances + bundle   | `f4e58c0`            | `shared-components.tsx`, `style.css`, 4 new `Markdown` tests, rebuilt `tcw/serve/dist`                             |
| 4 — manual look                  | (no commit)          | Screenshots in both themes; see **Task 4** below                                                                   |
| 5a — documentation               | `6a346eb`            | `README.md`, `docs/release-notes/upcoming.md`, `docs/changelogs/upcoming.md`                                       |
| — findings                       | `417179d`            | Two pre-existing defects filed to `docs/work/inbox/`                                                               |
| — review rework                  | `634cf05`, `c594274` | Lazy hosted-projects snapshot; unopenable references made genuinely unclickable; three tests strengthened or added |

An adversarial `codex exec` review of the finished diff returned **NOT DONE**
with one P1 and five P2 findings. What was accepted and what was not is below;
the rework is the last row.

At this first pass, 5b (the capability wording flip) was deliberately not done
yet: it belonged at `complete`, per the plan. It is reconciled in the final
round recorded below.

## Test results

Run at the tip of `c594274` (after the review rework):

- `pytest` — **1959 passed** in 422s (`pytest -q`, exit 0).
- `pnpm test` — **58 passed**, 11 files.
- `pnpm exec tsc --noEmit` — exit 0. `pnpm lint` — exit 0.
- `pnpm check:build` — exit 0: the committed `tcw/serve/dist` matches a fresh
  build of the committed source.
- `tcw validate` — on this repo, `validate OK`, byte-identical to the capture
  taken before the first edit; and on the three-node fixture that actually holds
  off-board references, byte-identical between `tcw/` at `5ecdb9a` and at `HEAD`
  (spec criterion 7, re-done properly after the review).

The Python tests were watched red first, and the failure text named the defect
rather than something adjacent: `KeyError: 'reason'` on the shape test, and
`assert {'ok': False} == {'ok': False, ...}` with `Right contains 2 more items:
{'project': 'proj', 'reason': 'unhosted-project'}` on the two gate tests. Of the
four original client tests, three were red for the right reasons and the fourth
(`rewrites a resolvable reference into in-app navigation`) was **green from the
start** — it is a regression guard for behavior this change preserves, not a
test of new behavior, and it is recorded as such rather than counted as proof.
The three tests added or rewritten during the review round were each watched red
against the defective version before being accepted, including the one that only
goes red when `aria-describedby` specifically is removed.

## The review round

Reviewed `5ecdb9a..417179d` with `codex exec --sandbox read-only`, prompted at
the response contract, the hoist, the disclosure argument, the DOM insertion,
whether each test proves what it claims, and whether the spec asserts anything
the diff does not support. Every finding was reproduced before being accepted.

**Accepted and fixed (`634cf05`, `c594274`):**

1. **P1 — an off-board reference was still clickable.** The rendering added a
   class, a badge and `cursor: not-allowed` but left `href="tcw://…"` in place,
   and the delegated handler navigates only on `data-nav-key`
   (`web/client/src/ui/app.tsx:891`) — so the click went to the browser's
   protocol handling. The item is titled "…as a visibly distinct **non-link**";
   what shipped first was a link that looked otherwise. Worse, my accessibility
   test asserted `getByRole("link", …)`, which would have blessed it. Both
   failure paths now drop the `href` and keep the address in `data-tcw-ref` —
   the root-cause fix, so the pre-existing `tcw-inert` path is corrected too.
   Verified in the browser: clicking an off-board reference leaves `location`
   unchanged, `cursor` computes to `not-allowed`.
2. **P2 — the `_hosted_projects()` hoist widened the failure surface.** Hoisting
   it out of the loop meant an aggregating server walked and validated the
   descendant graph for _every_ batch, including `{"uris": []}` and batches of
   purely local or malformed references — so a broken graph could turn
   `tcw://garbage`, which needs no storage to classify, into a 500. Now taken
   lazily on the first foreign reference and reused for the rest of the batch,
   which keeps the "one walk per batch instead of 256" win without the new
   failure mode. New test `test_resolve_does_not_read_the_graph_for_a_batch_with_no_foreign_ref`
   counts the calls; watched red against the hoisted version (`assert [1] == []`).
3. **P2 — the duplicate-badge guard trusted the badge class.** `marked` passes
   authored HTML through, so a document containing a `tcw-project-badge` span
   next to a reference would have suppressed that reference's accessible note
   entirely, and an authored `id="tcw-off-board-0"` could collide with the first
   generated one. The guard now keys off a marker attribute we set ourselves and
   rebuilds the pair rather than bailing, and ids are minted past anything the
   document already claims. New test drives both through the public component.
4. **P2 — the accessibility test was vacuous.** `title` alone satisfies an
   accessible-description query, so the test would have stayed green with
   `aria-describedby` removed. It now asserts the attribute and resolves it to
   the element it names. Confirmed non-vacuous by deleting the `setAttribute`
   line and watching it fail.
5. **P2 — spec claims the diff does not support.** Four corrected in `spec.md`,
   each marked as a post-review correction: criterion 6 named a non-string-URI
   test that does not exist in any commit; criterion 12 required
   `pnpm prettify:check`, red at baseline; criterion 14 required the whole e2e
   suite, red at baseline; and the Risks section claimed the `detail` disclosure
   "discloses nothing to anyone who could not already read the store", which the
   review correctly refuted — loopback binding and Origin/CSRF checks are
   network and CSRF controls, not caller authentication, so a local process
   with no read access to the store can still query the server. The narrower,
   accurate threat model is now stated and accepted rather than argued around.
   The review also confirmed there is no markup-injection path: the values go
   through `title` and `textContent`, never `dangerouslySetInnerHTML`.
6. **Criterion 7 was verified against the wrong node.** The original evidence
   compared `tcw validate` on _this_ repo, which has no connected projects and
   therefore no off-board reference at all — so it could not have exercised the
   criterion. Re-run properly on the three-node fixture, whose document does hold
   off-board references, with `tcw/` at `5ecdb9a` and then at `HEAD`: output
   identical, and the off-board references are absent from the problem list both
   times, while the deliberately-broken ones are present both times.

**Noted, not fixed:** the review's remaining test-coverage points — an untested
empty batch beyond the new call-count test, an over-cap test that checks only the
result count, and no serve-level test that drives a store _exception_ through the
`detail` branch. The last is the one worth having, since that branch is the
security-relevant one; it needs a way to make a store raise from inside a live
server thread, which is a bigger fixture than this item should grow. Recorded
here rather than silently skipped.

**Rejected:** nothing. One correction to the review: it noted `resolve_tcw_ref`
has no path producing `ok=True` with `key=None`, which matches what the code
does — that was a hypothesis in the prompt, not a claim in the spec.

## What the plan and spec got wrong

**1. Task 4's target document has no `tcw://` links.** The plan said to open this
item's own request document, "which carries a `tcw://W/…` reference the board
does not host". It does not — the request document mentions `tcw://` only in
prose and inline code, and this repo has no `connected-projects`, so it has no
unhosted references at all. A fixture had to be built: three connected nodes
(`platform` → `orchestrator` → `webapp`) with one document holding all four
situations at once.

**2. The plan's fixture surface was broken, by a defect that predates this
change.** The first fixture put the four links in a _work item body_ and read it
from the Initial Request tab. Nothing rendered — not the new treatment, and not
the pre-existing `tcw-inert` one either. Verified against the pre-change bundle
by checking out `5ecdb9a`'s `tcw/serve/dist` and reloading: identical failure, so
it is not a regression from this item. Filed as
`docs/work/inbox/2026-08-24-tcw-link-resolution-never-applies-on-a-work-items-document-tab.md`
with the measurements (one `/api/resolve` at ~95ms, zero anchor mutations,
article children replaced underneath the effect). Root cause **not** confirmed;
the note says where to look and says not to guess the fix.

The visual check was then done on a **capability** page, where the resolution
pass works correctly. That is a real user-facing surface, so Task 4 is genuinely
satisfied — but the item's behavior is invisible on the work-item tab until that
separate defect is fixed. **This is the open question for `verify`.**

**3. Spec criterion 12 is not satisfiable and never was.** (Also raised by the
review; the criterion is now corrected in `spec.md`.) It requires
`pnpm prettify:check` to be clean. It fails on `main` at `5ecdb9a` with the same
104 files it fails with now — pre-existing, mostly `tests/fixtures/`. The three
source files this change touches _are_ clean (`pnpm prettier --check` on them
passes); `README.md` was already prettier-dirty before this change and was left
that way rather than reformatting the whole file into this diff. The criterion
should have been checked when it was written; it was asserted, not run.

**4. Spec criterion 14 is likewise false at baseline.** `pnpm test:e2e` does not
pass on `main`: `parity.spec.ts:332 › searches references and surfaces targeted
validation warnings` times out at line 392 waiting for "Saved with validation
issues", and 6 tests then do not run. Confirmed pre-existing by running the full
e2e suite against `5ecdb9a`'s code — same test, same line. The 7 tests that do
run pass, and no snapshot moved. The criterion assumed a green baseline from
reading snapshot filenames rather than from running it.

**5. The plan's new test names duplicated tests that already existed.** It named
`test_resolve_reports_an_unhosted_descendant` and
`test_resolve_reports_an_unhosted_ancestor`; `test_resolve_descendant_work_gated`
and `test_resolve_ancestor_work_is_unhosted` already covered those cases against
the old bare `{"ok": false}`. They were tightened in place instead, and the
ancestor one was extended to run under both `include_descendants` settings as the
plan intended. Only the shape test (criterion 5) was genuinely new.

## Task 4 — what was seen

Fixture: `orchestrator` serving on a loopback port, with `platform` registered as
its parent and `webapp` as its child; one capability body holding an off-board
reference in both spellings, a resolvable local reference, a dangling one, and a
malformed one, with two of them mid-paragraph.

Confirmed from the live DOM (re-run after the rework, since removing the `href`
changes what the browser styles by default):

```
off-board (both spellings) -> class tcw-unhosted, badge "platform",
                              title + aria-describedby
                              "Project platform is not included in this board"
resolvable                 -> data-nav-key "viewer/read-a-document", no class,
                              href rewritten to /capabilities/viewer/read-a-document
dangling                   -> class tcw-inert, title "no capability: viewer/does-not-exist"
malformed                  -> class tcw-inert, title "malformed tcw:// uri"

every failed reference     -> no href, address preserved in data-tcw-ref
clicking an off-board one  -> location unchanged, cursor computes not-allowed
```

Both themes were checked by switching Appearance → Light and → Dark. In each, the
amber warning colour, the ⚠ glyph and the project badge are legible and clearly
separate from the grey struck-through broken links and from the blue live link;
the markers are findable by scanning a paragraph without hovering, which is the
property the request asked for. Light-theme amber on white is the lower-contrast
of the two — it is Radix's accessible `-11` text step, so it meets the scale's
own contract, but it is the thing to look at first if anyone finds it faint.

## Notes

- **At this first pass, two pre-existing defects were found and filed, not
  fixed; both were later absorbed and fixed in the passes recorded below.** The
  second is
  `docs/work/inbox/2026-08-24-a-dangling-bare-work-slug-resolves-ok-so-validate-never-flags-it.md`:
  `resolve_tcw_ref` checks existence for `T` and `C` but not for a bare `W` slug,
  so `tcw://W/anything` resolves `ok: true`, `tcw validate` never flags a dangling
  local work reference, and the viewer rewrites it into a link that 404s. Found
  while building the fixture — the "dangling" link chosen for it turned out not to
  be dangling as far as the resolver was concerned.
- **`_hosted_projects()` is taken at most once per batch**, lazily, on the first
  foreign reference. It previously ran once _per foreign reference_, up to
  `RESOLVE_MAX_URIS` (256) times. (Corrected after review round 2: this paragraph
  still described the _eager_ hoist — "walks once instead of zero times" — which
  was true of the first pass and removed by `634cf05`, restoring the zero. The
  sentence outlived the code it described, which is the drift the review exists
  to catch.)
- **The `tcw` CLI was used throughout**, against the standing preference for inbox
  documents while `tcw/` is being modified. `tcw/cli.py` imports `tcw.serve` at
  module load, so the edited module is loaded by every `tcw` command; it was kept
  importable at every commit and the CLI misbehaved at no point. The two findings
  above were filed as inbox documents rather than through `tcw work new`.

---

# Second pass — the absorbed work-tab defect

Follows `rework.md`, not the plan: verification rejected the item so it would
absorb the defect that kept its result off the surface work items are read on.

## Root cause

Found, not guessed — the rework file was explicit that a plausible mechanism is
not a diagnosis, and the one it suggested turned out to be only half the story.

`Markdown` (`web/client/src/ui/shared-components.tsx`) queried the container for
`a[href^="tcw://"]`, posted them to `/api/resolve`, and then applied the answers
**to the anchors it had captured before the request**. Instrumented in a test:

```
EFFECT RUN, anchors: 1
THEN RUN, connected: false   data keys: ["tcw://W/orchestrator/2026-01-01-x"]
```

The response is correct and arrives; the nodes it is written to have left the
document. Nothing errors, and the effect does not re-run, because `[html,
resolveLinks]` never changed — a re-render replaced the content with
byte-identical HTML. That is why the browser showed exactly one `/api/resolve` at
~95ms and zero anchor mutations: the request in the network log looked like proof
the feature had run.

`work-document-tabs.tsx` triggers it on every mount. Its
`useEffect(…, [item.slug])` resets state with a fresh `{}`, and a child's effect
runs before its parent's — so the resolve request is always in flight when that
re-render lands. Confirmed by deleting `setArtifactStates({})` and watching the
reproduction test go green.

## The fix, and why it is not in `work-document-tabs.tsx`

The response handler re-queries the container instead of trusting the captured
nodes (`ed59223`). That is the shared point every call site routes through, so
one edit restores the work, capability, and taxonomy surfaces together. Fixing
the parent's state reset would have made this symptom go away while leaving the
next parent that re-renders mid-request broken in exactly the same silent way —
the `tcw-inert` and `data-nav-key` paths were equally dead here, which is the
tell that the defect was never about the new rendering.

`setArtifactStates({})` still allocates a fresh object per mount. It is a wasted
render, not a defect, and it is left alone.

**The residual, stated rather than pre-solved:** a replacement landing strictly
_after_ the response is applied would still wipe the treatment, and the effect
still would not re-run. Not observed, and not reproducible in a test, so nothing
guards it.

## Evidence

- `web/client/src/ui/work-document-tabs.test.tsx` gained a reproduction that
  mounts the real component with a body containing a `tcw://` link. **Written
  first and watched fail** against the pre-fix `Markdown` (timed out waiting for
  `tcw-unhosted`), then green. The existing `Markdown` tests pass either way —
  they render the component directly and never touch the tab, which is how this
  survived.
- In the running app, on a work item's Initial Request tab: both off-board
  spellings carry `tcw-unhosted` + the `orchestrator` badge + the sentence, the
  dangling one carries `tcw-inert` + `no such work item: …`, the malformed one
  `malformed tcw:// uri`, and the resolvable one **navigated in-app** from that
  tab — `/work/2026-03-01-…` → `/work/2026-02-01-local-sibling-task`. That
  navigation was dead before this pass too.
- `docs/work/inbox/2026-08-24-tcw-link-resolution-never-applies-on-a-work-items-document-tab.md`
  was deleted when the rework absorbed it; its measurements live in `rework.md`.

## Gates at this pass

- `pnpm test` — **60 passed**, 11 files (the tab reproduction, plus the two the
  second review round forced).
- `pnpm exec tsc --noEmit`, `pnpm lint`, `pnpm check:build` — all exit 0.
- `pytest` — **1959 passed** in 496s, re-run after this pass rather than reasoned
  about. No Python changed here, but the tree did, and asserting which tests read
  which files is the kind of claim that turns out false.

## What the rework file got wrong

Its hypothesis — the parent's `{}` reset — was the _trigger_, and it named the
right file. It was not the _cause_: the cause is `Markdown` holding node
references across an await, and a fix aimed only at the trigger would have been
the wrong fix in the right file. Recorded because the rework file explicitly told
the next pass not to treat that hypothesis as a diagnosis, and it was right to.

## Review round 2

Run against `5ecdb9a..HEAD` after the first round's fixes, on the standing rule
that a fixed round is not a passed round. It returned **NOT DONE**, and its P1
had been **introduced by round 1's own fix** — the failure mode worth naming:

- **P1 — the duplicate-badge guard could delete authored content.** Round 1
  replaced a class-based guard with one keyed on a `data-tcw-badge` marker, which
  removed the marked sibling _and the element after it_. A document containing
  `[ref](tcw://…)<span data-tcw-badge></span><em>keep me</em>` lost both. A
  DOM-visible attribute cannot establish ownership.

    Fixed by **deleting the guard**, not by hardening it. It defended a condition
    that can no longer arise: since `ed59223` the loop selects
    `a[href^="tcw://"]` from the live DOM at response time, and every anchor it
    treats has had its `href` removed — so the same anchor cannot be reached twice.
    Two rounds of increasingly clever defense for an impossible case, and the
    defense was the only thing that ever broke. Round 2 also noted this same
    change closes its other finding, the `getAttribute("href")` re-entrancy hole:
    a re-queried anchor has an href by construction.

- **P2 — the id-collision test did not test the id-collision fix.** It authored
  `id="tcw-off-board-0"`, but earlier tests had already advanced the module
  counter past 0, so reverting collision-avoidance still minted a free id and the
  test passed. `freeNoteId()` now counts from zero against the document on every
  call, with no module state — which makes the outcome deterministic, so the test
  pins the exact id (`tcw-off-board-1`) that an authored `-0` forces. Watched red
  against the counter version.

- **P2 — spec criterion 9 still required `getByRole("link", …)`,** the semantics
  `neutralize()` deliberately removes. A criterion demanding the thing the change
  set out to remove would have blessed the defect it was written to prevent.
  Corrected.

- **P2 — `outcome.md` described the eager hoist that `634cf05` had removed** —
  "walks once instead of zero times", true of the first pass only. The sentence
  outlived its code. Corrected.

- **Narrowed rather than fixed:** the review held that `README.md` and the
  release note overclaim, because a bare `tcw://W/<slug>` naming no existing item
  still resolves and is rendered as a live link. That is the second filed
  defect, out of scope here; both documents now say so explicitly rather than
  implying coverage this change does not have. (Its other overclaim point — that
  the work-document tab shows none of this — was already obsolete: `ed59223` had
  landed while the review was reading, which the review itself noted.)

Both new client tests were watched red against the round-1 code before being
accepted. A third round is running over these fixes; the pattern of each round
finding a hole in the previous round's fix is the reason it is running rather
than being declared unnecessary.

## Review round 3

**NOT DONE**, with one P1 again inside the previous round's fix — the third round
in a row where the newest change carried the newest defect.

- **P1 — a stale response could consume a newer render's anchors.** The re-query
  in `ed59223` fixed writes landing on detached nodes, but introduced the mirror
  problem: source A's request in flight, source B renders, **A answers first**,
  re-queries B's anchors, finds no entry for B's uris, and marks them all
  unresolved — stripping their hrefs, so B's own answer finds nothing left to
  repair. Reachable by switching document tabs. The effect now sets a
  `superseded` flag in its cleanup, which React runs before the next effect, and a
  superseded response is dropped.

    The first test written for this **passed without the fix** and was thrown away:
    it released A's response _after_ B's, in which order B has already stripped the
    hrefs and A's re-query finds nothing to damage. The race only exists when A
    lands first. Rewritten with both responses gated so the order is explicit, it
    fails without the guard on `Expected the element not to have class: tcw-inert`.
    A vacuous test here would have shipped the P1 with a green suite over it.

- **P2 — the capability delta was framed as a contradiction when it is an
  extension.** Criterion 15 required _deleting_ the sentence "unknown,
  unregistered, or dangling foreign targets remain inert" from
  `docs/capabilities/web/description.md`. That sentence is still true — those
  targets do remain inert, and now say why. Deleting it would have made the
  ledger less accurate, not more. Criterion 15 and the Capability changes section
  now describe an extension, which is what the closeout flip will apply.

- **P2 — the residual was stated as the only one.** `spec.md` and `outcome.md`
  called a post-response replacement the sole remaining hole while the P1 above
  was open. Corrected; the surviving residual is stated as what it is.

- **P2 — the release note claimed three tabs, evidence covered one.** Only the
  Initial Request tab was tested and looked at. Narrowed to what was verified,
  with the shared rendering noted rather than asserted as verified.

- **Acknowledged, not fixed:** the exact-id assertion added in round 2 fails
  against the old module-global counter only in full-file order, not run in
  isolation, so it proves collision avoidance but not the removal of module
  state. Contorting it further buys less than it costs; recorded instead.

The review's own verdict: **not converged** — "one more adversarial round after
adding response ownership/cancellation and an overlapping-source test is
worthwhile." Both of those now exist, which is precisely what round 4 would be
reviewing. That decision is the user's, and is put to them rather than taken
here.

---

# Third pass — the absorbed resolver defect

The user absorbed the second filed defect too. `docs/work/inbox/` is now empty of
this item's findings; both are in the item.

## What was wrong

`resolve_tcw_ref` asked "does this exist?" of two axes and not the third
(`tcw/refs.py`):

- `T` → `FsTaxonomyStore.get(ref)`, `None` → not ok
- `C` → `FsCapabilitiesStore.get(ref)`, `None` → not ok
- `W` → `resolve_qualified_work_ref(...)`, whose answer is **which store
  addresses this ref**, not whether the item is in it

Only the status-path spelling ever checked, inside
`resolve_qualified_work_ref` itself. The bare spelling — the one people actually
write for a local item — did not, and neither did the cross-node one. Both
returned `ok`:

```
tcw://W/2026-01-01-never-created              -> ok=True   key='2026-01-01-never-created'
tcw://W/proj/2026-01-01-never-created         -> ok=True   key='proj/2026-01-01-never-created'
```

Wider than the filed note said, which claimed only the bare form. So
`tcw validate` passed a dangling work reference without comment, and the viewer
rewrote it into an in-app link that 404s — the dead-end link `resolve_tcw_ref`'s
own docstring says the design exists to prevent.

This is not a decoration on the rest of the item: the failure-reason work is
worth less while the resolver is wrong about _which_ references are broken.

## The fix

The `W` branch confirms the item exists and, when it does not, returns the
message `qualified_work_ref_problem` already produces. `resolve_qualified_work_ref`
is deliberately untouched — it answers store location, which is what
`tcw serve`'s `_resolve_work` wants, and changing it would have altered routing
for a question about resolution.

## Evidence

- Two tests in `tests/test_refs.py`, written first and watched red:
  `assert True is False … ResolveResult(ok=True, axis='W', key='2026-01-01-never-created')`
  and the same for the registered-project spelling.
- End to end, on the fixture:

    ```
    [orchestrator] docs/capabilities/viewer/follow-a-reference/description.md:
      tcw:// tcw://W/2026-01-01-never-created → no such work item: 2026-01-01-never-created
    ```

    `tcw validate` did not report that before. It is the defect's headline
    consequence and now it is caught.

- `tcw validate` on **this** repo still exits `0` — the stricter resolver finds
  nothing dangling in a tree it now checks properly, so the change is not
  retroactively breaking the repo's own documents.
- `pytest` — **1961 passed** in 459s. Making a core resolver stricter is exactly
  the change that breaks something elsewhere; nothing broke, and the run is the
  evidence rather than the reasoning.

---

# Review round 4 — final adversarial split

The fourth round found no subject code defect in either primary target.

## Supersession guard

- Cleanup can run after the response promise settles but before its reaction is
  executed; the reaction then observes `superseded` and returns before touching
  the DOM. Once the reaction starts, JavaScript run-to-completion means cleanup
  cannot interleave between the guard and the mutation loop, so a dropped answer
  cannot leave a neutralized anchor, badge, note, or `aria-describedby` half
  applied.
- The round-2 live-DOM fix remains intact. When identical dependencies leave the
  effect mounted while the DOM is replaced, cleanup does not run, `superseded`
  remains false, and the response still re-queries and updates the live anchors.
- The stale-first test is non-vacuous. With only `if (superseded) return` removed,
  it failed at the pre-release assertion because the current anchor had acquired
  `tcw-inert`. Restored, the focused test passed as part of the full web unit run.

## Work-reference existence

- `resolve_qualified_work_ref` and `tcw serve` routing remain unchanged. Only
  `resolve_tcw_ref` asks the returned store whether the item exists, so
  `_resolve_work` keeps its permissive store-location contract while
  `/api/resolve` and `tcw validate` get strict object resolution.
- Bare, correct status-path, registered-project, and both foreign URI spellings
  resolve through the same check. Missing local and registered-project items use
  `qualified_work_ref_problem`'s `no such work item` message; an unregistered
  qualifier names the missing project; a wrong status locator names the locator
  that does not exist. Completed and discarded items still resolve in both bare
  and matching status-path form.
- `FsWorkStore.get` may raise for duplicate items, interrupted claims, or I/O;
  `resolve_tcw_ref`'s existing exception boundary converts those into `ok: false`
  instead of aborting a link scan.
- Reverting only the new `store.get(bare)` block made both new tests fail with
  `ResolveResult(ok=True, ...)`, proving both gates cover the fix.

## Decisive finding split

**Belongs to this change's subject, fixed here:** the lifecycle record named a
nonexistent `_work_store_for` helper instead of `_resolve_work`, retained stale
badge-guard and capability-delta claims, and had not yet reconciled the two
declared capability descriptions. The spec, plan, outcome, and capability ledger
now describe the code that exists; `tcw capabilities check` passes.

**Needs a different mechanism / separate item:** the existence check is
O(work references × work items), because each `FsWorkStore.get` scans the work
tree. In this checkout (148 items), 100 distinct missing references took about
0.716 seconds and 100 repeats about 0.699 seconds; `/api/resolve` accepts 256
URIs. Correctness is retained here, and a request/validation-scoped index or
batch resolver is filed as
`2026-08-25-avoid-rescanning-work-items-for-every-tcw-work-reference`.

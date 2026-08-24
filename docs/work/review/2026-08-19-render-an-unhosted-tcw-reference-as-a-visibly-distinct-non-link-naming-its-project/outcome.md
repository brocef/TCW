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

5b (the capability wording flip) is deliberately not done yet: it belongs at
`complete`, per the plan.

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

- **Two pre-existing defects were found and filed, not fixed.** The second is
  `docs/work/inbox/2026-08-24-a-dangling-bare-work-slug-resolves-ok-so-validate-never-flags-it.md`:
  `resolve_tcw_ref` checks existence for `T` and `C` but not for a bare `W` slug,
  so `tcw://W/anything` resolves `ok: true`, `tcw validate` never flags a dangling
  local work reference, and the viewer rewrites it into a link that 404s. Found
  while building the fixture — the "dangling" link chosen for it turned out not to
  be dangling as far as the resolver was concerned.
- **The hoist of `_hosted_projects()`** out of the per-URI loop is a behavior-
  neutral change with one honest cost: an aggregating server whose batch contains
  no foreign references now walks the descendant nodes once instead of zero times.
  It previously walked them once _per foreign reference_, up to
  `RESOLVE_MAX_URIS` (256) times. Recorded in the changelog under Internal.
- **The `tcw` CLI was used throughout**, against the standing preference for inbox
  documents while `tcw/` is being modified. `tcw/cli.py` imports `tcw.serve` at
  module load, so the edited module is loaded by every `tcw` command; it was kept
  importable at every commit and the CLI misbehaved at no point. The two findings
  above were filed as inbox documents rather than through `tcw work new`.

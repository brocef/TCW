# Outcome — Configure an external tracker and read its tickets

Built 2026-09-12 and 2026-09-13. Eight commits of code, tests and documentation on
top of the three artifact commits. Full suite green at every commit boundary, ending
at **2811 passed**, up from 2657 before this item.

## What shipped

| Part | Where |
| ---- | ----- |
| `work.tracker` config: `TrackerConfig`, `parse_tracker_config`, `tracker_config` / `tracker_problems` on `WorkStore` | `tcw/store/base.py`, `tcw/store/fs.py` |
| Problems reach `tcw validate`, read directly rather than through `check()` | `tcw/validate.py` |
| Jira Cloud client on the standard library, one `_request` seam, four reads | `tcw/tracker/jira.py` |
| Six exception types, one per cause, each with its own message | `tcw/tracker/jira.py` |
| Claimability and exclusivity, pure | `tcw/tracker/claim.py` |
| `tcw work tracker list` and `show`, read-only | `tcw/work/cli.py` |
| Replay fixtures captured from a live site and scrubbed | `tests/fixtures/tracker/` |

Six test files, 154 new tests. No runtime dependency added: `pyproject.toml` is
unchanged, and `find_packages(include=["tcw*"])` already covered the new
subpackage, which was checked rather than assumed.

## Deviations from the plan

1. **The error taxonomy landed with the seam, not after it.** The plan made them
   tasks 3 and 4. A seam that cannot raise coherently has undefined error behaviour,
   so splitting them would have left an intermediate commit in that state. Task 4
   became the taxonomy's tests, including the real-socket test it was always going to
   carry.
2. **The aggregate claim-name check was built and then deleted.** Not in the plan at
   all; it was an attempt to save a spec claim that live testing disproved. See
   below.

## Corrections to the spec, all found by building or by running

The spec was revised five times during implementation. Each correction is in the
spec itself; they are collected here because the pattern matters more than any one
of them.

1. **The exclusivity asymmetry.** The spec said exclusivity is answerable whenever a
   ticket sits in the status the claim leads to. A ticket only reveals that
   destination by *offering* the claim, and a ticket already in the destination no
   longer offers it. So one ticket can prove a workflow is not exclusive and can
   never prove it is. Found by a test failing; fixed by taking the destination as an
   optional argument for a caller that knows it, not by weakening the test.
2. **`/rest/api/3/search` has been removed by Atlassian.** A live call returns 400
   naming `/rest/api/3/search/jql`. The replacement is token-paginated and reports
   `isLast` rather than a count, so `SearchResult` carries no total and the command
   says "there are more" instead of printing a number it cannot know. A reviewer had
   raised this as a question deferred to the plan; running the code answered it in
   one call.
3. **Detecting a wrong `transitions.claim` name is not possible here, and the spec
   claimed it was "the highest-value thing this item does".** A ticket that does not
   offer the claim may simply have been claimed already. The obvious repair — warn
   when no ticket in the query offers it — was built, run against the conforming
   fixture, and reported a typo on a configuration that was correct, because every
   ticket there had been claimed during the earlier experiment. Reporting a typo on a
   correct configuration is worse than reporting nothing. The heuristic is deleted,
   the verdict name is kept deliberately unreachable, and a test records why. Real
   detection needs the workflow definition and belongs to C4, which must now treat it
   as required rather than optional.
4. **Criterion 1 was unachievable in two successive wordings.** Comparing output to a
   branch point cannot work: this item's own artifacts and its capability flip change
   what `validate` scans. A seeded fixture is no better — `evals/seed_fixture.py`
   documents that two runs are deliberately not byte-identical. The property those
   wordings were reaching for is that the tracker modules are never imported, which
   is strictly checkable.
5. **The authoritative workflow read left this item entirely**, before code started,
   on review. Four verified reasons: no severity tier on `tcw validate`, a named
   reporting command that does not exist, no configuration key identifying a project,
   and `tcw validate` being a `pre` hook on `complete` — a network call there would
   make completing a work item depend on Jira being reachable.

## Mutation checks

Every assertion that carries a guarantee was broken on purpose and confirmed red.

| Property | Mutation | Result |
| -------- | -------- | ------ |
| `tcw validate` makes no network call | inject a connection | 3 red |
| Every operation passes a timeout | drop it from the shared helper | 5 red |
| New operations cannot escape the timeout check | add an unlisted fifth operation | 1 red |
| No cause is inferred from a response body | branch on the body | 2 red |
| The two claim words never collapse | make them equal | 5 red |
| Each error cause has its own message | collapse them | 7 red |
| No credential reaches output | print the token | 1 red |
| Tracker modules are never imported | hoist the import to module scope | 5 red |

**One of those checks caught a test of mine lying.** The import guard, written
in-process, did *not* fail when the import was hoisted: the CLI module is already
imported before the test body runs, so clearing the module cache and calling the
entry point again never re-executes its module-scope imports. It looked like a strong
guarantee and was worth nothing. Rewritten as a subprocess per command, it fails on
all five under the same mutation. This is the single most useful thing mutation
testing did here.

## Live verification

Run against the two fixture projects created for the epic. Recorded here because the
suite cannot settle any of it.

- `tracker list` returns the six tickets of the conforming project with status,
  assignee and summary.
- `tracker show` on a ready ticket: `claimable: claimable`, workflow
  `not determined`, with a note naming where the claim leads.
- `tracker show` on a claimed ticket: `claimable: not claimable`, and an
  informational note listing what the ticket does offer.
- `tracker show` on the non-conforming project, ticket in the landing status:
  `workflow: not exclusive`, with the explanation that applying the transition twice
  succeeds. This is the failure the item exists to surface, observed live.
- Each of those four responses is now a scrubbed replay fixture.

## Not verified

- **Team-managed (next-generation) Jira projects.** Both fixtures are
  company-managed. The issue-level transitions endpoint is expected to behave
  identically, which is part of why that route was chosen over the workflow
  definition, but it was not tested.
- **Whether a non-administrator can read a workflow definition.** No longer this
  item's concern, since that read moved to C4. C4 should settle it with a non-admin
  token before designing around the route. An attempt to settle it from the
  documentation failed because the page truncated, and no non-admin account was
  available.
- **`tcw work complete` offline on a tracker-configured node.** Criterion 7 proves
  the mechanism — `tcw validate` makes no connection and reads no credential
  variable — but the end-to-end behaviour was not exercised by hand.

## Two environment findings worth keeping

1. **The `tcw` on PATH is not this worktree.** It runs the primary checkout, because
   the editable install pins an import hook there. The existing documented-surface
   test shelled out to it and therefore measured whether the *installed* CLI matched
   *these* docs, so a command added in a worktree read as nonexistent. Fixed by having
   the test invoke its own repository. The alternative the project guide suggests —
   re-pointing the global install — was rejected because other sessions on this
   machine share it.
2. **The installed package is `tcw` 0.10.3 pinned to the primary checkout**, while
   the project is at 2.0.3. That is the stale version-mismatched hook the guide warns
   shadows the right one. Untouched, and filed as an inbox note.

## Follow-up: two notes that overstated what one ticket shows

Reported in the side notes of GitHub issue
[#36](https://github.com/brocef/TCW/issues/36) (2026-09-14, @brocef), from a
hand run on tcw 2.1.1 through Triage → To Do → In Progress → Done. The rest of
that issue is tracked separately as
`2026-09-14-inherit-work-tracker-from-parent-nodes-key-by-key`. Both notes are
`Assessment.detail` strings in `tcw/tracker/claim.py`, and both were reworded on
2026-09-14 in a worktree merged to `main`.

1. **The claim-not-offered note named two cases, and there are three.** For a
   ticket in Triage it said the name is wrong "or this ticket is past the point
   where it applies". That ticket had not reached the point yet. The note now
   says the ticket "has not reached it yet, or is already past it".
2. **The leads-to note implied a second `show` would answer exclusivity.** `show`
   never passes `landing_status` to `assess()`, so on an exclusive workflow the
   landed ticket still reports "not determined"; the reporter's second `Start`
   was refused by Jira with HTTP 400. The note now says a landed ticket can show a
   workflow that is not exclusive but never one that is, and that exclusivity "is
   confirmed only when a claim is made, or from the workflow definition". The
   reporter suggested "at claim time"; the wording covers both a refused claim in
   Jira today and the claim command C2 will add.

| Commit | What |
| ------ | ---- |
| `cbbcd72d` | Both notes reworded; two tests in `tests/test_tracker_claimability.py`, each asserting the new wording and the absence of the old. Both were run red against the old wording first. |
| `29394fd7` | `docs/guide/work.md` and `skills/tcw-work/references/commands.md`, which repeated both two-case explanations; changelog and release-note entries in `upcoming.md`. |

Full suite: **2814 passed** (`python -m pytest`, from the worktree, with the
worktree's own `tcw` confirmed as the one imported).

**What the spec and the first build got wrong here:** the build's live
verification ran `show` on a ready ticket and a claimed ticket, but never on a
ticket *before* the claim applies, so the third case was never seen. And the
leads-to note was written from the exclusivity asymmetry the spec correction
already recorded (correction 1 above) without applying that asymmetry to its own
wording.

## Version

This section said "not cut" when it was written. The code has since been
released: the tracker commits are in `v2.1.0`, which never reached PyPI, and
`v2.1.1`, which did. The #36 follow-up is not yet in any release; it waits in
`docs/{changelogs,release-notes}/upcoming.md` for the next version cut.

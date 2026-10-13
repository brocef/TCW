# Refined outcome — TCW-71: the Jira work backend

**Accepted** on 2026-10-13 under the TCW 3.0 epic's rule: a child item is
approved at verify when it passes a bounded adversarial review (the owner,
2026-10-02: "You can also consider work approved if it passes adversarial
review, I will not review anything until we finish the epic"). The confirming
round ended `DONE`.

## What was accepted

Everything in `outcome.md`: the Jira work backend for 3.0, with Jira owning
status and the request, `tickets list`/`tickets adopt`, delegation into Jira
projects, and `validate --remote`. All 27 acceptance criteria are met. AC 23
and 24 were met on 2026-10-13 by the live check (`live-check.md`), which ran
after the owner had `TCWTEST` prepared through the Jira API
(`tcwtest-checklist.md` records every object created).

## The live check

Six runs of the scenario against `TCWTEST`. The last two passed every step and
`validate --remote` exited 0. The sixth ran on the final code, after the review
fixes, with the same answers as the fifth. What it changed:

- **A defect:** Jira answers 204 to a comment sent with a transition that has
  no screen, and discards it. A qa rejection's reason was lost. `set_stage` now
  posts such a note on its own; spec Design 5 amended.
- **A false error:** `validate --remote` required Parent on the Epic edit
  screen, which Jira never offers. Spec check 2 amended.
- **The fake was wrong about Jira** on four points: a JQL status the site lacks
  matches nothing (no 400); expanded transitions always carry `fields`, empty
  for a comment-only screen; create-screen fields carry `key`; the top-level
  type has no Parent field.
- **Two gaps in the checklist:** Epics needed the TCW workflow and fields too.

## Reviews

**Earlier rounds (2026-10-08), over Tasks 2–17:** round 1's findings are listed
in commit `5888f0a7` (accepted 1–4, 6, 7, 9; narrowed 5). The confirming round
narrowed adopt's two resume cases (`f65bb31f`; spec 7.2, `62b37183`), and the
owner closed that review by decision after two rounds.

**Verify review (2026-10-13), over the live check's changes
(`f65bb31f..9ddb0c3c`):**

| # | Finding | Decision |
| - | ------- | -------- |
| 1 | `_edit_screens` called `metadata()`, which raises on a missing configured field and stopped checks 3–5 (a regression from the Epic fix) | Accepted; fixed in `a40d4d22` |
| 2 | Recorded files held Gravatar avatar URLs, which hash an email address | Accepted; scrubbed, test rejects them, the unpushed commit that added them amended so the hash is in no history (`3d36c029`) |
| 3 | A test went vacuous when the fake stopped refusing unknown statuses; a stale comment; unused code | Accepted; fixed in `a40d4d22` |
| 4 | After a lost race on a screenless move, a matching older comment suppressed the note | Accepted; fixed in `bc24aaee` |
| 5 | "Top level" taken from this project's types could spare a Task Parent | Narrowed: only a top level of 1 or more is spared (`a40d4d22`) |
| 6 | Paths the backend reads were missing from the shape test | Accepted; adding them found two more fake gaps, fixed in `1bdf9da3` |
| 7 | Probes left `tcw-test`/`live` values on tickets | Accepted; probes clear them, and the 20 left by earlier runs were cleared in Jira |
| — | Spec silent on the separate note's refusal and drop cases; changelog silent on the live-check changes | Accepted; spec `ec0bcd38`, changelog `9ddb0c3c` |

None rejected. Each code fix has a test that fails when the fix is undone.

**Confirming round:** all seven fixes correct, no new defect, `DONE`. Its
separate-change list, folded in here as small (`89ff245d`, spec `fcb77128`):
the top-level type is spared Parent on its create screen too; `field_id`'s
`key` fallback is tested; the spec states the level-1 guard.

## Follow-ups

Two inbox entries (`817ddc8a`):

- `2026-10-13-settle-the-jira-live-check-questions-that-need-a-second-account`:
  translated status names, and whether a non-administrator can read the
  workflow definition.
- `2026-10-13-tidy-what-tcw-71-s-reviews-left-for-the-jira-backend`: the
  note-after-a-drop message, three Jira shapes `TCWTEST` could not show, and
  `timeZone`/`locale` in recorded files.

## Deferred, by the owner's instructions for this epic

- The full suite runs near the end of the epic. Here: `tests/work/jira`, 633
  passed, 1 skipped (the live test, run by hand).
- Documentation beyond the release-notes and changelog entries goes to TCW-74
  and TCW-75, as the spec's non-goals say.

## Capabilities

The three new records and the changed delegation record were written on the
branch (Task 16) and pass the records gate there (`outcome.md`). They reach
`main`'s ledger only when the epic merges, so on `main` they cannot resolve:
`tcw work complete` refused them, and with `--force` its `tcw validate` pre
hook refused the same four. The item was therefore completed by hand, as the
plan's notes say and as TCW-69 and TCW-70 were: the folder moved to
`completed/` with `resolution: done`, a graveyard entry, the folder deleted
with its location recorded, and the Jira ticket moved to Done.

## Closeout route

The branch `work/2026-10-01-tcw-71-…` fast-forwards `epic/tcw-3.0`; its worktree
and branch are then removed. `main` receives 3.0 only when the epic ends. No
GitHub issue originated this item.

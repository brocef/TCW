# Refined outcome: claim an external tracker ticket and bind it to a work item

## Decision

**Accepted, 2026-09-14, by the user**, on the condition that the dropped-connection
gap the verification found was fixed before closeout. It was, in `6afd795e`. The
user's answers at this stage:

- **Verdict:** "Accept, but fix the connection gap first".
- **Merge:** `tcw work complete` merges the worktree branch into `main`; no push.
- **Version:** keep the current version; entries stay in `upcoming.md`.

Accepting also accepts the two deviations the assessment put to the user:

1. **`tcw validate` checks `tracker.yaml`** (`c1bd4b62`). A binding that is not a
   YAML mapping is reported like any other TCW record, so a hand-broken binding
   fails validate and therefore the `pre` hook on `complete`. The spec's non-goal
   wanted to avoid that; `outcome.md` item 1 has why it was the only route that did
   not edit an existing test assertion.
2. **`tcw work tracker unlink` with no `--reason` exits 2** (argparse's missing
   required option), where criterion 15 said 1. An empty `--reason` exits 1.

## Evidence

**Assessment:** the `tcw-verifier` agent, read-only, against the worktree at
`a630b800`, run from the worktree root with `import tcw` confirmed to load the
worktree.

- Tracker, validate, documented-surface and serve-write tests: **638 passed**.
- `tcw capabilities check` → `capabilities OK`; `tcw validate` (worktree code) →
  `validate OK`.
- `claim()` (`tcw/tracker/intake.py`) matches the spec's step 1, 2 and 3 tables row
  for row: assign only after an applied transition, read-back requires the landing
  status, row 1f carries no assign advice.
- No credential, e-mail address or real account id in any added file under `tests/`
  or `docs/`.
- Where a criterion was tested only at claim level (3, 4, 5, 7, 8, 9, 13), the
  verifier also ran the command end to end against the fake, in throwaway nodes, and
  each behaved as specified.

**After the fix,** run in this session:

- `tests/test_tracker_client.py::test_a_server_that_drops_the_connection_is_unavailable_not_a_crash`
  failed first with `http.client.RemoteDisconnected: Remote end closed connection
  without response`, then passed after `6afd795e`.
- `tests/test_tracker_client.py`, `test_tracker_claim.py`, `test_tracker_cli.py`:
  78 passed. `tests/test_documented_cli_surface.py`: 225 passed.
- **Full suite at `46b8b06a`:** **2919 passed** in 14m43s, in a throwaway checkout of
  that commit.

**Live** (recorded in `outcome.md`): criteria 11 and 18 on `TCWCLAIM` and `TCWTEST`,
idempotent re-import, unlink then link, no token in any file.

| # | Verdict |
| - | ------- |
| 1, 2, 10, 11, 12, 14, 17, 19 | Met |
| 3, 4, 5, 7, 8, 9, 13 | Met; automated at claim level, checked end to end by hand by the verifier |
| 6 | Met; orders (a), (b), (c) at claim level, (a) and (c) at command level |
| 15 | Met, except the exit code for a missing `--reason` (2, accepted above) |
| 16 | Met on the paths tested (about nine) and by reading the code: the fake replaces the only function that reads the token, so the older client tests carry the real handling |
| 18 | Met live; not automatable |

## What changed at verification

- **`6afd795e`** — `JiraClient._request` raises `TrackerUnavailable` for
  `ConnectionError` and `http.client.HTTPException`. Before, a connection dropped
  after a request was sent escaped as a traceback; for a claim whose transition may
  have landed, the command died instead of reading the ticket back (row 3f). The gap
  was in C1's transport and reached every tracker command; it is fixed where they
  all route through. Changelog entry added.
- **`46b8b06a`** — `skills/tcw-work/references/commands.md` said the binding is "not
  editable in the web app". The client hides the edit button but the server still
  accepts a write, so it now says exactly that.

## Capability ledger reconciled

`work/manage-external-tracker-intake` (`cap-bd57b7`) moved `Missing` → `Supported`
in `a85aa73c`, with a description of what shipped and its two accepted limits.
`work/inspect-external-tracker-work` had one sentence corrected, since it called
claiming "not yet built". `synchronize-external-tracker-work` and
`require-tracker-backed-work` stay `Missing`; C3 and C4 own them.

## Deferred, deliberately

- **Not verified, for the epic's checkpoint 2:** two developers on two machines
  against one Jira project (no second account), and a ticket filed by someone
  without a checkout (nobody available). Both the user's answer, 2026-09-14.
- **Also for checkpoint 2:** criterion 6 is narrowed to two accounts on a workflow
  that excludes; two runs by one account may both create an item; a second claimant
  on a workflow that does not exclude is not stopped. The last two are user
  decisions.
- **`docs/work/inbox/2026-09-14-serve-accepts-writes-to-generated-sidecars.md`** —
  the server-side refusal for generated sidecars, filed rather than fixed, as the
  epic asked.
- **Command-level test for race order (b)** — the verifier notes threads could build
  one; the logic is proved at claim level. Not filed.
- **Live test tickets** `TCWCLAIM-7`, `TCWCLAIM-8`, `TCWTEST-3` are left
  `In Progress` in the fixture projects, each described as safe to close.
- **No version cut**, by the user's choice. Entries wait in
  `docs/{changelogs,release-notes}/upcoming.md`, to batch with the sibling
  `2026-09-14-inherit-work-tracker-from-parent-nodes-key-by-key`, which edits the
  same documentation sections; whichever merges second rebases.

## Definition of Done

- **tests pass** — see Evidence.
- **docs synced** — README, `docs/guide/work.md`, the `tcw-work` skill reference,
  release notes and changelog (`4319d247`, `46b8b06a`); `skills/tcw-work/SKILL.md`
  re-read and unchanged, as it routes to the reference for every command.
- **capabilities reconciled** — see above.
- **reviewed** — spec reviewed adversarially before planning (`4701bc7c`); the
  implementation assessed by the `tcw-verifier` agent and decided by the user.
- **version offered** — offered; the user kept the current version.
- **originating GitHub issue** — not applicable; the item came from the epic, not an
  issue.

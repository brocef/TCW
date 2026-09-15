# Refined outcome — Synchronize the work lifecycle outward to the tracker

## Decision

**Accepted**, on 2026-09-14, by the autonomous session driving the tracker bridge
epic, which the user authorised to take the verify decision in their place. No user
was asked.

## Evidence

- **Full suite, as CI runs it.** Bare `pytest` from `/Users/brian/Projects/TCW` on
  merged `main` (`cbf68f6d`), editable install restored to the primary checkout:
  **3231 passed** in 690 s.
- **After verification**, two tests were added on `main` for gaps the verifier had
  covered with a one-off script (`b6ec1bf8`): the whole lifecycle through the
  commands, and `start` / `sync` on a binding from another site — 5 passed.
- **Checks on `main`.** `tcw validate` → `validate OK`; `tcw capabilities check` →
  `capabilities OK`; `pnpm check:build` rebuilt the client with no difference under
  `tcw/serve/dist`.
- **Verifier.** The `tcw-verifier` agent found all 25 acceptance criteria met: 150
  targeted tests and 8 web tests passed, and for criteria 5, 7, 9, 11, 12, 15, 17 and
  21 it drove the real commands against the fake tracker in throwaway folders. It
  noted criterion 9 is tested on an `EVERYWHERE` workflow rather than `GLOBAL`, which
  offers no transition to `In Review` and so cannot express the case; and that
  criterion 22 proves TCW does not print the credential variable, not that a real
  Jira error body is scrubbed (recorded in `outcome.md`).
- **Hands-on**, recorded in `outcome.md`: a node pointed at `https://127.0.0.1:9`
  showed the pending message, board state, `show` line and `sync --all` exit 1.
  No live Jira was contacted at any point in this item.
- **Mutation checks** in `outcome.md`, including the one that did not go red and
  what pins that behaviour instead.

## Review

Two rounds (`outcome.md` § Review): the adversarial code reviewer's first round
found six real holes in the spec's rules, all fixed or narrowed; a bounded Codex
second round found four more in those fixes, all fixed. Round 2 ended NOT DONE with
nothing left that was not addressed. The two remainders that need their own change
are in `docs/work/inbox/2026-09-14-follow-ups-the-lifecycle-sync-review-left.md`.
The combined review of all three children at the end of the epic covers these files
again.

## Capabilities

`work/synchronize-external-tracker-work` reads `Supported`;
`work/manage-external-tracker-intake`, `work/start-a-work-item`,
`work/read-a-work-item` and `work/view-the-board` describe the new behaviour. The
item's `capabilities.yaml` lists all five.

## Closeout choices

- **Route:** merged into local `main` as `cbf68f6d`, then `tcw work complete
  --already-integrated`. Nothing pushed.
- **Documentation:** README, release notes, changelog, `skills/tcw-work` command
  reference, `skills/tcw-configure` tracker reference — all fired and written.
- **Version:** none cut; entries are in `docs/*/upcoming.md` for the coordinating
  session.
- **Follow-ups:** the inbox note above; the progress-links child
  `2026-09-14-publish-concise-progress-links-and-comments-to-a-bound-tracker-ticket`.
  The site inbox note is resolved and cleared (`82c91a98`).
- **GitHub issue:** none.
- **Post-mortem:** not run. The review found real defects in the spec's rules after
  a spec review had already run; worth offering to the user, who can decide.

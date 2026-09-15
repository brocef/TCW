# Refined outcome — Surface an item's tracker binding in the board, the projection and the web app

## Decision

**Accepted**, on 2026-09-14, by the autonomous session driving the tracker bridge
epic, which the user authorised to take the verify decision in their place. No user
was asked. The decision rests on the evidence below; nothing in it is testimony
alone.

## Evidence

- **Full suite, as CI runs it.** Bare `pytest` from `/Users/brian/Projects/TCW` on
  merged `main` (`7969bbdb`, the item's merge), with the editable install restored to
  the primary checkout: **3148 passed** in 647 s.
- **Checks on merged `main`.** `tcw validate` → `validate OK`;
  `tcw capabilities check` → `capabilities OK`; `pnpm check:build` rebuilt the web
  bundle and found no difference under `tcw/serve/dist`.
- **Verifier.** The `tcw-verifier` agent checked all twelve acceptance criteria
  against the code and tests: 388 tracker, projection and absent-tracker tests passed
  and 7 web detail tests passed; 12 of 12 met. It checked criterion 10 by building the
  client into a scratch folder and comparing it byte for byte with the committed one,
  since it would not run a build inside the checkout; `pnpm check:build` was then run
  here (above). It checked criterion 3's unlink case through `unlink_document`, the
  function `tracker unlink` writes with.
- **Hands-on.** In a scratch node, three items (bound, unbound, malformed binding)
  read with the installed `tcw`: `tcw work list` printed `| ticket: EX-1` and
  `| ticket: unreadable` on the right rows and nothing on the unbound one; `show`
  printed `tracker: EX-1 (jira-cloud, part default) https://example.invalid/browse/EX-1`
  and `tracker: tracker.yaml cannot be read (missing or empty: ticket.key, provider,
  project, part)`; `show --json` gave the bound value and `null`. `tcw serve` on that
  node returned the same `tracker` value from `/api/work/<slug>`, and the served
  client bundle was the rebuilt one.
- **Not done: a browser check.** No browser connected to this session. The web
  change is covered by the `vitest` tests and the bundle comparison only.
- **Mutation checks** are listed in `outcome.md`; each new guard was broken and its
  test went red for the named reason.

## Review

Two rounds, recorded in full in `outcome.md` § Review: eight findings accepted, one
narrowed to an inbox follow-up, two rejected with reasons, one "no defect". The
second round was a Codex review because the first reviewer did not answer twice.
The verifier also caught the changelog calling `read_binding` "unchanged in
behaviour" after round 2 changed it; corrected in `a1f586e7`.

## Capabilities

Reconciled before closeout: `work/read-a-work-item`, `work/view-the-board` and
`work/manage-external-tracker-intake` read `Supported` with text describing the new
output; the item's `capabilities.yaml` lists all three as changed.

## Closeout choices

- **Route:** merged into local `main` as `7969bbdb` before verification, then
  `tcw work complete --already-integrated`. Nothing pushed.
- **Documentation:** README, release notes, changelog, `skills/tcw-work` command
  reference and search procedure — all written; the configuration entry did not fire.
- **Version:** none cut. Entries are in `docs/changelogs/upcoming.md` and
  `docs/release-notes/upcoming.md` for the coordinating session to fold into v2.2.0.
- **Follow-ups:** `docs/work/inbox/2026-09-14-an-unreadable-capabilities-yaml-breaks-the-whole-board.md`.
- **GitHub issue:** none; the item did not come from one.
- **Post-mortem:** not offered; nothing unforeseen reached verification.

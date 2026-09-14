# Refined outcome: inherit work.tracker from parent nodes, key by key

## Decision

**Accepted** by the user on 2026-09-14: "The work is complete if it passed reviews."
It did. The user also asked for the branch to be rebased onto the latest `main`,
a patch release to be cut, and the result pushed.

The first acceptance request was **declined**. The verifier recommended accepting
with five open points, and the user asked for all of them to be dealt with first.
`outcome.md` "Second round, after the first verification" records how each was
handled.

## Evidence

- **Acceptance criteria C1–C26.** The `tcw-verifier` agent checked each one against
  a test or command it ran. C1–C18 and C20–C26 were met. C19 (the full suite) it
  left to the runs below. The second round added tests for the gaps it named (C18
  now compares the whole merged mapping) and fixed the two doc statements it found
  narrower than the code.
- **Full suite on the rebased branch (`91be00ea`):** 3061 passed under
  `python -m pytest` and 3061 under bare `pytest`, which is what CI runs. Earlier
  rounds: 2867 and 2874 on the first implementation, 3009 on the combined tree
  with the claim item, and 3012 after the second round.
- **Reviews, all of which ended clean or with every finding handled:**
  - Adversarial spec review, twice: the spec, then the plan with the revised spec.
    The findings changed the design, most importantly making inheritance opt-in and
    adding the credentials rule.
  - Multi review of the code: reviewer agent (DONE), Codex (findings, all handled),
    and the local model (two findings, both rejected with reasons).
  - Combined review with the claim item, on both branches merged: reviewer agent
    and Codex. The local model was switched off for maintenance. Both found the same
    two claim-code problems. Both were fixed here, and a third was filed.
  - Codex review of those fixes: VERDICT CLEAN.
- **Checks:** `tcw capabilities check` prints `capabilities OK`, and `tcw validate`
  prints `validate OK`.

## Capability ledger reconciled

- `work/inherit-tracker-settings-from-parent-nodes` (`cap-69ba01`): added Missing
  at the start of implementation and now **Supported**. It is declared under `new:`
  in this item's `capabilities.yaml`, so `complete` checks it.
- `work/inspect-external-tracker-work`: Supported, unchanged. Its description notes
  that settings can come from parent nodes.
- `work/manage-external-tracker-intake` (the claim item's capability): status
  unchanged. Its description now says "one item per ticket" holds within a node.

## Deferred, deliberately

- `docs/work/inbox/2026-09-14-config-parsers-crash-on-a-non-string-key.md`: six
  other config parsers raise on a non-string key. The two sites this item reaches
  were fixed.
- `docs/work/inbox/2026-09-14-a-tracker-binding-does-not-record-its-site.md`: a
  binding does not record its Jira site, so a `base-url` change can make an
  unrelated ticket look bound. This predates inheritance, and inheritance widens
  it.
- Unsetting an inherited optional key, and whether `strict` inherits, are for the
  sync and strict-mode items.
- **Closing GitHub issue #36.** `CLAUDE.md` holds closing an originating issue
  until the fix is released and pushed, and nothing is posted to an issue without
  its exact text being approved. The release is being cut as part of this closeout.
  The reply is drafted and waits for the user's approval of its wording once the
  version is published.

## Definition of Done

| Item | State |
| --- | --- |
| tests pass | Yes: 3061 under both runners on the rebased branch. CI is checked on `main` before tagging. |
| docs synced | Yes: README, guide, `tcw-work` skill reference, both capability descriptions, changelog and release notes. |
| capabilities reconciled | Yes: see above. |
| reviewed | Yes: see Evidence. |
| version offered | Yes. The user chose a patch release, cut after completion. |
| originating GitHub issue answered and closed | Deferred to after publication, for the reason above. |

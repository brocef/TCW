# Refined outcome

**Accepted.** The rule for a later amendment to an item's request (append under
a dated `## Added` heading, write the request first on an intake-only item,
carry it into the spec and plan or say why not, route it through `rework.md`
in review, and leave a bound ticket alone) reads the same in
`skills/work/references/commands.md` and `docs/guide/work.md`. The
`create-work` procedure points to it. The request prompt keeps `## Added`
sections on a re-run.

## Evidence

- The `tcw:verifier` assessment: criteria 1, 3 and 4 met. Criterion 2 was met
  in the skill and the guide, and partly in `create-work.md`, which did not say
  a ticket is not updated. That clause was added at verify (`ddb70730`). Its
  pointer design was intended by the spec, which says the procedure points to
  the rule rather than restating it.
- The verifier also ran 567 tests across the 12 documentation-surface files:
  all pass. `tcw validate` and `tcw capabilities check` pass.
- Full suite as CI runs it (bare `pytest`) on `main` at `9dbe4384`, which holds
  every commit of this item except the one-line verify fix: 5044 passed,
  3 skipped. After `ddb70730` the procedure tests passed: 40.
- Hands-on: in a scratch project, piped text becomes `intake.md` with no
  request, and the `request` prompt tells a re-run to keep `## Added` sections.
  The router's `request` row points to "Amending a request".

## Not changed, deliberately

- The "Change nothing" row in `create-work.md` for an idea overlapping an
  active or review item. It answers "should this new idea touch that item?",
  not "how do I record a decision on it?", and the two are different questions.

## Deferred

- **Closing GitHub issue #74 waits for publication.** This repository's
  instructions say an issue closed before the fix ships tells the reporter it
  is fixed when they still cannot install it. The order is: complete every
  item in this batch → cut the version → push → answer and close. The reply
  text will be approved before it is posted.
- **The backlog-only wording** changes in the same release with #71
  (`2026-09-29-let-a-started-item-still-pass-its-planning-gates-or-stop-start-from-letting-it-past-them`),
  which makes `request` legal in `active` and updates this rule in its own
  commits and changelog entry.

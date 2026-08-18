# Refined outcome — Make the work lifecycle polymorphic and CLI-driven

**Accepted** by the requester on 2026-08-18. All eight children completed; none
discarded, deferred, or left open.

## How the initiative was verified

Aggregate verification, reconciled from the children and re-run at closeout by
the coordinating session rather than accepted from any child's report:

```
1580 passed
validate OK
capabilities OK
no capability drift
```

- **The eleven lifecycle baselines pass unmodified** across the entire
  initiative. That is the compatibility guarantee C3 established and every later
  child had to keep, and it is the single most load-bearing check here: it proves
  a `tcw-config.yaml` valid before the epic still resolves identically.
- **The headline feature was exercised by hand**, not only by test. On this
  repository — which has no `work.lifecycle` key at all —
  `tcw work stage implement <ref>` prints TCW's own instructions and exits 0.
  Before the epic the same command exited 0 and printed nothing.
- **Every capability delta is applied and the ledger is clean.** C7's sweep found
  one record falsified by a sibling and fixed it, plus two linkage gaps: the
  `configurable-work-lifecycle` Feature had zero inbound references, and
  `work/run-a-lifecycle-stage` shipped with no `Subject`.

## Closeout decisions

**Merge route.** Not settled here. The work sits on `epic/polymorphic-work-lifecycle`
and has not been merged or pushed; that is the requester's call and is recorded
as outstanding rather than assumed.

**Version.** The requester chose a **major** cut at closeout. The reasoning is on
the record: the initiative changed what TCW is, added two commands
(`tcw work stage`, `tcw work scaffold`), and carries one deliberate back-compat
break — a bare `stages.<id>: []` and its explicit spelling `prompt: []` are now
refused by `tcw validate`, with `{blob: ""}` as the documented opt-out. Reading
that break as breaking rather than as a validation tightening is the honest call.

**Follow-up items.** C8 filed three, each carrying the evidence that produced it:
`2026-08-18-reconcile-read-artifact-with-the-canonical-presence-rule`,
`2026-08-18-close-the-readme-lifecycle-heading-…`, and
`2026-08-18-report-the-missing-skill-caveat-from-tcw-work-lifecycle-…`. C8 also
rescoped two existing items against the shipped design and left nine untouched.

**GitHub issue #12** was re-verified as live and unrelated to this epic; the
requester deferred it deliberately — no comment, no close, no work item.

## What was accepted without a test behind it

Stated plainly, because these are the initiative's real residual risks:

1. **The six stage prompts and eight artifact templates are asserted to exist, to
   be bounded, and to name no plugin-only skill — not to be good instructions.**
   No test can assert that. Accepted on a reading of the rendered output.
2. **A faithful paraphrase between a router and its prompt is uncaught.**
   Criterion 18's shared-sentence check catches a copied sentence; nothing
   catches a restatement in different words, and C7 wrote both sides of the seam
   in one sitting. The 40-line router ceiling is the only backstop.
3. **The pre-implementation review of C5's revised spec never completed.** An
   agent was dispatched and re-prompted three times and never returned findings,
   so `--force`, the removal of `read_draft`, and roughly forty file:line
   citations went unreviewed by it. The load-bearing claims were verified by hand
   — `resolve_artifact` having no implicit built-in fallback, the canonical
   presence rule, `STAGE_STATUSES`, and the `produces`/`produces_note` invariant
   across all twelve rows — and the `plan` stage independently disproved
   criterion 13. Recorded as a real gap rather than a completed check.
4. **sdist parity is untested.** The wheel is the artifact under test.

## What this initiative learned about its own process

Worth keeping, because it is the argument behind C7's self-review pass:

**Every planning defect was caught by the stage after the one that wrote it.**
C5's criterion 13 asserted an equality that fails 3 of 7 stage documents —
caught when `plan` ran the assertion. C6's spec cited a line number C5 had moved
— caught the same way. C5's plan proposed a second `Builtins` construction site —
caught by the implementation refusing it. The epic's own C8 forecast named two
discard candidates that were already complete.

None shipped. The cost was a revision round each, which is exactly what a
lifecycle is for — and precisely why C7 added a self-review pass at `spec`,
`plan`, and `implement`, derived from these defects rather than copied from a
generic checklist. A generic four-item checklist would have caught **neither** of
the two spec defects: both were internally consistent, unambiguous, and simply
false about the tree.

## Outstanding

- The branch is unmerged and unpushed.
- The version cut follows this completion.

# Outcome — Declare a component store's home repository so a fresh checkout can provision it

Coordination outcome for the epic. It implemented nothing itself; three children
did the work and all three are `completed`.

## What the initiative delivers

The requester's problem was that a cloud session clones only the project
repository, so a project whose work items live in a separate orchestrator folder
starts blind — no board, no specs, no plans. All three parts of the original ask
shipped:

| Child | Delivers |
| ----- | -------- |
| A — declare and provision the work store | `work.repository` in the config, `tcw provision`, and error surfaces that name the remote instead of misdirecting to `tcw init` |
| B — generalize to taxonomy and capabilities | the same declaration and one shared resolution ladder for all three component trees, plus `<component>.path` for the two that never had a configurable location |
| C — publish writes | a provisioned store refreshes before a transition and pushes after, so an ephemeral session's work outlives it |

## Acceptance criteria (initiative level)

| # | Criterion | Where it holds |
| - | --------- | -------------- |
| 1 | unprovisioned board names remote + command; provisioning then works | A |
| 2 | `tcw validate` distinguishes declared-but-unprovisioned from a wrong path | A |
| 3 | node/drift reporting treats unprovisioned as unprovisioned | A |
| 4 | criteria 1-3 hold for taxonomy and capabilities | B |
| 5 | provisioning twice is idempotent | A |
| 6 | only `tcw provision` and C's publish step reach the network | A, C — pinned by a parametrized property test over 3 rules × 3 transitions |
| 7 | a plain `work.path` node is unaffected; its suite unmodified | A, B, C |
| 8 | a transition commits in the store repository and publishes; a later provisioning sees it | C |
| 9 | a provisioning failure reports and leaves nothing behind | A, B |
| 10 | reproducible from a bare shell | all three |

**Suite: 2163 passing.** The reported failure is fixed and was walked end to end
by hand in the requester's own shape — a code repository with no local store,
declaring one in another repository.

## What coordination actually cost

The epic's plan predicted the children's boundaries accurately and the seam
between them held: B consumed A's declaration vocabulary unchanged, and C
consumed B's ladder unchanged. Two things the plan did not predict:

- **Child A needed five review passes**, four of them finding the same defect
  shape. The plan budgeted for one implementation pass per child.
- **The order mattered more than the plan said.** B's `--component` widening had
  to arrive in the same change as its adapters, because A had deliberately
  narrowed it; and C's publication had to be gated on B's ladder having recorded
  *which rule* resolved a store. Neither was a scheduling dependency — both were
  design ones, discovered at implementation.

## What the initiative taught the repository

One post-mortem, one process change, and three follow-up items.

**The uncrossed grid.** Four times across A and B, an acceptance criterion
written as a general property was verified only against the cells its own text or
fixtures happened to reach — and every time, the uncovered axis was already
written down as a numbered list in the same spec's Design section. The
countermeasure (a `### Coverage` cross-product table in
`docs/lifecycle/templates/spec.md`, with `file:line` citations required on every
`n/a`) was first used by child C, where it caught two contradictions on paper
before any code. Its limit is also now known: it finds contradictions between a
spec's own sections, not with code the spec did not describe. Full analysis in
child B's `post-mortem.md`.

**Assertions aimed at a string another program owns.** Child C's divergence test
passed by matching git's push-rejection hint while TCW's own message was still
unhelpful. This is the same family as the grid problem and is not covered by the
countermeasure; recorded in child C's outcome.

**An independent review found three real defects on the riskiest child** after
2163 tests passed and after my own verification walk. Worth the cost, and worth a
stopping rule — one pass — so that review-gated acceptance still terminates.

## Follow-ups left open

- [Nothing verifies that a `changed:` capability was actually changed](tcw://W/2026-08-31-nothing-verifies-that-a-changed-capability-was-actually-changed)
  — found twice in this initiative; child A declared three and edited none.
- [Nothing enforces a spec's declared capability deltas without a capabilities.yaml](tcw://W/2026-08-21-nothing-enforces-a-spec-s-declared-capability-deltas-without-a-capabilities-yaml)
  — the sibling hole in the same gate; the two want one spec.
- [Upstream the acceptance-criteria coverage table to TCW's own spec stage](tcw://W/2026-08-31-upstream-the-acceptance-criteria-coverage-table-to-tcw-s-own-spec-stage)
  — deliberately not upstreamed until it had survived an item; it now has, with a
  known limit to carry into that decision.

## Deliberately not built

Publishing taxonomy and capabilities writes. Raised during child C's spec, filed,
and then dropped: those trees describe the code and are realized when the code
implementing them merges, so publishing an edit on its own would announce a
capability while the code making it true is unmerged. Work is different — an
item's state is the record of a session and changes independently of the code.
The asymmetry is a design decision, not a gap.

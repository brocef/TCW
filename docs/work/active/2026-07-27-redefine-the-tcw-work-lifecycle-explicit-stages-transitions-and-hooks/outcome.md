# Outcome — aggregate

All six children resolved: five completed, one superseded before it was built.

**943 Python tests, up from 733** when the epic opened. 44 web tests.
`tcw validate` OK.

| Child | Result |
|---|---|
| 1 — `review` status, `submit`/`rework` | completed |
| 2a — transition commits, `trunk-branch`, DoD | completed |
| 2b — lifecycle policy and hooks | completed |
| 3 — `tcw work methodology` | **superseded** |
| 4 — skill and command restructure | completed |
| 5 — post-mortem skill | completed |

## What the lifecycle is now

**Two ladders, and nothing is both.** A stage produces one artifact; a transition
moves status. Seven stages, five transitions, each with a stable id that is
public API and exactly one reference document.

**`review` is a status**, so "implemented, awaiting acceptance" is a state the
board can show rather than a thing you remember. It is deliberately *not*
resolved: an item in review still blocks its dependents and still holds its epic
open, because verification can reject it. **`rework` is the model's only reverse
edge**, and it fails closed while `refined-outcome.md` still asserts the work
passed.

**Every transition commits itself**, scoped to the item that moved — from the
CLI and from `tcw serve` alike, because the commit lives at the single choke
point both pass through.

**A node can bind its own skills and shell commands** to any stage or transition.
`pre` hooks abort before anything is written; `post` hooks never roll back.

**Every documented step names its actor and whether anything enforces it.** The
epic did not convert the planning half to `[gated]` — it made the reliance on
judgment visible instead of implied.

## Two children changed shape mid-flight

**Child 2 split into 2a and 2b** once its spec showed it carried auto-commit,
config, validation, hook execution, and an inspection command. The two halves
share no code. The reviewed spec sections were carried across unchanged, and the
blocker graph was rewired to say they were parallel rather than asserting a
sequence that did not exist.

**Child 3 was superseded before implementation.** `tcw work lifecycle` (2b)
already answered its question, and its only remaining distinguishing feature — a
*shipped default* methodology binding — is listed first among the epic's own
non-goals. It would have shipped the thing its parent forbids. Discarded with the
reasoning recorded rather than built and later regretted.

## Nine spec claims disproved by implementation

Counted because it is the epic's most transferable result. None was findable by
more careful reading; every one required running the code.

- **Child 1 (2):** `phase` is not erased by a later write — `set_field` preserves
  unknown keys. `WORK_ARTIFACTS` was not inert; adding a name crashed
  `tcw work list`.
- **Child 2a (4):** three benign `git commit` failure sentences, not two, all
  localized. Untracked entries must be excluded from the precheck. Pathspecs must
  be filtered individually, because `git commit` fails if *any* matches nothing —
  this broke 67 tests the instant auto-commit switched on. A store outside a repo
  never worked, so the criterion demanding it was wrong.
- **Child 2b (1):** a child-1 omission — `SUBCOMMANDS` never gained `submit` or
  `rework` — caught by a test written for something else.
- **Child 4 (2):** the plugin manifests glob directories, so the predicted
  manifest edit was unnecessary. `Produce` could not mean "the one artifact":
  `verify` writes one of two, `inbox` writes none.

## Three guards that did not exist before

- **`tests/test_status_parity.py`** — the Python↔TypeScript status mirror had
  no guard, and this epic added a status. Proven to fail in both directions.
- **`tests/test_lifecycle_policy.py`** — every rejected config shape, checked for
  its *message*, not just a count.
- **`tests/test_skill_lifecycle_parity.py`** — 71 checks that the prose agrees
  with `LIFECYCLE_STEPS`. Proven to fail on real `Produce` and `Inputs` drift.
  This is the one that addresses the epic's opening complaint: two documents that
  had silently stopped agreeing, with nothing to notice.

## Three fields deleted

`phase` (dead since the first work commit), `dod` (a fixed constant stored 60
times), and `pr` — **which this epic itself added** in child 1, on a prediction
that four later children each failed to fulfil.

The pattern is now settled and stated three times: a field stops being read,
existing items keep it inertly, and no migration pass is added. `pr` is the most
instructive of the three, because it shows the rule applies to fresh mistakes and
not only inherited ones.

## Deferred, and recorded so it is not lost

- The capability-first lifecycle: authoring a capability's expected behavior
  *before* `spec.md`, and a capability-vs-tests attestation at completion.
- The `tcw-lifecycle-audit` skill.
- Repo-local `docs/work/lifecycle/<stage>.md` overrides, three-tier
  `bare-wins-local` resolution, and `reset` — these now slot in ahead of the
  configured binding in `tcw work lifecycle` rather than needing a command.
- Concurrency-safe transitions, which
  [already has an item](tcw://W/2026-06-22-concurrency-safe-work-claims-for-multi-agent-repos-configurable-work-path-atomic-owner-stamp).
  Auto-commit widened that window and did not close it.
- Surfacing a refused auto-commit in `tcw serve`'s mutation response rather than
  only its terminal.

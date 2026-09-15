# Refined outcome — aggregate

## Verification decision

**Accepted.** Approved under the decision taken partway through: drive the whole
epic to completion, use the resulting lifecycle for a while, and refine it from
experience under a fresh work item rather than polishing each child in isolation.

That decision is worth recording as the epic's own strongest evidence. **Nine
spec claims were disproved by implementation across five children**, and not one
was findable by more careful reading — each required running the code. More
up-front analysis would not have caught them; it would only have delayed
finding them.

## Aggregate evidence

- 943 Python tests, up from 733. 44 web tests. `tcw validate` OK.
- Three guards added where none existed: Python↔TypeScript status parity, policy
  validation messages, and skill-versus-`LIFECYCLE_STEPS` agreement. **All three
  were proven to fail on real drift before being trusted** — a guard nobody has
  watched fail is not yet known to be a guard.
- The lifecycle was dogfooded on itself throughout: every child moved
  `backlog → active → review → completed` through the transitions child 1 added,
  and every one of those moves was committed by the code child 2a shipped.

## Children

Five completed, one superseded. Child 2 split into 2a and 2b once its spec
revealed how much it carried; child 3 was discarded before implementation because
`tcw work lifecycle` had already answered its question and its one remaining
feature contradicted the epic's own non-goals.

## Capability and taxonomy reconciliation

- **New capabilities:** submit a work item for review; send a reviewed item back
  for rework; configure the work lifecycle; inspect the lifecycle contract; run a
  post-mortem. All `Supported`.
- **Changed:** `work/start-a-work-item`, `work/complete-a-work-item`,
  `work/discard-a-work-item`, `work/view-the-board`, `plugin/work-lifecycle`.
- **New taxonomy:** `work-item/lifecycle-stage`, `configurable-work-lifecycle`.
- A proposed `lifecycle-transition` term was **not** added: `work-item/transition`
  already means exactly that, and adding a synonym to match a planning document
  would be the taxonomy drifting to fit prose.

## Version

Cut once, here, as a **minor** release. Accumulating all six children into one
`upcoming.md` means the release note describes a coherent lifecycle rather than
five partial ones each documenting a half-built state machine.

The prominent entry is `auto-commit-transitions` defaulting to `true` — it
changes what every `tcw work` command does to a user's repository, including from
the web app.

## What to watch when using it

Three predictions this epic makes that only use will confirm:

1. **The 60-line router.** Its budget is defended by a test, but whether the
   extracted content is *findable* is not testable. If agents start missing rules
   that moved out of `SKILL.md`, the destination table was wrong.
2. **Enforcement markers.** The claim is that making judgment visible changes
   behavior. It may just be honest labelling on a document nobody re-reads.
3. **Skill bindings.** Nothing enforces them on any harness, and Codex cannot
   even confirm a bound skill exists. If they turn out to be ignored in practice,
   the hook layer's value is the `command:` half only.

## Deferred

Carried forward in `outcome.md` and not lost: the capability-first lifecycle, the
`tcw-lifecycle-audit` skill, repo-local stage overrides, concurrency-safe
transitions (which has its own item), and surfacing a refused auto-commit in
`tcw serve`'s response rather than only its terminal.

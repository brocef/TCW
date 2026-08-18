# Outcome — Make the work lifecycle polymorphic and CLI-driven

An epic's `outcome.md` is aggregate status reconciled from the children. **All
eight are `completed`**; no child was discarded, deferred, or left open.

## What the initiative delivered

TCW stopped being one opinionated way to run a work item and became the framework
for running one. The measurable difference, on this repository, which configures
no `work.lifecycle` key at all:

**Before:** `tcw work stage spec <ref>` exited 0 and printed nothing. The
methodology existed only in a Claude plugin.

**After:** it prints TCW's own instructions for the stage, and a Codex user — or
anyone driving `tcw` with no plugin at all — gets the same text.

## The children

| ID | Child | Delivered |
| --- | --- | --- |
| C1 | Unify raw intake | `intake.md` as an artifact, an abstract intake surface on `WorkStore`, one canonical presence rule, the board's `i` prefix. Creation paths stopped synthesizing requests. |
| C2 | Work item JSON projection | A versioned, closed DTO with a real JSON Schema, `tcw work show --json`, unified with `serve`'s existing projection. |
| C3 | Hook roles, kinds, conditions | `check`/`prompt`/`artifact` roles; six kinds; the `when:` matcher; the `generate` contract; full back-compat. |
| C4 | The stage verb | `tcw work stage <id> <slug>` — legality → checks → resolve → print. Writes nothing. |
| C5 | Artifact scaffolding | `tcw work scaffold <artifact> <ref> [--force]`, `write_draft` on the store, a built-in template per artifact, `produces` as a tuple. |
| C6 | Built-in stage prompts | Six condensed prompts as package data, the unconfigured-stage floor that makes them reachable, and the `prompt: []` rejection that floor made necessary. |
| C7 | Skill and documentation rewrite | Seven stage documents → 22–36-line routers, `hooks.md` 159 → 92, `SKILL.md` repointed, README section rewritten, plus a self-review pass in three prompts. |
| C8 | Backlog and issue audit | Eleven items and one issue audited; two rescoped, three new items filed, nothing discarded. |

## Capability deltas — all applied

- **New:** `work/capture-raw-intake` (C1), `work/run-a-lifecycle-stage` (C4),
  `work/customize-lifecycle-artifact-templates` (C5).
- **Changed:** `work/open-a-work-item`, `work/manage-the-work-inbox`,
  `work/reconcile-an-epic-rollup`, `web/editing` (C1); `work/read-a-work-item`
  (C2); `work/configure-the-work-lifecycle`, `work/inspect-the-lifecycle-contract`
  (C3); `work/run-a-lifecycle-stage` again (C6);
  `work/configure-the-work-lifecycle` again (C7, correcting a line C6 falsified).

C7 additionally linked all four lifecycle capabilities to the
`configurable-work-lifecycle` Feature, which had **zero** inbound references
before it, and gave `work/run-a-lifecycle-stage` the `Subject` C4 shipped without.

## Verification

```
1580 passed
validate OK
capabilities OK
no capability drift
```

The eleven `tests/fixtures/lifecycle_baseline/*.json` fixtures pass
**unmodified** across the whole initiative — the compatibility guarantee C3
established and every later child had to keep.

## The two amendments

Both recorded in `spec.md` rather than absorbed by the child that found them,
because a child overruling its epic quietly is how an epic stops being the source
of truth.

1. **C6 owns the floor.** The epic scoped C6 to "content and wheel packaging
   only" while criterion 14 demanded built-in instructions *with nothing
   configured*. Those could not both hold: `LifecyclePolicy.stage()` returns `[]`
   for an unconfigured stage, so filling the registry changed nothing. C6 also
   shipped the `resolve_prompts` floor, the `Builtins` argument, and — because
   the floor made `prompt: []` indistinguishable from an absent key — a
   `tcw validate` rejection of an empty prompt list. **The initiative's one
   deliberate back-compat break.**
2. **C7 owns both sides of the seam.** Scoped to consolidation, widened to also
   add a self-review pass to the stage prompts, because C7 is the only child that
   reads a prompt and its router together.

## What planning got wrong, and where it was caught

Recorded because it is the most useful thing this epic learned about its own
process. **Every one was caught by the stage *after* the one that wrote it** —
which is what the lifecycle is for, and also the argument for C7's self-review
pass.

- **C5's criterion 13** asserted exact-set equality between a stage document's
  `Produce` section and its `produces` tuple. The `plan` stage ran the assertion:
  it fails 3 of 7 documents on prose that legitimately names an artifact the
  stage does not produce. Reduced to the subset direction.
- **C6's spec cited `cli.py:801`**; C5's changes had moved it to `:804`.
- **C5's plan** said to construct `Builtins(...)` at the `scaffold` call site.
  The implementation refused — that is the second-loader shape both specs forbid
  — and built the shared `load_builtins()` instead.
- **The epic's own C8 forecast**: it named two items as likely discards; both
  were already `completed`. Its prediction that the three `remote/*` items would
  inherit C1's intake surface and C2's DTO held for one of the three; the other
  two sit on axes this epic changed zero lines of.

## What no test covers

Carried into `refined-outcome.md` as the verification questions, not resolved
here:

- **The prompts and templates are asserted to exist, be bounded, and carry no
  dangling plugin reference — not to be good.**
- **A faithful paraphrase between a router and its prompt is uncaught.** C7 wrote
  both sides; the 40-line ceiling is the only backstop.
- **The pre-implementation review of C5's revised spec never completed** — an
  agent was dispatched three times and never returned findings. The load-bearing
  claims were verified by hand instead. A real gap, not a completed check.

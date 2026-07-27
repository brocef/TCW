# Objective sketch

A sketch of the **end state** — what the plugin looks like once all four children
have landed. Written to be critiqued: if something here reads badly, the spec is
wrong and should be revised before any plan is written.

Not a spec, not a plan. Illustrative content is representative, not final
wording.

---

## 1. File tree

```
skills/tcw-work/
  SKILL.md                          router only — ~60 lines
  references/
    lifecycle-0-inbox.md            id: inbox
    lifecycle-1-request.md          id: request
    lifecycle-2-spec.md             id: spec
    lifecycle-3-plan.md             id: plan
    lifecycle-4-implement.md        id: implement
    lifecycle-5-verify.md           id: verify
    lifecycle-6-postmortem.md       id: postmortem
    transitions.md                  all five, with gates
    hooks.md                        binding skills/commands to ids
    delegation.md                   dispatching stages to subagents
    epic-deltas.md                  differences only
    cross-node-deltas.md            differences only
    decompose.md                    --parent vs --initiative (unchanged)

skills/tcw-post-mortem/
  SKILL.md

agents/
  tcw-verifier.md                   read-only
  tcw-post-mortem.md                read-only

commands/
  tcw-process-inbox.md              stage: inbox
  tcw-plan-work.md                  stages: request → plan
  tcw-drive-work-to-completion.md   current → end
  tcw-verify-work.md                stage: verify
  tcw-post-mortem.md                stage: postmortem
```

**Deleted:** `lifecycle.md`, `task-lifecycle.md`, `epic-lifecycle.md`,
`process-inbox.md`.

---

## 2. `SKILL.md` — the router

````markdown
---
name: tcw-work
description: Drives the `tcw work` change-tracking CLI — the Work axis of TCW.
---

# Driving `tcw work`

Work items move through **statuses** (where the item lives) while agents perform
**stages** (what produces each artifact). These are two different ladders. Never
conflate them: a stage produces an artifact, a transition moves status.

| Stage | Artifact | Status | Delegable |
|---|---|---|---|
| `inbox` | — | — | no |
| `request` | `initial-request.md` | backlog | no |
| `spec` | `spec.md` | backlog | yes |
| `plan` | `plan.md` | backlog | yes |
| `implement` | `outcome.md` | active | yes |
| `verify` | `refined-outcome.md` | review | no |
| `postmortem` | `post-mortem.md` | any | yes |

| Transition | Move | Verb |
|---|---|---|
| `start` | backlog → active | `tcw work start` |
| `submit` | active → review | `tcw work submit` |
| `complete` | review \| active → completed | `tcw work complete` |
| `rework` | review → active | `tcw work rework` |
| `discard` | backlog \| active \| review → discarded | `tcw work complete --resolution …` |

The `inbox` stage is not a transition: `tcw work inbox accept` **creates** the
item directly in `backlog`, and a raw inbox entry has no status to move from.
One exception is not in the table: a fully-reconciled epic may complete straight
from `backlog`, which is why the table is a summary and `transitions.md` is the
authority.

## Reading rule

**Read one stage document, not all of them.** Find the item's stage with
`tcw work show <slug>`, open that stage's reference, and read only the inputs it
declares. Never load the whole lifecycle to perform one stage.

## Routing

| When | Read |
|---|---|
| performing any stage | `references/lifecycle-<n>-<id>.md` |
| moving an item's status | `references/transitions.md` |
| a stage or transition has a configured binding | `references/hooks.md` |
| dispatching a stage to a subagent | `references/delegation.md` |
| the item is `type: epic` | the stage doc **plus** `references/epic-deltas.md` |
| slices span registered projects | `references/cross-node-deltas.md` |
| one item is too large | `references/decompose.md` |

## Notation

Every step is marked with who acts and what enforces it:
`[auto]` the tool does it · `[gated]` the tool refuses if preconditions fail ·
`[prompted]` the tool says so, you may ignore it · `[judgment]` nothing checks.
````

---

## 3. A stage document — `lifecycle-2-spec.md`

````markdown
# Stage: spec

**id** `spec` · **produces** `spec.md` · **runs in** backlog · **delegable** yes

## Purpose

Turn an agreed request into a settled design: what changes, why, what is
explicitly out of scope, and how anyone will know it worked.

## Inputs

Read exactly:

- `initial-request.md`

Also, only if applicable:

- the epic's `spec.md`, when the item has `initiative:`
- `tcw capabilities list` output, when there is a product delta

Do **not** read other work items, and do not read this item's later artifacts —
they do not exist yet.

## Produce

`<item>/spec.md`, containing in order:

- `## Capability changes` — first, and only when there is a product delta
- `## Problem` · `## Goals` · `## Non-goals`
- `## Current state` — with file references
- `## Proposed behavior` · `## Acceptance criteria`
- `## Risks and dependencies`

## Steps

Ordering is a dependency, not a ritual: the binding must be honored first, and
`spec.md` written last. The middle steps interleave freely.

1. `[prompted]` agent — !`tcw work lifecycle --stage spec --directive`
   (Codex: run `tcw work lifecycle --stage spec` and honor any binding listed.)
2. `[judgment]` agent — deep-dive the repository enough that the design is
   settled, not sketched.
3. `[judgment]` agent — for a product delta, run the tcw-capabilities planning
   check **before** settling the technical shape. Nothing enforces this.
4. `[judgment]` user — resolve any open question that changes the shape of the
   work. Ask; do not assume.
5. `[judgment]` agent — write `spec.md`.

## Exit

- `[auto]` tcw — the spec-stage commit, when `auto-commit-transitions` is on.
  Otherwise `[judgment]` agent: commit `spec.md` and only its related work files.
- Next stage: `plan`.

## When this stage cannot finish

- `initial-request.md` is missing or a bare scaffold → return to stage `request`.
  Do not infer a request from the title.
- Discovery contradicts the request → stop and take it to the user. Do not
  silently respec.
- The work turns out too large for one item → read `decompose.md` and split
  before writing a spec that spans several deliverables.
````

---

## 4. A delta document — `epic-deltas.md` (excerpt)

````markdown
# Epic deltas

Read the stage document first. This lists only what differs for `type: epic`.

## spec

**Produce** — replace the section list with: the initiative, affected nodes,
expected child tasks, capability scope, ordering constraints, and acceptance
criteria for the initiative as a whole. An epic spec is an overview; detail
belongs in each child's own spec.

## implement

**Purpose** — coordination, not code. Dispatch child work, monitor blockers,
answer escalations.

**Steps** — add before all others:
`[gated]` tcw — `tcw work reconcile <slug>` before choosing any next action.

**Never** implement child-node code in the epic's own item.

## complete

**Gate** — add: an epic cannot complete while any initiative child is open.
````

Nothing else is restated. Today's `epic-lifecycle.md` is 98 lines that duplicate
the task lifecycle; this is ~20 that don't.

---

## 5. Configuration

```yaml
# tcw-config.yaml
work:
  lifecycle:
    stages:
      spec:      [superpowers:brainstorming]
      plan:      [superpowers:writing-plans]
      implement: [superpowers:subagent-driven-development]
    transitions:
      submit:
        post: ["gh pr create --fill"]
      complete:
        pre: ["pytest -q"]
  auto-commit-transitions: true
  trunk-branch: main
```

`stages` bindings are `[judgment]` — the agent is trusted to invoke them.
`transitions.*.pre` are `[gated]` — a non-zero exit blocks the move.
`transitions.*.post` are `[auto]` — they run after a successful move.

That asymmetry is the point: **anything that must be guaranteed lives on a
transition**, because only transitions run inside the tool.

---

## 6. `tcw work lifecycle` — three output modes

```
$ tcw work lifecycle 2026-07-27-some-item
stage  spec        → spec.md          [backlog]  binding: superpowers:brainstorming
stage  plan        → plan.md          [backlog]  binding: superpowers:writing-plans
trans  start         backlog → active            gates: blockers, epic-active
trans  submit        active → review             post: gh pr create --fill
...

$ tcw work lifecycle --stage spec --directive
For this stage, invoke the superpowers:brainstorming skill.

$ tcw work lifecycle --stage plan --directive     # unbound
                                                   # (empty, exit 0)

$ tcw work lifecycle --stage nope --directive
tcw work lifecycle: unknown stage id: nope        # stderr, exit 2
```

---

## 7. End-to-end trace

An item from inbox to done, showing what each actor does and what stays out of
the main context.

| # | Actor | Action | Level | Context |
|---|---|---|---|---|
| 1 | agent | `tcw work inbox accept req-42 --title "…"` | `[gated]` | main |
| 2 | agent+user | stage `request` → `initial-request.md` | `[judgment]` | main |
| 3 | tcw | commit the request stage | `[auto]` | — |
| 4 | **subagent** | stage `spec` → `spec.md` | `[judgment]` | **isolated** |
| 5 | agent | verify `spec.md` exists and has its sections | `[judgment]` | main |
| 6 | tcw | commit the spec stage | `[auto]` | — |
| 7 | **subagent** | stage `plan` → `plan.md` | `[judgment]` | **isolated** |
| 8 | agent | `tcw work start <slug>` | `[gated]` | main |
| 9 | tcw | move backlog→active, commit on trunk | `[auto]` | — |
| 10 | **subagent** | stage `implement` → code + `outcome.md` | `[judgment]` | **isolated** |
| 11 | agent | `tcw work submit <slug>` | `[auto]` | main |
| 12 | tcw | move active→review, commit; run `gh pr create` | `[auto]` | — |
| 13 | **`tcw-verifier`** | assess the diff, report findings | `[judgment]` | **isolated** |
| 14 | user | approve, or send back | `[judgment]` | main |
| 15 | agent | stage `verify` → `refined-outcome.md` | `[judgment]` | main |
| 16 | agent | `tcw work complete <slug> --resolution done --confirm` | `[gated]` | main |
| 17 | tcw | `pytest -q` pre-hook; capability reconciliation gate; merge-back; move; commit | `[auto]`+`[gated]` | — |

The main session never holds the diff — only `outcome.md` and the verifier's
findings. Four of seven stages run outside it.

**Failure paths:**

| Where | What happens |
|---|---|
| 4, 7, 10 — delegated stage produces no artifact, or one missing required sections | `[judgment]` coordinating session re-dispatches with the gap named, or escalates to the user. No transition was attempted, so nothing refuses. |
| 10 — implementation cannot complete | The item stays `active`. Record what blocked it in `outcome.md`, then either `tcw work edit --blocked-by …` or discard with a non-`done` resolution. |
| 14 — user rejects | `tcw work rework <slug>` → back to `active`, return to step 10. |
| 17 — `pre` hook exits non-zero | The move is refused; the item stays in `review`. |
| 17 — merge conflict | Fails closed; branch and worktree left intact; item stays put. Resolve and re-run rather than `--force`. |

**Assumption this trace makes:** every subagent running a delegable stage can
execute the `tcw` CLI. A stage agent restricted to Read/Write alone cannot honor
its own `Steps`. Agent definitions for delegable stages must include Bash.

---

## 8. What a reader gains

| | Today | Sketched |
|---|---|---|
| Docs read to perform one stage | `lifecycle.md` + `task-lifecycle.md`, ~140 lines | router + one stage doc, ~40 |
| Where "commit this stage" is stated | ~14 places | 1 (`Exit`, per stage) |
| Epic guidance | 98 lines, ~85% duplicated | ~20 lines of deltas |
| Knowing if a step is enforced | not stated anywhere | a marker on every step |
| Verification state | none — invisible in `active` | `review` status |
| Failed verification | no modeled transition | `rework` |
| Stage work in main context | all of it | `spec`/`plan`/`implement`/`postmortem` isolated |

---

## 9. Open for critique

**A terminology collision worth settling before anything is written.** The word
"gate" currently means two things: the enforcement marker `[gated]` (the tool
refuses), and prose usages like "the capabilities planning gate" that are pure
`[judgment]`. Two independent reviewers tripped on exactly this. The sketch now
says "planning *check*", but the spec still says "gate" in several places. Either
reserve "gate" for `[gated]` everywhere, or the marker vocabulary undercuts
itself on contact.

**Collapse `[prompted]` into `[judgment]`?** Both reviewers raised this
unprompted. Operationally they are identical — the agent may skip either. The
only difference is whether the tool emitted text first, which is a property of
the tool, not of the step. Three levels (`[auto]` / `[gated]` / `[judgment]`)
may carry all the meaning with less labeling burden.

**A sixth stage-doc section appeared.** The sample now has
"When this stage cannot finish", because both reviewers flagged that the shape
had no error handling. That is a real gap, but it breaks the agreed five-part
shape — worth confirming rather than absorbing silently.

Still open:

- Should `transitions.md` split once it carries five gate sets, or does one file
  stay right?
- The trace assumes the coordinating session re-reads each delegated artifact.
  That is a real token cost the table does not show, and it partly offsets the
  isolation win.
- `postmortem` has no command range and no natural trigger in the trace — it only
  appears when something went wrong. Is a stage the right shape for it?
- Do `hooks.md` and `delegation.md` earn separate files, or fold into
  `transitions.md` and `SKILL.md` respectively? One reviewer called the file
  count over-engineering.

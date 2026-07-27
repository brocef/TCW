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
| `verify` | `refined-outcome.md` **or** `rework.md` | review | no |
| `postmortem` | `post-mortem.md` | review, or after completed | yes |

| Transition | Move | Verb |
|---|---|---|
| `start` | backlog → active | `tcw work start` |
| `submit` | active → review | `tcw work submit` |
| `complete` | review \| active → completed | `tcw work complete` |
| `rework` | review → active | `tcw work rework` (refuses while `refined-outcome.md` exists) |
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

## Delegation

Where subagents exist, dispatch stages marked delegable; give the subagent the
stage document and its declared `Inputs`, nothing more. **Delegable means
permitted, not required** — with no subagents available, run the same stage here,
following the same document. **Never delegate a transition**: those carry the
gates and belong to the session holding the primary checkout. Never delegate
`request` or `verify` — a subagent cannot ask the user. Check the artifact named
in `Produce` before transitioning; a subagent's context is gone once it returns.

## Routing

| When | Read |
|---|---|
| performing any stage | `references/lifecycle-<n>-<id>.md` |
| moving an item's status | `references/transitions.md` |
| a stage or transition has a configured binding | `references/hooks.md` |
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

**Lifecycle context — read exactly these, and no other work item:**

- `initial-request.md`
- the epic's `spec.md`, when the item has `initiative:`

**Repository discovery — unrestricted.** This stage exists to understand the
current system, so read whatever code, tests, and docs the design requires. The
restriction above bounds *lifecycle* reading, not investigation.

**Other axes**, when there is a product delta: route to the `tcw-capabilities`
skill and follow it. Reading `tcw capabilities list` output is not a substitute
for that skill under any harness.

Do not read this item's later artifacts — they do not exist yet.

## Produce

`<item>/spec.md`, containing in order:

- `## Capability changes` — first, and only when there is a product delta
- `## Problem` · `## Goals` · `## Non-goals`
- `## Current state` — with file references
- `## Proposed behavior` · `## Acceptance criteria`
- `## Risks and dependencies`
- `## Notes` — optional, last. Anything worth keeping that has no home above: how
  this stage actually ended, a dead end not worth re-exploring, something `plan`
  should know before it starts. Omit it when there is nothing to say.

## Steps

Ordering is a dependency, not a ritual: the binding must be honored first, and
`spec.md` written last. The middle steps interleave freely.

1. `[prompted]` agent — !`tcw work lifecycle --stage spec --directive`
   (Codex: run `tcw work lifecycle --stage spec` and honor any binding listed.)
2. `[judgment]` agent — deep-dive the repository enough that the design is
   settled, not sketched.
3. `[judgment]` agent — for a product delta, run the tcw-capabilities planning
   **check** before settling the technical shape. Nothing enforces this — it is a
   check, not a gate; "gate" is reserved for `[gated]`.
4. `[judgment]` user — resolve any open question that changes the shape of the
   work. Ask; do not assume.
5. `[judgment]` agent — write `spec.md`.

## Exit

**Ends well:**

- `[judgment]` agent — commit `spec.md` and only its related work files. Stage
  commits are agent-owned: nothing runs at the end of a stage, so nothing can
  enforce this. `auto-commit-transitions` covers *transitions* only.
- Next stage: `plan`.

**Ends badly:**

- `initial-request.md` is missing or a bare scaffold → return to stage `request`.
  Do not infer a request from the title.
- Discovery contradicts the request → stop and take it to the user. Do not
  silently respec.
- The work turns out too large for one item → read `decompose.md` and split
  before writing a spec that spans several deliverables.

Record which of these happened in the artifact's `## Notes`.
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
| 15 | agent | stage `verify` → `refined-outcome.md` (accepted) or `rework.md` (rejected) | `[judgment]` | main |
| 16 | agent | `tcw work complete <slug> --resolution done --confirm` | `[gated]` | main |
| 17 | tcw | `pytest -q` pre-hook; capability reconciliation gate; merge-back; move; commit | `[auto]`+`[gated]` | — |

The main session never holds the diff — only `outcome.md` and the verifier's
findings. Four of seven stages run outside it.

**Failure paths:**

| Where | What happens |
|---|---|
| 4, 7, 10 — delegated stage produces no artifact, or one missing required sections | `[judgment]` coordinating session re-dispatches with the gap named, or escalates to the user. No transition was attempted, so nothing refuses. |
| 10 — implementation cannot complete | The item stays `active`. Record what blocked it in `outcome.md`, then either `tcw work edit --blocked-by …` or discard with a non-`done` resolution. |
| 14 — user rejects | Write `rework.md` naming what is still required, **delete `refined-outcome.md`**, then `tcw work rework <slug>` → back to `active`, return to step 10. The transition refuses while `refined-outcome.md` is still there, so the deletion cannot be forgotten silently. `rework.md` is a declared input to the re-run of `implement`. |
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

## 9. Resolved

All questions raised by the first review round have been decided:

| Question | Decision |
|---|---|
| "gate" collides with `[gated]` | Reserve "gate" for `[gated]`. The capabilities planning *gate* becomes a **check**. "DoD gate" splits: checklist is `[prompted]`, reconciliation is `[gated]`. |
| Collapse `[prompted]` into `[judgment]`? | **Keep both.** `[prompted]` is an obligation on the *tool*, and therefore testable. The redundancy is only from the agent's side. |
| A sixth stage-doc section | **No.** `Exit` covers ending well and ending badly. Five sections stand, plus optional `Notes` on artifacts. |
| Split `transitions.md`? | **No.** Not for five short gate sets. |
| Separate `hooks.md`? | **Yes** — genuinely rare, most projects configure nothing. |
| Separate `delegation.md`? | **No** — folded into `SKILL.md`, which has a hard 80-line budget. If it breaches, it goes back out; the budget wins. |
| Is `postmortem` really a stage? | **Yes**, marked out-of-band: it produces an artifact but holds no position in the ordering. |
| Delegation token cost | Stated honestly — the coordinator re-reads each artifact. A large win, not a total one. |

## 10. Still open for critique

- **The 80-line `SKILL.md` budget is asserted, not demonstrated.** The sketch in
  section 2 plus the delegation paragraph is close to it already, and the routing
  table grows with every reference file. If the budget cannot be met, either
  delegation moves back out or the two-ladder tables get trimmed — decide which
  before writing, not after.
- **`Notes` has no size discipline.** It is optional and free-form by design, but
  an artifact whose `Notes` outgrows its required sections has become a scratch
  file. Worth a soft convention, or worth leaving alone until it happens.
- **Methodology resolution is settled in principle, unwritten in practice.**
  Amended Option A (repo-local methodology document → configured skill → shipped
  default) is agreed, but this sketch still shows only the contract half. What a
  methodology document must provide — its interface to TCW — is undefined, and
  child 3 cannot write the shipped defaults without it.
- **`postmortem` still has no trigger in the trace.** Marking it out-of-band
  names the shape but not the mechanism: nothing in the flow decides when to
  offer it. Child 4 owns that, and the `verify`-stage hook is the only candidate
  so far.

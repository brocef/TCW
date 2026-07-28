# Specification

Child 4 of [the lifecycle epic](tcw://W/2026-07-27-redefine-the-tcw-work-lifecycle-explicit-stages-transitions-and-hooks).
The last code-bearing child shipped; this one makes the documentation describe
what exists.

**Documentation only. No code, no CLI change, no test-covered behavior** — except
the structural checks this child adds to guard its own invariants.

## Capability changes

- **Changed:** `plugin/work-lifecycle` — the skill it names is restructured.

No new capabilities. Reorganizing documentation does not add something a user can
do.

## Current state, measured

| File | Lines | Fate |
|---|---|---|
| `skills/tcw-work/SKILL.md` | 170 | rewritten as a router, ≤60 |
| `references/task-lifecycle.md` | 139 | **deleted** |
| `references/epic-lifecycle.md` | 98 | **deleted** |
| `references/cross-node-epic.md` | 44 | → `cross-node-deltas.md` |
| `references/lifecycle.md` | 38 | **deleted** |
| `references/decompose.md` | 35 | unchanged |
| `references/process-inbox.md` | 16 | folded into `stage-inbox.md` |

`task-lifecycle.md` and `epic-lifecycle.md` are ~85% identical and have already
drifted — the measured fact that opened the epic. Deleting both is the point.

**Plugin manifests need no edit.** Both declare directories
(`"skills": "./skills/"`, `"commands": "./commands/"`), so new files are picked
up automatically. The epic plan listed "plugin manifests list every new command
and skill" as a deliverable; that was wrong about how the manifests work. The
child instead asserts the *packaging* still resolves.

## Design

### One document per id, named for the id

`references/stage-<id>.md` for each of the seven stages, plus `transitions.md`
for all five transitions in one file. **No ordinals in filenames** —
`stage-spec.md`, never `lifecycle-2-spec.md`. Ordinals recreate exactly the
renumbering churn that stable ids exist to prevent, and routing is by literal
path. Order lives in the router's table, the one place it is cheap to change.

Every stage document uses a fixed five-section shape:

| Section | Contains |
|---|---|
| **Purpose** | What this stage is for, in one or two sentences. |
| **Inputs** | The bounded lifecycle artifacts it may read, plus a note that repository discovery is unrestricted. Doubles as a subagent's context brief. |
| **Produce** | Every artifact the stage may write, with path and required sections. The return contract. |
| **Steps** | The work, each step carrying an actor and an enforcement marker. |
| **Exit** | How the stage ends well **and how it ends badly**. |

`Gates` is deliberately not a section: a gate is simply a step marked `[gated]`.
That is a documentation change only — it does not move where a gate runs or who
evaluates it.

**Two stages do not produce exactly one artifact, and `Produce` must say so
rather than being bent to fit.** `verify` writes `refined-outcome.md` on
acceptance *or* `rework.md` on rejection — which one is written *is* the verdict,
so both are named and the condition for each is stated. `inbox` writes no
lifecycle artifact at all; it creates the item. Its `Produce` section says
exactly that, and the parity test treats "no artifact" as a value, not as a
missing section. Any rule phrased as "the one artifact" would have forced a lie
into two of seven documents.

### `LIFECYCLE_STEPS` is the source, and agreement is checked

Child 2b put every id's objective, inputs, produced artifact, status move, and
gates into `LIFECYCLE_STEPS` in `store/base.py`. **The stage documents must agree
with that table, and this child adds the test that proves it** rather than
trusting two prose sources to match.

That test is the single most valuable thing in this child. Everything else here
is prose; this is the guard that stops the prose drifting from the tool the way
the six documents being deleted already did.

Concretely, `tests/test_skill_lifecycle_parity.py` asserts:

- Every id in `LIFECYCLE_STEPS` resolves to exactly one document — a
  `stage-<id>.md` for stages, a named section of `transitions.md` for
  transitions.
- No document exists for an id that is not in the table.
- **Each stage document's `Produce` names every artifact the table's `produces`
  field mentions**, and its `Inputs` names every artifact in the table's
  `inputs`. Both are checked by extracting `*.md` filenames from the table
  field and asserting each appears in the corresponding section.
- No filename or id contains an ordinal.
- The router lists every stage document exactly once.
- No reference to a deleted filename survives anywhere in the repository.
- Every stage document carries the five sections in order.
- Every marker used is one of the four; no other bracketed lowercase word
  appears where a marker belongs.

**Checking `Inputs` as well as `Produce` is the difference between a real guard
and a decorative one.** `Produce` alone was the first draft, and review was right
that `Inputs` is at least as likely to drift — it is the section that grows
quietly as an author remembers one more thing a stage reads.

Two limits, stated so the test is not oversold:

- **`Steps` is not checked against the table.** `LIFECYCLE_STEPS` records gates,
  not procedures, so there is nothing to compare a step list against. Asserting
  that every step *has* a marker is mechanical; asserting the marker is *correct*
  is not, and pretending otherwise would be the dishonesty this child is
  supposed to remove.
- **`transitions.md` needs section-level parsing**, not file existence — a
  heading-splitting helper, and therefore more brittle than the `stage-<id>.md`
  checks. Accepted: five transitions in one file is right for five short gate
  sets, and pre-splitting them into five files to simplify a test would be the
  test dictating the structure.

### Enforcement markers, on every step

Each step in a stage or transition document carries an actor (`tcw`, `agent`,
`user`) and one marker:

| Marker | Meaning |
|---|---|
| `[auto]` | The tool does it. Cannot not happen. |
| `[gated]` | The agent initiates; the tool refuses if preconditions fail. |
| `[prompted]` | The tool **must** emit a reminder; the agent may ignore it. |
| `[judgment]` | Nothing is emitted and nothing enforces it. |

This is the epic's central requirement: reliance on agent judgment must be
*visible* rather than implied. The initiative does not convert the planning half
to `[gated]`; it requires only that every step declare its level.

**"Gate" is reserved for `[gated]`.** Anything the agent is merely expected to do
is a *check* or a *step*. The one existing misuse — the tcw-capabilities
"planning gate", which is `[judgment]` — is renamed to **planning check**
wherever it appears, including in `skills/tcw-capabilities/`.

### Where the router's 170 lines go

The budget is only credible with an answer for every existing section, so it is
written down before the cut rather than discovered during it:

| Currently in `SKILL.md` | Destination |
|---|---|
| The artifact spine and stage order | The router's table — this *is* the router |
| The lifecycle handshake (`start`/`complete` reminders) | `transitions.md` |
| The full `complete` description and its gates | `transitions.md` |
| Tags | `tags.md` (new) |
| Cross-node addressing and project identity | `cross-node-deltas.md` |
| Lifecycle bindings and `tcw work lifecycle` | `hooks.md` |
| Resume-across-sessions | `SKILL.md` — three lines, always relevant |
| The quick-reference command table | `commands.md` (new) |

Two new reference files fall out of that: `tags.md` and `commands.md`. Neither
was in the epic plan's list, and both are better than the alternative of keeping
a 170-line router or deleting content that is currently useful.

### The router, under a hard 60-line budget

`SKILL.md` loads on every use of the skill, so its size is a recurring cost paid
forever, while a reference file is paid only when its gate condition fires. The
rule on breach is **extract, never grow**.

**The epic spec contradicts itself here** — its child-4 section says a hard budget
of 60 lines, its acceptance criteria say 80. Resolved to **60**: the 60 is stated
as a rule with its rationale, the 80 appears once in a list with none. The router
is currently 170 lines, so either number is a real cut; taking the stricter one
costs nothing and matches the stated reasoning.

Harness-specific fallbacks do **not** live in the router. They are per-stage, so
they live in the stage document, which every harness reads anyway on the path to
performing that stage. That removes the tension between the budget and Codex
correctness entirely — neither has to give.

### Methodology: one command, no second concept

Child 3 was superseded, so there is no `tcw work methodology` and no
`methodology.md`. Every stage document carries one harness-neutral step:

> Run `tcw work lifecycle --stage <id>` and honor any binding it reports.
> `[judgment]`

`--directive` is named in `hooks.md` as Claude-only sugar over that command,
never as the path. This is the harness-compatibility rule applied literally: what
must be guaranteed lives in the CLI, which behaves identically under both.

### Commands

Codex has no slash commands, so **every command's workflow must also be reachable
by invoking the skill directly**. Each command file is a thin wrapper naming the
stage range and pointing at the documents.

| Command | Stage range | Status |
|---|---|---|
| `tcw-process-inbox` | `inbox` → `request` | **new** |
| `tcw-plan-work` | `request` → `plan` | exists; retargeted |
| `tcw-drive-work-to-completion` | current → `complete` | exists; retargeted |
| `tcw-verify-work` | `verify` (+ `submit`/`rework`) | **new** |

`tcw-post-mortem` is **child 5's**, not this one's — it ships with the skill it
drives. Listing it here and having child 5 also create it is how two children end
up half-owning one file.

### The `tcw-verifier` agent

Read-only (no `Edit`/`Write`), for the `verify` stage's *assessment* — reading the
diff, running checks, forming an opinion. The **approval** is not delegable,
because a subagent cannot ask the user.

This repository has no `agents/` directory and neither plugin manifest declares
one. Adding the agent therefore means creating that directory and wiring it into
the Claude manifest. **Codex has no custom agents**, so per the
harness-compatibility rule it is an accelerator only: every stage document must
stand alone without it, and `stage-verify.md` must be followable with no subagent
at all.

**If wiring the agent turns out to need more than a directory and a manifest key,
drop it and record why.** It is the least load-bearing item in this child, and
the epic's own rule says a custom agent earns its place only when it needs a
different tool set — which is exactly one line of justification, not a
subsystem.

### Deleting four files means sweeping for links

`lifecycle.md`, `task-lifecycle.md`, `epic-lifecycle.md`, and `process-inbox.md`
are referenced from `SKILL.md`, from the commands, and from each other. A
dangling route is worse than the duplication it replaces, so a repo-wide grep for
each deleted filename is a required step, not a courtesy — and the parity test
asserts no reference to a deleted file survives.

## Out of scope

- The post-mortem skill, its agent, and its command — child 5.
- Any CLI or model change. If a document cannot describe what the tool does, the
  document is wrong; the tool is not changed to match it.
- Rewriting `skills/tcw-capabilities/` beyond the "planning gate" → "planning
  check" rename.
- `decompose.md`, which is already scoped correctly.

## Acceptance criteria

Automatically checkable:

1. Every id in `LIFECYCLE_STEPS` resolves to exactly one document; no document
   exists for an id not in the table.
2. Each stage document's `Produce` names every artifact `LIFECYCLE_STEPS` lists
   under `produces`, and its `Inputs` names every artifact listed under
   `inputs`. `inbox`, which produces none, says so explicitly; `verify`, which
   produces one of two, names both with the condition for each.
3. No filename, id, or heading carries an ordinal.
4. `SKILL.md` is **≤60 lines**.
5. No reference to `lifecycle.md`, `task-lifecycle.md`, `epic-lifecycle.md`, or
   `process-inbox.md` survives anywhere in the repository.
6. Every stage document has all five sections, in order.
7. Every step line in a stage or transition document carries one of the four
   markers.
8. No document uses the word "gate" for anything not marked `[gated]`.
9. `tcw validate` passes; the existing plugin-manifest tests pass.

Manual sign-off, honestly labelled as such because neither is programmatically
verifiable:

10. No rule is stated twice across the skill.
11. Every stage document is followable by a Codex agent with no injection, no
    custom agents, and no slash commands.

## Risks

- **A 170 → 60 line cut loses something real.** The router currently carries
  cross-node addressing, tags, the artifact spine, and the full `complete`
  description. All of it has to land somewhere findable, and "findable" is what
  criterion 10's manual review is actually checking.
- **The parity test is the child's whole value; a weak one is worse than none.**
  If it only checks that files exist, it will pass while the documents say
  something false. Criterion 2 — `Produce` matching the table — is the clause
  that gives it teeth.
- **`tcw-verifier` may not be wireable cheaply.** Named as droppable above so
  that discovering this does not turn into scope creep.
- **Prose criteria invite self-marking.** 10 and 11 are sign-off, not tests, and
  the child must not claim them as verified by the suite.

## Notes

The epic plan predicted a `methodology.md` reference and a manifest edit. Neither
survives contact: child 3 was superseded, and the manifests glob directories.
Both are recorded here rather than quietly dropped, because this child's entire
subject is documentation that stopped matching reality.

**`pr` is now certainly unconsumed.** Child 1 added it, children 2a and 2b were
each predicted to use it and did not, and stage documents have no reason to read
a field. Unless child 5 finds one, it should be deleted at epic close under the
same pattern the epic applied to `phase` and `dod`.

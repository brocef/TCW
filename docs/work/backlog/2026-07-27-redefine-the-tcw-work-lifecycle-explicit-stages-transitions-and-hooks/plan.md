# Coordination plan

This is an epic. It implements nothing itself — each child runs its own
`spec` → `plan` → `implement` → `verify` cycle. This document fixes the child
boundaries, the order, and what must be true at each rollup.

## Dependency order

Strictly sequential. Nothing here parallelizes usefully: each child establishes
vocabulary the next one depends on.

```
1. review status + transitions      CLI — the model
        ↓
2. transition commits + policy      CLI — behavior and config
        ↓
3. methodology resolution           what a stage's "how" resolves from
        ↓
4. skill + command restructure      docs — describes 1, 2, and 3
        ↓
5. post-mortem skill                needs 4's stage docs to read
```

Two hard ordering constraints, both discovered during planning rather than
assumed:

- **4 cannot precede 1–2.** A skill documenting a transition the CLI does not
  have is exactly the drift `AGENTS.md` forbids.
- **4 cannot precede 3.** A stage document that does not know where its
  methodology comes from cannot be authored — it would be all contract and no
  instruction, which is the flaw that prompted this epic.

## Artifact ownership, so it is not split three ways

Naming an artifact and defining its contents are different jobs, and they land in
different children. Stated once here rather than discovered later:

- **Child 1** owns only that `post-mortem` and `rework` **exist** in the bounded
  `WORK_ARTIFACTS` set.
- **Child 4** owns every artifact's **required sections**, expressed as the
  `Produce` section of the stage document that writes it. `rework.md`'s shape is
  defined by `stage-verify.md`; `post-mortem.md`'s by `stage-postmortem.md`.
- **Child 5** owns the post-mortem **methodology** — how to conduct one — not the
  file's structure.

## Child 1 — `review` status and transitions

Owns the state machine. Nothing about config, commits, or hooks.

- `WORK_STATUSES` gains `review`; `RESOLVED_STATUSES` unchanged, so an item in
  `review` still blocks its dependents.
- `LEGAL_TRANSITIONS` gains `(active, review)`, `(review, completed)`,
  `(review, active)`, `(review, discarded)`.
- `WorkStore.submit()` and `.rework()` beside `start()` / `complete()`.
- `tcw work submit <slug>`; `tcw work rework <slug>`, which **fails closed while
  `refined-outcome.md` is present**; `complete` accepts `review` as a source and
  warns on the `active` route.
- `WORK_ARTIFACTS` gains `post-mortem` and `rework` — bounded, no series.
- Add `pr`. **Delete `phase`** — the field, its `state.yaml` key, the `show` line
  (`work/cli.py:97`), and the reconcile column (`work/recursion.py:134`).
- `web/client/src/model/types.ts` + the precedence map in `tree.ts`, and the
  Python↔TypeScript parity test that does not exist today.
- Lazy `review/` creation for nodes that predate the status.

**`phase` removal is a no-op migration, and the child must prove it.** Every
existing `state.yaml` carries `phase: ""` and no code path ever writes anything
else, so nothing is lost. The adapter already tolerates its absence
(`fs.py:1785` reads it with a default). Required: a test that loads a
pre-existing item whose `state.yaml` still contains `phase` and confirms it is
read without error and dropped on the next write.

**Done when:** an item traverses `active → review → active → review → completed`;
`rework` refuses while `refined-outcome.md` exists; `complete` still works from
`active` with a warning; a node with no `review/` folder does not crash; `phase`
appears nowhere; and **the Python↔TypeScript status parity test exists and
fails** when the two sets diverge. That test is a named deliverable, not a
by-product — it is the one guard that does not exist today.

## Child 2 — transition commits, config, and policy

Owns behavior and configuration. No new statuses.

- `auto-commit-transitions` (default **true**) — every transition commits its own
  move through the existing scoped `git_commit(node, msg, *paths)`. No empty
  commits. Stage commits stay `[judgment]`; nothing runs at stage end.
- `trunk-branch` — compare `HEAD`, warn on mismatch, commit where you are.
- Stop persisting `dod:`. Keep the checklist as a closeout prompt; keep the real
  gates (capability reconciliation, merge-back, `--confirm`).
- `LifecyclePolicy` + `WorkStore.lifecycle_policy()`; FS adapter reads node-local
  `work.lifecycle`; bindings declared explicitly as `{skill: …}` or
  `{command: …}`, never inferred from a bare string.
- The full hook execution contract from the spec: node-root cwd, shell
  execution, `TCW_*` environment, 300s default timeout, `pre` aborts in declared
  order, `post` failure never rolls back.
- `tcw validate` rejects unknown ids, non-mapping/non-list shapes, blank or
  duplicate refs, and mappings with neither or both of `skill`/`command` — and
  never reorders or disturbs unrelated config.
- `tcw work lifecycle [work-ref]` in three modes: human, `--json`, `--directive`.
- `tcw work complete --already-integrated`.

**Done when:** a node with no `work.lifecycle` behaves exactly as before apart
from transition commits; every rejected policy shape has a test and an actionable
message; `--directive` emits one complete instruction, or nothing, or exits
non-zero on error with empty stdout; a qualified descendant uses its own node's
policy.

## Child 3 — methodology resolution

The piece the epic cannot be planned around. Owns the contract/methodology split.

- Resolution order, first match wins, modeled on `bare-wins-local`
  (`fs.py:627`, `:1096`): repo-local `docs/work/lifecycle/<stage-id>.md` →
  configured binding → shipped default.
- **The override target is a document in the consumer's repository, never a skill
  file.** Verified: Claude namespaces plugin skills so a project cannot shadow
  one, and the Agent Skills spec defines no layering at all.
- Define what a methodology document must supply to satisfy a stage contract, and
  what it may not override.
- `origin` reporting through `tcw work lifecycle`, matching how
  `tcw capabilities list` already flags provenance.
- Write the shipped default methodologies.

**Explicitly out of scope for this child**, because two reviewers independently
called it the most likely to expand: rewriting the `tcw-work` stage documents
(child 4), any build or composition step that bakes methodology into generated
files (rejected — plugin files are replaced on update and plugin skills cannot be
shadowed), and shipping more than one default methodology per stage.

**Done when:** a stage resolves its methodology from each of the three sources
and `tcw work lifecycle` reports which one won; a project with no override and no
config behaves exactly as it does with the shipped default; and a methodology
document that attempts to override a contract field is **rejected by
`tcw validate` with an error naming the field** — "enforced" means that error
exists and is tested, nothing looser.

## Child 4 — skill and command restructure

Owns documentation. No code.

- One `stage-<id>.md` per stage on the fixed shape **Purpose / Inputs / Produce /
  Steps / Exit**, every step carrying its actor and enforcement marker. `Inputs`
  separates bounded lifecycle context from unrestricted repository discovery.
  `Exit` covers ending well **and** ending badly.
- No ordinals in filenames. Order lives in the router's table.
- `transitions.md`, `hooks.md`, `delegation.md`, `methodology.md`,
  `epic-deltas.md`, `cross-node-deltas.md`; `decompose.md` unchanged.
- **Delete** `lifecycle.md`, `task-lifecycle.md`, `epic-lifecycle.md`,
  `process-inbox.md`.
- `SKILL.md` becomes a router under a hard **60-line** cap; the rule on breach is
  extract, never grow. Harness fallbacks live in stage docs, not the router.
- Commands: `tcw-process-inbox`, `tcw-plan-work` (request → plan),
  `tcw-drive-work-to-completion` (current → end), `tcw-verify-work`,
  `tcw-post-mortem`. Every command workflow must also have a skill-based entry
  path, because Codex has no slash commands.
- The read-only `tcw-verifier` agent — an accelerator only; the stage doc must
  stand alone without it.
- Plugin manifests list every new command and skill.

Deleting four reference files means sweeping every surviving document, command,
and manifest for links to them. A dangling route is worse than the duplication it
replaced.

**Done when** — automatically checkable: every stage and transition id resolves
to exactly one document; no id or filename carries an ordinal; `SKILL.md` is ≤60
lines; no reference to a deleted file survives anywhere in the repo; plugin
manifests list every command and skill.

**Done when** — manual review gate, not a test: no rule is stated twice, and
every stage document is followable by a Codex agent with no injection, no custom
agents, and no slash commands. Neither is programmatically verifiable; both are
sign-off criteria for this child's `verify` stage, and labelling them as tests
would be dishonest.

## Child 5 — post-mortem skill

- `skills/tcw-post-mortem/`, reading the artifact spine backward from
  `refined-outcome.md` (and any `rework.md`) to locate which stage first missed
  the problem. `Notes` across the spine is the primary trail.
- Writes `post-mortem.md`; never changes status; legal in `review` or after
  `completed`.
- The `verify`-stage instruction offering it when verification surfaced serious
  unforeseen issues, invoked only on user assent.
- The read-only `tcw-post-mortem` agent.

**Done when:** a post-mortem can be produced before and after completion, and
producing one after completion changes nothing but that single file.

## Documentation sync

Evaluated against the `## Documentation Sync` table in `AGENTS.md`. Each child
carries its own share; none of it defers to the end.

| Entry | Trigger | Owner |
|---|---|---|
| `README.md` | new status, `submit`/`rework`, `tcw work lifecycle`, new commands | 1, 2, 4 |
| `docs/release-notes/upcoming.md` | new review step, auto-commit default, methodology overrides | 1, 2, 3, 5 |
| `docs/changelogs/upcoming.md` | any code change | all five |
| `skills/tcw-work/SKILL.md` | the component's CLI, model, and lifecycle all change | 4 (1–3 note deltas) |

`auto-commit-transitions` defaulting to `true` is a **behavior change** — plain
`tcw work start` commits nothing today — and needs a prominent release note, not
just a changelog line.

## Rollup checkpoints

`tcw work reconcile <epic-slug>` after each child resolves and before closeout.
The epic cannot complete while any initiative child is open.

Before child 4 writes a single stage document, re-read the spec's contract tables
**and** what children 1–3 actually shipped. Child 4's job is to describe reality,
not to restate this plan's predictions.

## Creating the children

```
E=2026-07-27-redefine-the-tcw-work-lifecycle-explicit-stages-transitions-and-hooks

tcw work new "Add the review status and the submit/rework transitions" \
    --initiative $E --tag work --tag cli --effort high --complexity high --priority 10
tcw work new "Commit every work transition; add lifecycle policy config" \
    --initiative $E --tag work --tag cli --effort high --complexity high --priority 9
tcw work new "Resolve stage methodology from repo, config, or shipped default" \
    --initiative $E --tag work --tag skills --effort high --complexity very-high --priority 8
tcw work new "Restructure the tcw-work skill into per-stage references and commands" \
    --initiative $E --tag skills --tag docs --effort high --complexity medium --priority 7
tcw work new "Add the post-mortem skill and its verify-stage trigger" \
    --initiative $E --tag skills --effort medium --complexity low --priority 6
```

`--initiative`, not `--parent`: these are scheduled and completed independently
over time, and `reconcile` follows the initiative relation. The epic must be
`active` before any child can start.

## Risks

- **ID stability.** Once released, renaming a stage or transition id breaks user
  configuration. Review the id set hard during child 1, before anything ships.
- **Behavior change.** Auto-commit alters what every `tcw work` command does to
  the repo. Scoped commits limit blast radius; the default is still deliberate.
- **Cross-language drift.** The TypeScript status mirror has no parity guard, and
  child 1 adds a status — precisely when that bites.
- **Hook ownership blur.** A bound skill may attempt its own commits or
  transitions. The envelope's ownership rule is the only guard, and it is
  `[judgment]` on every harness.
- **Unenforceable bindings.** Codex cannot enumerate skills, so a
  configured-but-missing skill cannot fail closed there. Nothing may depend on
  that check firing.
- **Scope.** Five children across CLI, config, documents, and two new skills.
  Child 3 is the least defined and the most likely to expand.

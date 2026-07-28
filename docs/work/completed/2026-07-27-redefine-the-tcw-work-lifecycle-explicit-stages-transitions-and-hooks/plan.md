# Coordination plan

This is an epic. It implements nothing itself — each child runs its own
`spec` → `plan` → `implement` → `verify` cycle. This document fixes the child
boundaries, the order, and what must be true at each rollup.

## Dependency order

Almost sequential — each child establishes vocabulary the next one depends on,
with one genuine fork.

```
1. review status + transitions      CLI — the model                 ✅ completed
        ↓
        ├── 2a. transition commits + trunk-branch + DoD    behavior
        │                                                  (joins at 4)
        └── 2b. lifecycle policy config + hooks            configuration
                ↓
        3. methodology resolution   what a stage's "how" resolves from
                ↓
        4. skill + command restructure   docs — describes 1, 2a, 2b, and 3
                ↓
        5. post-mortem skill             needs 4's stage docs to read
```

**The 2a/2b split was made after the combined spec was written and reviewed.**
The original child 2 carried auto-commit, `trunk-branch`, `dod:` removal,
`--already-integrated`, `LifecyclePolicy`, hook execution, policy validation, and
`tcw work lifecycle` — too much for one item, and the two halves share no code.
The reviewed spec sections were carried across unchanged rather than rewritten,
so the review that produced them still applies.

**2a and 2b are genuinely parallel**, and the blocker graph now says so rather
than asserting a false ordering: neither blocks the other, and `reconcile` lists
both as next. Only 2b blocks child 3 — methodology resolution builds on the
binding concept, and has nothing to do with commit behavior.

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
  `WORK_ARTIFACTS` set. ✅ shipped.
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
read without error.

**Corrected by implementation:** this section originally predicted the key would
be *dropped on the next write*. It is not — `set_field` is a read-modify-write
over the raw mapping, so unknown keys survive. The migration is that `phase`
stops being read and displayed; existing items keep an inert key, and no rewrite
pass was added to erase it.

**Done when:** an item traverses `active → review → active → review → completed`;
`rework` refuses while `refined-outcome.md` exists; `complete` still works from
`active` with a warning; a node with no `review/` folder does not crash; `phase`
appears nowhere; and **the Python↔TypeScript status parity test exists and
fails** when the two sets diverge. That test is a named deliverable, not a
by-product — it is the one guard that does not exist today.

## Child 2a — transition commits, trunk-branch, and DoD cleanup

Owns what a transition *does*. No new statuses, no policy schema.

- `auto-commit-transitions` (default **true**) — every transition commits its own
  move, implemented in `FsWorkStore._effect_transition`, the single choke point
  both the CLI and `tcw serve` pass through. Committing has no abstract analog,
  so it belongs in the adapter, not the CLI.
- Commits scoped to the item's source and destination paths, not `docs/work` —
  `git commit -- <paths>` takes working-tree state, so a broad pathspec sweeps in
  every other item's uncommitted edits.
- Three distinct outcomes on a failed commit, never conflated: not a repo and
  nothing-to-commit skip silently; everything else reports and exits non-zero.
- `trunk-branch` — compare `HEAD`, warn on mismatch, commit where you are;
  suppressed when the item's own `branch` field equals `HEAD`.
- Stop persisting `dod:`. Keep the checklist as a closeout prompt; keep the real
  gates. Stage commits stay `[judgment]`; nothing runs at stage end.
- `tcw work complete --already-integrated`.

**Done when:** every transition leaves a commit containing exactly the moved
item; an unrelated edit elsewhere under `docs/work/` is not swept in; a real git
failure is loud while the two benign ones are silent; a `tcw serve` transition is
committed too; `--worktree` produces no duplicate commit.

## Child 2b — lifecycle policy config and the hook layer

Owns the schema and the contract for executing it. Changes no transition
behavior.

- `LifecyclePolicy` + `WorkStore.lifecycle_policy()`; FS adapter reads node-local
  `work.lifecycle`; bindings declared explicitly as `{skill: …}` or
  `{command: …}`, never inferred from a bare string.
- The full hook execution contract: node-root cwd, shell execution, `TCW_*`
  environment, 300s default timeout, `pre` aborts in declared order, `post`
  failure never rolls back.
- **`pre` hooks run before the store is touched at all.** `complete()` writes the
  resolution before it moves the item, so a hook evaluated inside it would strand
  a resolution on an unmoved item. Execution lives in the CLI, which owns the
  ordering — no `WorkStore` change, no transaction concept.
- `tcw validate` rejects unknown ids, non-mapping/non-list shapes, blank or
  duplicate refs, and mappings with neither or both of `skill`/`command` — and
  never reorders or disturbs unrelated config.
- `tcw work lifecycle [work-ref]` in three modes: human, `--json`, `--directive`.

**Done when:** a node with no `work.lifecycle` behaves exactly as before; every
rejected policy shape has a test and an actionable message; `--directive` emits
one complete instruction, or nothing, or exits non-zero on error with empty
stdout; a qualified descendant uses its own node's policy; an aborted `pre` hook
leaves no field written.

**`tcw serve` runs no hooks** — an accepted asymmetry, since running configured
shell from an HTTP handler on a button click is a worse posture than a CLI the
user invoked. The web complete modal must say so rather than leave it inferred.

## Child 3 — methodology resolution

Establishes the concept of skill-use bindings with the smallest surface that
works. Explicitly not the final design.

- `tcw work methodology <stage>` prints the skill to use for that stage, and
  where it came from. Resolution: configured binding → shipped default.
- Unresolved prints nothing and exits 0 — the stage proceeds on TCW's own
  guidance. An unknown stage id exits non-zero.
- Ship a default binding per stage, or none where TCW has no opinion.

The value is that every stage document can then carry one harness-neutral step —
*run `tcw work methodology <stage>` and invoke the skill it names* — reading
identically under Claude and Codex, with dynamic injection reduced to optional
sugar rather than the primary path.

**Explicitly out of scope**, because two reviewers called this the likeliest
child to expand: a repo-local `docs/work/lifecycle/<stage>.md` override, the
three-tier `bare-wins-local` order, a `reset` path, any definition of what a
methodology *document* must contain, and any build step that bakes methodology
into generated files (already rejected — plugin files are replaced on update, and
plugin skills cannot be shadowed). Each can slot in later ahead of the configured
binding without changing this command's contract.

**Done when:** `tcw work methodology <stage>` resolves a configured binding, then
a shipped default, then prints nothing — and reports which of those applied; an
unknown stage exits non-zero; and a node with no configuration behaves exactly as
it does today.

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
| `README.md` | new status, `submit`/`rework`, `tcw work lifecycle`, new commands | 1, 2a, 2b, 4 |
| `docs/release-notes/upcoming.md` | new review step, auto-commit default, methodology overrides | 1, 2a, 2b, 3, 5 |
| `docs/changelogs/upcoming.md` | any code change | all six |
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

Created as `--initiative`, not `--parent`: these are scheduled and completed
independently over time, and `reconcile` follows the initiative relation. The
epic must be `active` before any child can start.

```
E=2026-07-27-redefine-the-tcw-work-lifecycle-explicit-stages-transitions-and-hooks

tcw work new "Add the review status and the submit/rework transitions" \
    --initiative $E --tag work --tag cli --effort high --complexity high --priority 10
tcw work new "Commit every work transition; trunk-branch and DoD cleanup" \
    --initiative $E --tag work --tag cli --effort high --complexity medium --priority 9
tcw work new "Add lifecycle policy config and the hook layer" \
    --initiative $E --tag work --tag cli --effort high --complexity high --priority 9
tcw work new "Add tcw work methodology to resolve a stage's skill binding" \
    --initiative $E --tag work --tag cli --effort medium --complexity low --priority 8
tcw work new "Restructure the tcw-work skill into per-stage references and commands" \
    --initiative $E --tag skills --tag docs --effort high --complexity medium --priority 7
tcw work new "Add the post-mortem skill and its verify-stage trigger" \
    --initiative $E --tag skills --effort medium --complexity low --priority 6
```

**Ordering is enforced, not described.** `blocked_by` chains 2b → 3 → 4 → 5, so
`start()` fails closed on an unresolved blocker and `reconcile`'s **Next** names
only what is actually workable. 2a and 2b carry no blocker between them, which is
the graph stating the truth that they are parallel.

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
- **Scope.** Six children across CLI, config, documents, and two new skills — child 2 was split once its spec showed how much it carried.
- **Child 3 is a deliberate down payment.** It ships the binding concept without
  the override model, so the first design that builds on it may want the command
  to answer differently. Its contract — "name the skill for this stage" — is
  chosen to survive that, but it is an untested bet.

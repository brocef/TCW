# Implementation plan

## Overview

Implement the lifecycle compatibility layer in six ordered phases. Keep the
checkpoint contract in the storage-neutral model, configuration parsing in the
filesystem adapter, CLI behavior in the work command layer, and methodology in
agent skills. Preserve default lifecycle and worktree behavior throughout.

Do not begin this plan until the user explicitly requests implementation. At
that point, run `tcw work start
2026-07-22-planning-agnostic-tcw-lifecycle-orchestration` and commit that status
transition before the first code edit.

## Phase 1: Register the product language and capability delta

1. Add `lifecycle-checkpoint` as concise Vocabulary for a stable point in the
   TCW-owned work lifecycle.
2. Add `configurable-work-lifecycle` as a Feature operating on the relevant
   work/lifecycle vocabulary.
3. Expand `docs/capabilities/plugin/work-lifecycle` to cover configured ordered
   mappings and the fixed ownership boundary.
4. Add a Missing capability for auditing one skill or a complete configured
   workflow.
5. Add or update the worktree closeout capability to describe completion after
   external integration.
6. Record new and changed paths in this work item's `capabilities.yaml`, with
   planning pointers on new entries.
7. Run contradiction checks before mutations, then `tcw taxonomy check` and
   `tcw capabilities check`.

Expected touch points:

- `docs/taxonomy/`
- `docs/capabilities/plugin/work-lifecycle/`
- the relevant worktree completion capability under `docs/capabilities/work/`
- this work item's `capabilities.yaml`

## Phase 2: Model and parse lifecycle policy

1. Define the ordered checkpoint constants and immutable contract data in the
   work model, including objectives, allowed artifacts, required evidence, and
   destination paths.
2. Add the storage-neutral `LifecyclePolicy` type and abstract
   `WorkStore.lifecycle_policy()` operation in `tcw/store/base.py`.
3. Implement `FsWorkStore.lifecycle_policy()` in `tcw/store/fs.py`, reading only
   the resolved node's `tcw-config.yaml`.
4. Parse ordered opaque skill-reference lists without resolving installed
   skills, applying empty defaults for omitted checkpoints.
5. Integrate structural errors with `tcw validate` in `tcw/validate.py`:
   unknown checkpoints, malformed mappings/lists, blank or non-string values,
   and duplicates.
6. Ensure config writes used elsewhere preserve `work.lifecycle` and unrelated
   keys.

Tests:

- Add focused policy tests for the empty default and a fully configured policy.
- Assert checkpoint and skill declaration order.
- Parameterize every invalid shape and value.
- Assert unrelated configuration survives existing config mutations.
- Assert lifecycle configuration does not inherit from parent or connected
  nodes.

## Phase 3: Add read-only lifecycle inspection

1. Add `tcw work lifecycle [work-ref] [--json]` to `tcw/work/cli.py`.
2. Resolve no argument to the current node, a bare reference to the local item,
   and a qualified reference through the registered project graph.
3. Render all checkpoint contracts in fixed order with configured skills in
   declaration order.
4. Keep human and JSON rendering sourced from the same model data.
5. Return actionable errors for unresolved or invalid work references without
   changing state.

Tests:

- Cover default and configured human output.
- Cover stable JSON structure and ordering.
- Cover local, descendant, and qualified descendant items.
- Prove a descendant item reads the descendant node's policy rather than the
  invoking node's policy.
- Add smoke/help assertions for the new public CLI surface.

## Phase 4: Extend integration-aware completion

1. Add `--already-integrated` to `tcw work complete` in `tcw/work/cli.py`.
2. Restrict it to an item carrying TCW-created worktree metadata and keep normal
   `--confirm`, resolution, blocker, definition-of-done, and capability gates.
3. When selected, skip `merge_worktree()` and evaluate gates against the primary
   checkout's current state.
4. Make `remove_worktree()` cleanup best-effort when the integration skill has
   already removed the branch or worktree, without masking real completion
   failures.
5. Preserve the existing merge-first behavior when the flag is absent.
6. Ensure creating a pull request or retaining a branch leaves the item active;
   document resumption with `--already-integrated` only after integration.

Tests in `tests/test_work.py` should prove:

- default worktree completion still merges before capability checks;
- `--already-integrated` never invokes merge;
- capability and completion gates still block;
- gates read the primary checkout;
- already-removed branch/worktree state is tolerated;
- remaining TCW-created state is cleaned safely;
- non-worktree items reject the flag clearly;
- qualified descendant worktree completion behaves consistently.

## Phase 5: Implement agent orchestration and audit surfaces

1. Keep `skills/tcw-work/SKILL.md` a thin router and update its always-relevant
   ownership rules and quick reference.
2. Update `skills/tcw-work/references/lifecycle.md`,
   `task-lifecycle.md`, and `epic-lifecycle.md` as needed to:
   - inspect the effective lifecycle policy;
   - preflight configured skill availability and fail closed;
   - invoke skills in declared order through the fixed prompt envelope;
   - preserve generic TCW behavior for unmapped checkpoints;
   - record review, verification, and integration evidence in the bounded
     artifact spine;
   - reserve commits and transitions for TCW.
3. Update `commands/tcw-plan-work.md` and
   `commands/tcw-drive-work-to-completion.md` to route through configured
   checkpoints without duplicating the lifecycle reference documents.
4. Add a thin `skills/tcw-lifecycle-audit/SKILL.md` router, with a reference
   document only if the conditional audit procedure is large enough to justify
   progressive disclosure.
5. Add `commands/tcw-audit-lifecycle-skill.md`. With an argument, inspect one
   skill; without one, inspect all effective mappings and adjacent handoffs.
6. Define evidence-backed `compatible`, `conditional`, and `incompatible`
   classifications covering paths, stage fit, subskills, handoffs, approvals,
   TCW ownership, completion claims, cleanup, availability, and destructive
   actions.
7. Add Superpowers-shaped fixtures for compatible mappings, fixed-output-path
   conflicts, hard-coded handoffs, missing required skills, and workflow gaps.
8. Update Claude and Codex plugin manifests and packaging tests so both new
   surfaces ship. Update `.agents/plugins/marketplace.json` only if its
   versionless availability metadata needs the new skill declared; do not add a
   version.

Expected tests:

- `tests/test_skill_flow.py`
- `tests/test_plugin_manifests.py`
- focused fixture tests for lifecycle audit instructions and classifications

## Phase 6: Documentation, reconciliation, and verification

Documentation Sync triggers expected to fire:

1. Update `README.md` for lifecycle configuration, inspection, audit, and the
   already-integrated closeout route. Present the Superpowers mapping only as an
   example.
2. Update `docs/release-notes/upcoming.md` in user-facing language because the
   public CLI and workflow behavior change.
3. Update `docs/changelogs/upcoming.md` with technical detail and the final
   implementation commit hash range because runtime behavior changes.
4. Ensure the matching `tcw-work` skill is synchronized with the component's
   CLI, model, lifecycle, and guardrails; this is mandatory for the
   Skill-Driven-Component trigger.
5. Update capability statuses and descriptions so all declared new entries are
   no longer Missing and all changed entries match shipped behavior.
6. Run the complete verification matrix:

   ```text
   python -m pytest
   pnpm prettify:check
   tcw taxonomy check
   tcw capabilities check
   tcw validate
   git diff --check
   ```

7. Record implementation and verification evidence in `outcome.md`, then stop
   for explicit user verification and refinement. Do not complete the item or
   cut a release without the user's closeout choices.

## Parallelization and dependencies

- Phases 1 and 2 may be prepared in parallel after the start checkpoint, but
  model contract names must settle before capability wording is finalized.
- Phase 3 depends on the Phase 2 model and adapter operation.
- Phase 4 is mostly independent of Phase 3 after the CLI parser touch points are
  coordinated.
- Audit fixtures and plugin packaging work in Phase 5 can proceed alongside
  Phase 4, while lifecycle skill text depends on the final checkpoint contract.
- Phase 6 depends on all behavioral phases and must use the actual final diff and
  commit range.

## Implementation guardrails

- Apply the abstraction litmus test to every `WorkStore` operation; filesystem
  paths and Git commands remain adapter or CLI details.
- Keep skill references opaque to the Python model and preserve their order.
- Source human and JSON contracts from one canonical definition.
- Do not let mapped skills commit, transition, reconcile capabilities, or claim
  TCW completion.
- Preserve unrelated working-tree changes and use narrow lifecycle commits.
- Do not introduce a Superpowers dependency or preset.
- Do not cut or push a release as part of implementation without explicit user
  direction.

# Registered project graph and stable project IDs — implementation plan

## Capability changes

- Add the `connected-project-registry` Feature over `node`, `namespace`, and
  `reference`.
- Update and link these existing capabilities:
  `cli/host-multiple-projects-in-one-repo`,
  `cli/scaffold-the-doc-trees`, `cli/validate-a-node`,
  `cli/reference-a-tcw-object`, `taxonomy/federate-shared-vocabulary`,
  `capabilities/federate`, `work/view-the-board`, and `web`.
- Keep the change ledger in this item's `capabilities.yaml` under `changed:`;
  no new capability is introduced.

## Execution policy

Phases are ordered because the registry contract becomes the shared dependency
for every later migration. Test/doc updates within a phase may be developed
alongside their code, but this item is executed sequentially unless the user
explicitly requests subagent parallelization. Preserve unrelated worktree
changes and checkpoint lifecycle artifacts separately.

## Phase 1 — start the lifecycle

1. Run `tcw work start
   2026-07-20-registered-project-graph-and-stable-project-ids`.
2. Inspect and commit only the backlog-to-active status move.
3. Confirm the item is active before modifying implementation or product files.

## Phase 2 — establish project identity and the abstract registry

Expected touch points: `tcw/store/base.py`, a focused project-registry module in
`tcw/store/` (split from `fs.py` if that keeps the abstraction legible),
`tcw/store/fs.py`, and new registry tests.

1. Define immutable project records and an abstract `ProjectRegistry` interface
   for current ID, direct relations, ID lookup, ancestors, descendants, and
   validation. Keep locator types opaque and avoid filesystem vocabulary.
2. Define the project-ID regex and reserved set in one reusable location.
3. Implement strict YAML loading for `tcw-config.yaml`, including duplicate-key
   rejection and shape/type checks.
4. Implement `FsProjectRegistry`:
   - begin from the nearest selected sentinel;
   - resolve only declared absolute or config-relative locators;
   - cache each canonical config path once;
   - check existence, target-ID/key agreement, one parent, reciprocal edges,
     reciprocal target equality, unique IDs/configs, and cycles;
   - expose deterministic ancestor/descendant order and ID lookup.
5. Remove topology meaning from `child_nodes`, `descendant_nodes`,
   `parent_node`, and filesystem-qualified resolution. Delete them when all
   consumers have migrated; keep git helpers used solely for worktree lifecycle.
6. Add focused tests for valid arbitrary layouts, absolute/relative locators,
   siblings/out-of-tree nodes, deep traversal, invalid/reserved/missing IDs,
   malformed shapes, duplicate YAML keys, missing targets, mismatched keys,
   nonreciprocal links, multiple parents, duplicate IDs, and cycles.
7. Instrument reads/subprocess calls to prove one config load per node, no
   directory walk, no git call, and no access to unregistered/decoy/worktree
   nodes.

## Phase 3 — migrate initialization and command bootstrapping

Expected touch points: `tcw/cli.py`, initialization helpers in
`tcw/store/fs.py`, component CLI parsers/modules, and init tests.

1. Add `--id` to top-level and taxonomy/capabilities/work init parsers.
2. Validate IDs before scaffolding or writing.
3. Require an ID for a new marker; reuse an existing configured ID when omitted;
   accept an identical supplied ID; reject a conflicting supplied ID.
4. Permit `tcw init --id <id>` to backfill an ID-less sentinel while preserving
   tags, connected-project configuration, component settings, comments where
   feasible under the existing YAML writer contract, and unknown keys.
5. Centralize command bootstrap so every non-init command loads/validates the
   registry and fails clearly on ID-less/invalid graphs with a concrete
   `tcw init --id <id>` migration instruction.
6. Update init and CLI tests for all mirrors, preservation, idempotence,
   conflicts, invalid/reserved values, and legacy markers.
7. Backfill this repository's own `tcw-config.yaml` with `id: tcw` as part of
   the implementation so subsequent commands run under the new invariant.

## Phase 4 — migrate work topology and coordination

Expected touch points: `tcw/store/base.py`, `tcw/store/fs.py`, work command
modules under `tcw/work/`, `tcw/cli.py`, and topology/work tests.

1. Inject or construct the registry for `FsWorkStore` without adding
   filesystem-only methods to `WorkStore`.
2. Replace child/descendant/parent store discovery with registry relations.
3. Resolve a qualified ref only as `<registered-descendant-id>/<slug>`;
   preserve local bare and status-qualified refs.
4. Emit `<project-id>/<slug>` for every descendant board entry and group headers
   by project ID, including deep descendants.
5. Convert `work nodes`, initiative lookup, epic rollups/reconcile,
   delegate/escalate destinations, and inbox `from:` metadata to stable IDs.
6. Ensure delegation targets direct registered children and escalation targets
   the direct registered parent; relation traversal must work across arbitrary
   filesystem placement.
7. Replace legacy path-oriented tests with registered graphs and cover every
   affected command, lifecycle gate, reconcile path, and unknown-ID failure.

## Phase 5 — migrate taxonomy and capability inheritance

Expected touch points: `tcw/store/base.py`, `tcw/store/fs.py`,
taxonomy/capability CLI modules, and federation/override tests.

1. Change both store configs to parse `extends` as a list of unique project IDs.
2. Resolve listed IDs through the current registry and open only the selected
   axis store at the registered target.
3. Use the source project ID as `origin`, inherited namespace, qualification,
   and capability override target prefix.
4. Change taxonomy and capability `extends add` to one project-ID argument;
   retain `rm <project-id>`.
5. Reject legacy maps, unknown IDs, self-extension, unreachable targets,
   missing axis stores, duplicates, ambiguity, and inheritance cycles.
6. Preserve inherited lookup, explicit selection, read-only inherited
   structure, local capability overrides, reset semantics, attachment/body
   composition, and taxonomy/capability check behavior.
7. Update all federation, override, CLI, validation, and serve fixtures to build
   reciprocal registered graphs.

## Phase 6 — migrate validation and `tcw://` resolution

Expected touch points: validation/reference modules located from `tcw/cli.py`
imports, store resolvers, and `tests/test_validate.py`.

1. Validate the whole current registry before any narrowed validation work.
2. Keep file/directory narrowing for YAML/Markdown/component checks.
3. Resolve work namespaces only among registered descendants.
4. Resolve taxonomy and capability namespaces only among their explicit
   `extends` project IDs.
5. Keep bare references local and preserve axis/path validation.
6. Add failures for unknown IDs, unregistered-but-present nodes, unreachable
   inheritance, legacy maps, and invalid graphs even when validating one file.

## Phase 7 — migrate the web API and UI

Expected touch points: `tcw/serve/__init__.py`,
`tcw/serve/static/app.js`, related styles/templates only if labels change, and
`tests/test_serve.py`.

1. Build the hosted-node set from the registry, never `descendant_nodes`.
2. Use project IDs in work object identifiers, route segments, board group
   labels, API payloads, and cross-project `tcw://` navigation.
3. Resolve work writes and reads through the same descendant-ID gate as the CLI.
4. Keep local taxonomy/capability rendering and explicit inheritance navigation
   aligned with the new namespace rules.
5. Reject unknown or non-hosted project IDs and keep dangling/foreign links
   inert.
6. Update API/UI tests for deep and out-of-tree descendants, editing endpoints,
   history/deep links, rollups, and project-ID-qualified objects.

## Phase 8 — taxonomy, capability, and documentation sync

Expected touch points: `docs/taxonomy/`,
the eight `docs/capabilities/` entries, `README.md`, the migration guide under
`docs/`, `docs/release-notes/upcoming.md`,
`docs/changelogs/upcoming.md`, `skills/tcw-work/SKILL.md` and its cross-node
reference, `skills/tcw-taxonomy/SKILL.md`, and
`skills/tcw-capabilities/SKILL.md`.

1. Use `tcw taxonomy add "Connected project registry" --kind feature` with
   vocabulary refs `node`, `namespace`, and `reference`; use the requested
   `connected-project-registry` slug and validate it.
2. Update the eight changed capability descriptions for stable addressing,
   arbitrary placement, explicit inheritance, and fail-closed registration.
3. Use `tcw capabilities set` to associate each changed capability with
   `Feature=connected-project-registry`; preserve useful existing subjects.
4. Update `README.md` because the public CLI/configuration surface and
   user-facing behavior change.
5. Update the migration guide with an explicit sequence for assigning IDs,
   registering reciprocal edges, converting `extends` maps to ID lists, and
   replacing path-qualified work/reference values. State that no fallback or
   compatibility aliases exist.
6. Update `skills/tcw-work/SKILL.md` and its cross-node lifecycle reference,
   `skills/tcw-taxonomy/SKILL.md`, and `skills/tcw-capabilities/SKILL.md` because
   each driven component's CLI, model, and guardrails change. Remove scanning,
   filesystem-hierarchy, path-alias, and sibling-path guidance.
7. Update user-facing `docs/release-notes/upcoming.md` for the breaking project
   graph and migration.
8. Update developer-facing `docs/changelogs/upcoming.md` under appropriate
   Added/Changed/Removed/Internal sections with the implementation commit hash
   range. This trigger fires for all behavior-affecting code changes.
9. Search the repository (excluding historical completed work artifacts) for
   stale path aliases, scanning, sibling-path inheritance, and path-qualified
   descendant guidance; update every live surface.

## Phase 9 — verification and lifecycle evidence

1. Run focused suites for registry, nodes/init, qualified refs, work topology,
   taxonomy, capabilities/overrides, validation, CLI, and serve.
2. Run the full suite:

   ```bash
   python -m pytest
   ```

3. Run repository checks:

   ```bash
   tcw capabilities check
   tcw taxonomy check
   tcw validate
   python -m pytest tests/test_plugin_manifests.py
   git diff --check
   ```

4. Exercise representative CLI flows in temporary git repositories:
   ID creation/backfill, arbitrary-layout reciprocal graphs, descendant boards
   and qualified commands, delegation/escalation/reconcile, explicit taxonomy
   and capability inheritance, and invalid-graph failures.
5. Record implementation, deviations, changed files, and exact verification
   results in `outcome.md`; checkpoint it separately.
6. Invoke the documentation-sync skill and confirm every configured trigger was
   evaluated and the three component-driving skills match implementation.
7. Reconcile the changed capability ledger and verify every path resolves with
   the new Feature association.
8. Pause for user verification/refinement. Do not complete the item or cut a
   release yet.

## Phase 10 — acceptance-gated closeout

Only after explicit user approval:

1. Apply requested refinements and rerun proportional/full verification.
2. Write `refined-outcome.md` with the acceptance decision and final evidence;
   commit it separately.
3. Run `tcw work complete
   2026-07-20-registered-project-graph-and-stable-project-ids --resolution done
   --confirm` and commit the completion transition.
4. Cut the selected breaking release with:

   ```bash
   python scripts/cut_version.py major
   ```

5. Verify all five version-bearing files agree, the upcoming docs rotated, the
   release commit/tag exist, and the worktree is clean. Do not push unless the
   user separately requests publishing.

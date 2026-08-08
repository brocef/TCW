# Implementation plan: concurrency-safe work claims and external per-project work stores

## Capability changes

- Add `work/configure-the-work-store-location` and its
  `configurable-work-store-location` Feature.
- Update `cli/scaffold-the-doc-trees`, `cli/host-multiple-projects-in-one-repo`,
  and `work/keep-resolved-work-out-of-git`.
- Update `work/start-a-work-item` to document claimant identity, atomic
  single-winner start behavior, contention diagnostics, and the distinct
  `--take-over` path while preserving `--force` for blocker/initiative bypass.
- Update `work/view-the-board` to document owner and start-time presentation for
  active work, including legacy unclaimed items.
- No capability is added or removed, and no taxonomy entry changes.

## Tasks

0. **Implement external per-project work-store placement.** Separate the owning
   code node, configured work root, and work-store Git root in `FsWorkStore`;
   keep placement out of `WorkStore`. Resolve default, relative, absolute,
   symlinked, broken, and linked-worktree cases through one factory. Route all
   CLI, web, validation, reconciliation, reference, staging, transition, and
   resolved-ignore behavior through it. Reject duplicate physical roots across
   registered projects.

   Add `tcw work init --path` and top-level `tcw init --work-path`. External init
   writes configuration, scaffolds the target, installs target-relative ignore
   rules in its Git repository, remains non-committing, and reports both roots.
   Permit replacement only of an exactly pristine generated default scaffold;
   refuse existing items, inbox entries, custom files, invalid/non-Git targets,
   and document manual migration. Verify with default/relative/absolute/symlink/
   broken-link/linked-worktree tests and two-repository integration coverage,
   including qualified commands, boards, hooks, code worktrees, web editing,
   validation, unrelated changes, and store-root collisions.

1. **Separate the code node, work root, and work-store Git root.** Refactor
   `FsWorkStore` construction without changing `FsTreeStore` for the other axes:
   read `work.path` from the code node's `tcw-config.yaml`, resolve default,
   relative, and absolute forms, retain the code `node_root`, and discover the
   Git worktree containing the resolved work root. Make malformed types, missing
   directories, invalid work-tree shapes, and non-Git roots under automatic
   commit produce one config-specific error shared by commands and validation.
   Keep direct/default construction compatible for isolated adapter tests.
   Update every `FsWorkStore.open(node_root)` entry path only through this common
   factory so CLI, qualified references, recursive boards, validation,
   capabilities gates, and the web server cannot disagree.

   Verify with focused store/config and validation tests covering absent/blank,
   relative-inside-node, absolute-external, malformed, missing, wrong-shape, and
   non-Git configurations; run the existing node discovery, project registry,
   qualified-reference, recursion, serve, and environment-hardness suites to
   prove the default path is unchanged.

2. **Route filesystem and Git effects to the correct root.** Give
   `FsWorkStore` adapter methods an explicit work-state Git root while preserving
   `node_root` for sentinel reads, registry traversal, lifecycle policy, and hook
   cwd. Replace hard-coded `docs/work/...` transition/worktree pathspecs with
   paths derived from the configured store. In external mode, commit status
   changes in the work repository and create/merge/remove code worktrees in the
   code repository; retain today's single-repository behavior by default.
   Confirm ignored resolved-status handling, scoped commits, off-trunk warnings,
   auto-commit disabled behavior, and transition-commit failure reporting use
   the intended repository.

   Verify with two-repository integration tests for ordinary transitions and
   `start --worktree`, assertions on each repository's commits and untouched
   unrelated changes, plus the existing worktree and transition-auto-commit test
   modules.

3. **Add the storage-neutral atomic claim contract and metadata.** Extend
   `WorkItem` and filesystem serialization with optional `owner` and `started`
   fields. Add the typed `AlreadyClaimed` result and a `WorkStore` claim/takeover
   operation whose documented semantics can be implemented transactionally by a
   remote adapter. Keep blocker and initiative checks in the model and keep
   ordinary legal transitions independent of the filesystem protocol. Clear
   claim metadata when leaving active; ensure rework yields an unowned active
   item and legacy state files remain readable.

   Verify with model-level fake-store tests for backlog claim, active
   contention, takeover, illegal statuses, blocker/initiative `force`, metadata
   clearing, rework, and legacy items. Run the full abstract work-store tests so
   no filesystem-only method leaks into caller behavior.

4. **Implement atomic filesystem publication and interrupted-claim recovery.**
   Realize ordinary claims by atomically moving the backlog item into an
   adapter-private claiming area, stamping the exclusively owned state, and
   atomically publishing it to active before Git staging/commit. Translate a
   lost source race into `AlreadyClaimed` after a short, bounded wait for the
   winner's publication; do not retry unrelated Git failures. Exclude private
   claiming directories from query, locator, reference, and validation surfaces.
   Detect a process death between acquisition and publication, report it
   explicitly, and allow only an explicit takeover to recover and publish that
   directory.

   Verify with deterministic barrier-controlled two-store races, repeated
   process/thread stress tests, read-during-publication assertions, injected
   failures at both rename boundaries, interrupted recovery/takeover cases, and
   held-`index.lock` tests proving exactly one claimant wins even when the later
   commit fails. Include nested work items and pre-existing active destination
   cases in the sibling-defect sweep.

5. **Wire claimant identity, takeover, hooks, and worktree sequencing through
   the CLI.** Add `--owner` and `--take-over`; resolve identity from the flag,
   `TCW_WORK_OWNER`, Git email, then Git name, and reject an unresolved identity.
   Preserve `--force` exclusively for blocker and initiative gates. Render typed
   contention and interrupted-claim errors without tracebacks. Ensure only the
   winning ordinary claim runs post-start hooks and worktree setup; run start
   bindings for an explicit takeover and preserve the truthful "moved but commit
   failed" result.

   Verify with CLI tests for identity precedence/whitespace, missing identity,
   ordinary contention, legacy unknown ownership, active takeover, interrupted
   takeover, `--force` non-takeover, hook invocation counts, and losing
   `--worktree` contenders. Run existing blocker, initiative, lifecycle-hook,
   recursion, and worktree tests.

6. **Expose claim metadata in every read surface.** Append owner and UTC start
   time to active CLI board rows, render legacy active items as unclaimed, and
   include the fields in `work show`. Carry the fields through the serve API and
   display them in the web client's active-item metadata without adding browser
   takeover controls. Confirm descendant/qualified boards preserve the metadata
   when they clone or qualify `WorkItem` values.

   Verify with CLI snapshot/assertion tests, serve API tests, client component
   tests, and a production client build; run board ordering, descendant-board,
   and serve parity suites.

7. **Run the finished implementation through repository-wide verification.**
   Run the complete pytest suite, `tcw taxonomy check`, `tcw capabilities check`,
   `tcw validate`, and `git diff --check`. Exercise a manual two-process claim
   against a temporary shared work repository to confirm the operator-facing
   winner/loser messages and inspect both Git histories. Record any behavior the
   automated suite cannot make deterministic in `outcome.md` rather than
   weakening the acceptance criteria.

## Documentation Sync

8. **Reconcile the changed capability records.** Update
   `docs/capabilities/work/start-a-work-item/description.md` and
   `docs/capabilities/work/view-the-board/description.md` to match the verified
   behavior declared in `capabilities.yaml`. Before editing, repeat the
   contradiction check against the finished implementation; if implementation
   and intended capability differ, stop and surface the conflict rather than
   silently choosing one. Verify with `tcw capabilities check` and `tcw
   validate`.

9. **Update `README.md` [Public-API].** Document `work.path`, shared-store setup
   and validation expectations, claimant identity precedence, contention and
   interrupted-claim recovery, `--take-over`, board metadata, and the external
   store/`--worktree` split. Verify every shown command against `tcw --help` and
   the CLI tests, then run `git diff --check`.

10. **Update `skills/tcw-work/SKILL.md` [Skill-Driven-Component].** Teach agents
    to supply an owner, treat start as a claim, select another item after typed
    contention, and use takeover only deliberately; route uncommon shared-store
    setup or recovery detail into a reference if it is large enough to satisfy
    the skill's progressive-disclosure rule. Update command/lifecycle references
    whose start syntax or guardrails changed. Verify with the skill parity tests
    and `git diff --check`.

11. **Update `docs/release-notes/upcoming.md` [Public-API].** Add a plain-language
    user-facing account of safe multi-agent claims, visible ownership, takeover,
    and configurable shared work storage. Verify terminology against the README
    and capability descriptions and run `git diff --check`.

12. **Update `docs/changelogs/upcoming.md` [Any-Code-Change].** Record the model,
    CLI, filesystem adapter, configuration, web presentation, and compatibility
    changes in the appropriate technical sections. Verify referenced flags and
    fields against the final code and run `git diff --check`.

13. **Repeat the complete verification after the documentation block.** Run the
    full pytest suite, `tcw taxonomy check`, `tcw capabilities check`, `tcw
    validate`, and `git diff --check` so capability and skill documentation are
    reviewed with the implementation rather than as an unchecked follow-up.

## Verification

The automated suite must prove the single-winner invariant, atomic visibility of
claim metadata, explicit interrupted-claim recovery, default-path compatibility,
and separation of code-repository and work-repository effects. The manual
two-process check in task 7 covers real OS scheduling and Git subprocess
interaction that mocked barriers cannot fully represent. During verification,
inspect both repositories' `git status --short` and recent scoped commits to
confirm unrelated staged and unstaged files were not swept in.

Do not start this item until its recorded blocker,
`2026-07-28-fold-the-trial-audit-s-findings-into-five-backlog-items`, is resolved
or the user deliberately authorizes the existing blocker override. Stop after
verification for user acceptance; completion and any version cut remain separate
decisions.

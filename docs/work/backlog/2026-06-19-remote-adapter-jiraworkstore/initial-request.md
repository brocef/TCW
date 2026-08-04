# Full external TCW store adapters

**Status: theoretical backlog item; retain until a concrete external-store use
case justifies specification.**

The stable slug retains the original `remote-adapter-jiraworkstore` wording for
history. The request is no longer Jira-specific and does not describe the
supplemental external-tracker bridge tracked separately.

## Product changes

Allow a project to keep one or more TCW axes entirely in external services
instead of the shipped filesystem stores. Taxonomy, Capabilities, and Work would
still expose the same TCW concepts and lifecycle, but their durable objects could
live in a tracker, wiki, graph database, or another service selected by the
project.

This remains theoretical. No current TCW consumer requires full replacement of
the filesystem methodology, and the filesystem's co-located, reviewable artifacts
remain the preferred default.

## Technical changes

TCW already has three independent abstract store interfaces:
`TaxonomyStore`, `CapabilitiesStore`, and `WorkStore`. A full remote deployment
means concrete implementations of whichever axes a project externalizes; it does
not mean introducing one monolithic adapter interface across all three axes.

The existing abstractions make remote implementations possible, but they are not
yet plug-and-play configuration points. The CLI and several cross-axis services
still construct or import filesystem stores directly. Before a remote adapter can
be selected, this item must inventory those seams and add provider selection and
dependency wiring without weakening the abstract spine.

Any future specification must apply the repository litmus test to each operation:
the portable model remains item/status/transition/reference/query/body/fields/
attachments, while filesystem discovery, paths, git operations, and worktrees
remain filesystem-adapter details.

Potential implementations include a `JiraWorkStore`, wiki-backed taxonomy or
capability stores, and database-backed stores. None is selected or promised by
this item.

## Boundaries

This item does **not** include:

- supplementing `FsWorkStore` with an external tracker for intake, assignment,
  claims, and status visibility;
- remote git/URL locators used to feed an otherwise filesystem-backed taxonomy;
- synchronizing selected capability metadata with tracker records; or
- building an adapter before a real consumer establishes its provider,
  permissions, consistency, and migration requirements.

Those are supplemental integrations with different authority and failure models,
not full store replacements.

## Meta changes

Keep this item at low priority. When a concrete consumer appears, specification
must cover adapter selection per axis, configuration and credentials, stable
identity, consistency and conflict handling, migration in both directions,
cross-axis references, CLI/service dependency injection, validation, and parity
under Claude Code and Codex.

Historical references: `docs/plan/phase-6-beyond.md` and
`docs/plan/phase-5-work.md` Part C. Their statement that a `JiraWorkStore` is
"purely additive" is directionally correct at the interface boundary but
overstates the current readiness of the CLI wiring.

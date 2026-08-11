# Add path commands for TCW storage folders

## Capability changes

- Add `cli/locate-tcw-storage-folders` as `Missing`, linked to this work item,
  then mark it `Supported` once all four root-location commands are implemented.
- Change `work/read-a-work-item` to document the no-argument work-root form while
  preserving `tcw work path <slug>`.
- Change `work/manage-the-work-inbox` to document `tcw work inbox path`.
- No taxonomy delta is needed: the registered `cli` and `store` vocabulary
  already names the concepts involved.

## Problem

TCW exposes filesystem-backed stores but does not provide a consistent CLI way
to discover their physical roots. Taxonomy and capabilities reserve no `path`
command in their normalization registries, so bare `path` is currently treated
as shorthand for `show path` (`tcw/taxonomy/cli.py:9-11`,
`tcw/capabilities/cli.py:10-12`). Work has an item-only path command whose parser
requires a slug (`tcw/work/cli.py:1040-1042`). The work adapter can also route to
a configured external store and resolves that root when it opens
(`tcw/store/fs.py:1920-1951`), but users cannot print the selected root or its
inbox folder.

## Goals

- Provide one exact-output root-location command for taxonomy, capabilities,
  work, and the work inbox.
- Preserve all existing work-item path resolution behavior.
- Ensure work-root output follows `work.path`, including external stores.
- Keep physical-path presentation in filesystem-aware CLI code.

## Non-goals

- Add filesystem paths to `TaxonomyStore`, `CapabilitiesStore`, or `WorkStore`.
- Add remote store adapters, migrations, taxonomy entries, or a version bump.
- Change item-resolution rules, transition behavior, or error wording.
- Accept taxonomy objects, capabilities, or inbox entries as arguments to the
  new root-location commands.

## Design

Add `path` to the taxonomy and capabilities `SUBCOMMANDS` registries and parser
trees. Each handler opens its existing filesystem adapter and prints
`store.root`, which is already an absolute resolved path through the shared
filesystem store initialization. This reserves `path` as a command; an entry or
capability named `path` remains available through explicit `show path`.

Make the work `path` positional slug optional. With no slug, open the active
`FsWorkStore` and print its resolved `root`. With a slug, retain the current
qualified resolver and item lookup unchanged. Add `path` beneath `work inbox`
and print `store.inbox_root`, keeping inbox location derived from the active
filesystem adapter.

No abstract-store method is introduced: a non-filesystem adapter need not
provide a local path, and the commands are presentation affordances of the
shipped filesystem adapters.

## Acceptance criteria

- `tcw taxonomy path`, `tcw capabilities path`, `tcw work path`, and
  `tcw work inbox path` each exit zero and print exactly one absolute, symlink-
  resolved path plus a newline.
- `tcw work path <slug>` continues to resolve local, status-qualified, and
  cross-project work items and retains its missing-item errors.
- A configured external work store supplies both `tcw work path` and
  `tcw work inbox path` output.
- Taxonomy and capabilities dispatch bare `path` as a command, while explicit
  `show path` still addresses an object named `path`.
- Outside a matching component, each command exits non-zero, emits the existing
  component-not-found error on stderr, and prints no path on stdout.
- No abstract store interface gains a filesystem-path operation.
- Focused tests, the full Python suite, taxonomy and capability checks,
  `tcw validate`, and `git diff --check` pass.
- Public CLI docs, release notes, changelog, the taxonomy/capabilities/work
  driving skills, and the work command reference describe the final behavior.

## Risks

- Reserving `path` changes the meaning of taxonomy/capabilities shorthand for an
  object with that literal name; explicit `show path` is the intentional escape.
- Refactoring the work handler could accidentally bypass qualified item
  resolution; tests must retain all existing slug cases.
- Using the node's conventional `docs/work` path instead of the opened store's
  root would report the wrong location for configured external stores.

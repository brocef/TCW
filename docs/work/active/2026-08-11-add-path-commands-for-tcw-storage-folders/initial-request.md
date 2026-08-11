# Add path commands for TCW storage folders

## Product changes

- Add `tcw taxonomy path`, `tcw capabilities path`, and no-argument
  `tcw work path` commands that each print the absolute, resolved folder for
  the active component's filesystem store.
- Add `tcw work inbox path` to print the absolute, resolved inbox folder inside
  the active work store.
- Preserve `tcw work path <slug>` as the exact path lookup for a work item,
  including status-qualified and cross-project references.
- Reserve `path` as a taxonomy and capabilities subcommand while keeping an
  object literally named `path` readable through explicit `show path`.

## Technical changes

- Present filesystem adapter roots directly in the CLI without adding path
  concepts to the abstract taxonomy, capabilities, or work store interfaces.
- Respect configured external work stores for both the work root and inbox
  root.
- Add focused CLI coverage for exact stdout, failure behavior outside matching
  components, and preservation of existing item-path resolution.

## Meta changes

- Track the new root-location capability and the affected work-item and inbox
  capabilities in the work item's capability ledger.
- Update public CLI documentation, release notes, changelog, all three driving
  skills, and the work command reference.
- Submit the verified item for review. Do not complete it or cut a release
  without explicit acceptance.

## Notes

- The supplied implementation plan is the authoritative request and no further
  reference material was provided.
- Taxonomy, capabilities, and inbox root commands accept no object or entry
  argument. Successful output is exactly one path plus a newline, with no label
  or hint.
- No taxonomy change, migration, model/store-interface change, or version bump
  is requested.

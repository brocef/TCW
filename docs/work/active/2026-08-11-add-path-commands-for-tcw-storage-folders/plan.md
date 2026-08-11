# Implementation plan

1. Add focused failing CLI tests for each root command in the existing taxonomy,
   capabilities, and work test modules. Assert exact stdout and exit status,
   command dispatch for the reserved taxonomy/capabilities name, explicit
   `show path`, no-component failures, configured external work/inbox roots, and
   preservation of local, status-qualified, cross-project, and missing-item work
   path behavior. Run only the focused tests to establish the expected failures.
2. Add `path` to the taxonomy and capabilities command registries and parser
   trees, with handlers that print the opened filesystem adapter's resolved
   root. Run the focused taxonomy and capabilities tests.
3. Make the work path slug optional and branch only the no-slug case to print
   `FsWorkStore.root`; add the nested inbox path handler/parser using
   `FsWorkStore.inbox_root`. Keep qualified item resolution unchanged. Run the
   focused work CLI tests, including the external-store cases.
4. Run the full Python test suite and resolve any regressions without widening
   the abstract store interfaces.
5. Perform the Documentation Sync block after code and tests settle:
   - Update `README.md` for the public CLI surface and reserved `path` shorthand.
   - Update `docs/release-notes/upcoming.md` in user-facing language.
   - Update `docs/changelogs/upcoming.md` with technical command behavior.
   - Update `skills/tcw-taxonomy/SKILL.md`, `skills/tcw-capabilities/SKILL.md`,
     and `skills/tcw-work/SKILL.md` because each driven component's CLI surface
     changes.
   - Update `skills/tcw-work/references/commands.md` for the new work-root and
     inbox-root forms.
6. Reconcile the capability ledger: update `work/read-a-work-item` and
   `work/manage-the-work-inbox`, then mark
   `cli/locate-tcw-storage-folders` `Supported`. Run `tcw capabilities check`.
7. Run final verification: focused tests, full `pytest`, `tcw taxonomy check`,
   `tcw capabilities check`, `tcw validate`, and `git diff --check`. Record the
   implementation and evidence in `outcome.md`, commit it separately, and submit
   the item to review. Do not complete the item or cut a release.

## Verification

The automated suite covers output bytes, dispatch, resolution, configuration,
and failure paths. In addition, inspect the final diff to confirm no method was
added to `TaxonomyStore`, `CapabilitiesStore`, or `WorkStore`, and run the four
commands in this checkout to confirm their output remains composable as a bare
path.

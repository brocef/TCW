# Implement round 1

## What was done, step by step

0. **Spec and plan revised for the spec review** (`a0f86459`), before any
   code: the B10 for a clashing taxonomy folder names the project or
   projects that have it and offers one full identifier per reading (an
   inherited folder suggests `'lib.taxonomy/b/turn'`, never a term the
   project does not have); an end-to-end `tcw migrate` test for the
   inherited clash; the release note's exception (lines the project's own
   taxonomy holds are right), a `grep` users can run, and what `--remote`
   skips; Design 1 now says the term rule deliberately differs from the
   capability rule on a held path, and why; the plan names the fixture
   migration tests (f-single, f-full, monorepo) as the check on unchanged
   output, not `test_goldens_current.py`; the `Ambiguous3` assertion uses
   `kid/y` so it reaches the new code; the `kid/auth` source-and-child
   assertion is said not to tell the two rows apart, and a `kid/zed`
   assertion that does was added; a Risk for a parent that meant its own
   term; criterion 2 aligned with the test's `inbox` item.
1. **Step 1** (`83b20a8e`): `legacy.TermClash` and
   `legacy.route_term_entry_3x(path, *, children, own, sources, project_id)`,
   test `test_a_capabilities_yaml_term_entry_is_routed_child_first` in
   `tests/migrate/test_migrate_legacy.py`.
2. **Step 2** (`115e0b1f`): `Owners.owner_of` routes a `capabilities-yaml`
   row of the taxonomy namespace through it; the module docstring says so.
   Five tests in `tests/migrate/test_migrate_references.py`, section
   "a taxonomy: entry prefixed with a child (TCW-119)", with a `family`
   helper whose `A` configuration is an explicit argument (no default for
   the axis the routing branches on) and one assertion helper,
   `_assert_refused_unwritten`, for both B10 tests.
3. **Step 3** (`456bac3a`): the migration guide (step 3 Jira-mode paragraph,
   Jira order step 4, B10 bullet, a "Names and addresses" paragraph) and
   `test_step_3_says_jira_mode_needs_remote_for_records`.
4. **Step 4** (`01695655`): the capability description of
   `tcw.capabilities/cli/migrate-a-tcw-3-x-project-to-tcw-4`.
5. **Step 5** (`01695655`): documentation entries evaluated with the
   `documentation-sync` skill against `tcw work docs`: the changelog and
   release-notes entry files fire and were written
   (`docs/changelogs/upcoming/<folder>.md`, `## Fixed` and `## Changed`;
   `docs/release-notes/upcoming/<folder>.md`, `## Fixes`); README, the Jira
   guide, the other guides (the linking guide already says plain validate
   skips declared records in Jira mode, and no guide describes the
   routing), skills, configure references and use-cases do not fire, as the
   plan's table says.

## Red, then green

| Test | Red (before the fix) | Green |
| --- | --- | --- |
| `test_a_capabilities_yaml_term_entry_is_routed_child_first` | `AttributeError: module 'tcw.migrate.legacy' has no attribute 'TermClash'` | passed after Step 1 |
| `test_a_taxonomy_entry_prefixed_with_a_child_names_the_child_s_term` | `AssertionError: assert 'a.taxonomy/b/' not in ...` (`- a.taxonomy/b/turn`, `- a.taxonomy/b/never`, `removed: - a.taxonomy/b/turn`): the defect | passed after Step 2 |
| `test_a_taxonomy_entry_whose_child_is_also_a_taxonomy_folder_is_b10` | `assert 0 == 3` (the run converted instead of refusing) | passed after Step 2 |
| `test_a_taxonomy_entry_whose_child_is_a_folder_of_an_inherited_taxonomy_is_b10` | `assert 0 == 3` | passed after Step 2 |
| `test_a_taxonomy_entry_the_parent_s_own_taxonomy_holds_keeps_3x_reading` | a guard, green before the fix as planned; mutation: deleting the held-path row of `route_term_entry_3x` makes it fail with `B10 ... b/turn: ambiguous` | passed |
| `test_a_capability_subject_prefixed_with_a_child_is_not_routed` | a guard, green before the fix as planned; mutation: routing every taxonomy row (`row.namespace == "taxonomy"`) through the new function makes it fail with `['b.taxonomy/turn'] == ['a.taxonomy/b/turn']` | passed |
| `test_step_3_says_jira_mode_needs_remote_for_records` | `AssertionError: assert ('tcw validate --remote' in '...` (step 3's body); re-confirmed red with the guide stashed after the test was changed | passed after Step 3 |

## Test results, run just now

- `tests/migrate/test_migrate_f_single.py tests/migrate/test_migrate_f_full.py tests/migrate/test_migrate_monorepo.py`: `46 passed in 137.19s`, unmodified.
- `tests/migrate/`: `386 passed in 186.11s`.
- The full suite, bare `.venv/bin/pytest` from the worktree root:
  `8278 passed, 115 skipped in 1044.45s (0:17:24)`.
- `.venv/bin/tcw validate` in this repository: `0 errors, 0 warnings, 0 unresolved`.

## The Reproduction against the changed code

The spec's Reproduction, built by script in a scratch folder (item
`2026-10-01-a` at `implement`, as the spec has it), with this checkout's
`tcw`:

```text
$ tcw migrate            # in A
write docs/work/2026-10-01-a/capabilities.yaml: C16
write docs/work/2026-10-02-b/capabilities.yaml: C16
changed: 6 files written, 0 moved, 3 deleted; 0 tickets edited     (exit 0)
$ cat docs/work/2026-10-01-a/capabilities.yaml docs/work/2026-10-02-b/capabilities.yaml
changed:
- b.capabilities/cli/x
taxonomy:
  changed:
  - b.taxonomy/turn
  new:
  - b.taxonomy/never
taxonomy:
  removed:
  - b.taxonomy/turn
$ tcw -C ../B migrate    # exit 0
$ tcw validate           # in A, exit 0
0 errors, 3 warnings, 0 unresolved
(the three warnings: the hand-made item at implement has nothing from request, spec, plan)
```

The same family with a term at `A/docs/taxonomy/b/other`: `tcw migrate`
exits 3, `A` keeps its root `tcw-config.yaml` and has no `.tcw/`, the item's
file is unchanged, and it prints:

```text
refused:
  B10 docs/work/2026-10-01-a/capabilities.yaml: b/turn: ambiguous — 'b' is both a child project of this project and a namespace in this project's taxonomy; write it as 'b.taxonomy/turn' or 'a.taxonomy/b/turn', then run 'tcw migrate' again
  B10 docs/work/2026-10-01-a/capabilities.yaml: b/never: ambiguous — ...; write it as 'b.taxonomy/never' or 'a.taxonomy/b/never', then run 'tcw migrate' again
  B10 docs/work/2026-10-02-b/capabilities.yaml: b/turn: ambiguous — ...
```

## What the plan or spec got wrong

- **The held-path test's fixture** (plan Step 2.1, criterion 3): it put a
  term at `A/docs/taxonomy/b/turn` but kept the Reproduction's item, whose
  `b/never` beside it is not held while `b` is now a folder of `A`'s
  taxonomy, so the new code (rightly) refused that entry with B10 and the
  test failed. The test now gives that item only the held entry; the rule
  is unchanged.
- **The "Names and addresses" row** (spec Design 3, plan Step 3): a row
  failed `test_the_names_search_finds_every_3x_file_name_and_name_form`,
  because each first cell of that table feeds the guide's names search,
  which finds only names 4.0 no longer uses, and `capabilities.yaml` is
  still a 4.0 name. The same content is a paragraph under the table; the
  spec and plan were corrected to say so (`456bac3a`).
- **Step 1's first red line**: the plan predicted
  `no attribute 'route_term_entry_3x'`; it was `no attribute 'TermClash'`,
  because the revised test references `legacy.TermClash` first. Same cause.

## Records changed

- `tcw.capabilities/cli/migrate-a-tcw-3-x-project-to-tcw-4`: description
  only, as `capabilities.yaml` in this folder declares (`changed:`). No
  term changes.

## Rejections answered

None: this is the first implement round, and no review or qa round exists.

---
verdict: accepted
judges: 1
---
# Review round 1 (TCW-119)

**Verdict: accepted.** This round judges implement round 1
(`implement/round-1.md`) together with the code review's wording fixes in
`aaee270f`, on branch `v4.0.1` at `09e1727b`, which also holds TCW-120.

## Who reviewed

A separate read-only reviewer agent (the `tcw:reviewer` type), which did not
write the code, read the change against the spec, plan and
`capabilities.yaml`, ran the targeted tests and `tcw validate`, and
recommended `accepted`. This session ran the full suite and the
documentation evaluation and wrote this round. It did not write the code
either.

Earlier reviews this round relies on: the adversarial code review of the
change returned DONE with wording findings only, all fixed in `aaee270f`
(the release note's scope and its search command, the guide's note on what
`--remote` skips, the capability description's owner cases, and the error
message's list of three or more sources). A combined review of TCW-119 and
TCW-120 together found no interaction defect: neither change reaches the
other's code paths. The one point of contact is that, in a copy made of
worktrees, an `extends` source that TCW-119's routing consults can now be
found once in the copy instead of being refused as found twice, which moves
the answer toward the one the main checkout already gives.

## The suite, run as CI runs it

One run serves both TCW-119 and TCW-120, since they ship together on this
branch. A fresh clone of the worktree's branch, checked out at `v4.0.1`, was
run with `bash ~/.tcw-4.0-release/ci-suite.sh` (bare `pytest` in a new
virtual environment with a scratch home folder and no `TCW_` variables, then
the web build):

- HEAD line: `== Tue Nov  3 18:33:38 UTC 2026 in .../scratchpad/c401b, HEAD 09e1727b00119683ca6c76565ff231379084103e`
- Summary line: `================ 8297 passed, 115 skipped in 1317.17s (0:21:57) ================`
- Then `== suite and web build passed`, exit 0.

`tcw validate` in this repository: `0 errors, 0 warnings, 0 unresolved`.

## Acceptance criteria

1. **The reported case: met.**
   `tests/migrate/test_migrate_references.py::test_a_taxonomy_entry_prefixed_with_a_child_names_the_child_s_term`
   checks exit 0, the `write docs/work/2026-10-01-a/capabilities.yaml: C16`
   line, and that both item files parse to exactly the mappings the
   criterion gives. The code is the `capabilities-yaml` branch in
   `Owners.owner_of` (`tcw/migrate/references.py`), which calls
   `route_term_entry_3x` (`tcw/migrate/legacy.py`).
2. **Validate is clean for these lines: met.** The same test then migrates
   `B`, runs `tcw validate` in `A`, and asserts exit 0 and that no output
   line names `capabilities.yaml`.
3. **The project's own taxonomy holds the path: met.**
   `test_a_taxonomy_entry_the_parent_s_own_taxonomy_holds_keeps_3x_reading`
   asserts `["a.taxonomy/b/turn"]`.
4. **The ambiguous case: met.**
   `test_a_taxonomy_entry_whose_child_is_also_a_taxonomy_folder_is_b10`
   (own taxonomy) and
   `test_a_taxonomy_entry_whose_child_is_a_folder_of_an_inherited_taxonomy_is_b10`
   (the `lib` source) each check exit 3, the exact B10 line, and through
   `_assert_refused_unwritten` that nothing was written.
5. **Unchanged readings: met.** `test_each_entry_of_an_items_capabilities_file`
   and `test_a_capabilities_yaml_entry_is_routed_as_3_x_routed_it` pass, and
   `git diff main...HEAD` on both test files shows additions only, so neither
   was modified.
6. **Other fields are not routed to a child: met.**
   `test_a_capability_subject_prefixed_with_a_child_is_not_routed` asserts
   `Subject == ["a.taxonomy/b/turn"]`; the new branch fires only for rows of
   the `capabilities-yaml` record.
7. **The function's table: met.**
   `tests/migrate/test_migrate_legacy.py::test_a_capabilities_yaml_term_entry_is_routed_child_first`
   covers every row of Design 1's table, including the clash with own,
   inherited and several sources, and the reviewer read the function's row
   order against the spec.
8. **The guide: met.** `docs/migration-guide-3.X-to-4.0.0.md` holds the three
   additions of Design 3; `tests/test_migration_guide_4_0.py` (including
   `test_step_3_says_jira_mode_needs_remote_for_records`) and
   `tests/test_migration_guide.py` pass.
9. **The capability record: met.**
   `docs/capabilities/cli/migrate-a-tcw-3-x-project-to-tcw-4/description.md`
   says a reference prefixed with a child project's ID is written as that
   child's full identifier, in the taxonomy lists as in the capability lists.
10. **The suite and `tcw validate`: met.** See above.

## Capability records

`capabilities.yaml` lists one path under `changed:`,
`tcw.capabilities/cli/migrate-a-tcw-3-x-project-to-tcw-4`. The record is
present and its changed description matches the code (`bare_owner_3x` for
own and inherited owners, `route_entry_3x` for capability entries,
`route_term_entry_3x` for term entries). It does not name the B10 refusal;
that is a level of detail, not a claim the code fails to back.

## Documentation entries (`documentation-sync`)

The `documentation-sync` skill was run over the whole branch difference
(`main...HEAD`). For this item:

| Entry | Fires? | Answered by |
| --- | --- | --- |
| `docs/changelogs/upcoming/<folder>.md` [Any-Code-Change] | yes | the item's file, `01695655` |
| `docs/release-notes/upcoming/<folder>.md` [Public-API] | yes | the item's file, `01695655`, scope and search command corrected in `aaee270f` |
| `docs/guide/<topic>.md` [Guide-Topic-Change] | yes, for the migration guide (not under `docs/guide/`, but the guide this topic belongs to) | `docs/migration-guide-3.X-to-4.0.0.md`, `456bac3a` and `aaee270f`. No guide under `docs/guide/` describes the migration's routing; `docs/guide/linking-and-validation.md` already says plain validate skips declared records in Jira mode. |
| `docs/guide/jira.md` [Jira-Change] | no | no ticket, `work.jira` key or status behavior changes |
| `README.md` [Public-API] | no | it does not describe how `tcw migrate` converts references |
| `skills/<component>/SKILL.md` [Skill-Driven-Component] | no | no CLI surface, field or lifecycle change; no skill describes the migration's routing |
| `skills/configure/references/<document>.md` [Configuration-Key-Change] | no | no configuration key changes |
| `docs/use-cases.md` [Project-Setup-Change] | no | the fix makes the migration do what the existing setups already expect; it adds no setup and closes no recorded gap |

Capability record: `docs/capabilities/cli/migrate-a-tcw-3-x-project-to-tcw-4/description.md`, `01695655` and `aaee270f`.

## Notes, not defects

- A taxonomy term whose whole path is just the child's ID (a term `b` with
  no `/`) counts as a folder `b` and so also leads to B10. That agrees with
  the spec's "first folder" wording, and is untested.
- Not confirmed by this review: the implement round's red-before-fix results
  and mutation checks, which it reports itself.
- The originating report is not a GitHub issue, so nothing waits on
  publication for this item beyond the 4.1.0 release itself.

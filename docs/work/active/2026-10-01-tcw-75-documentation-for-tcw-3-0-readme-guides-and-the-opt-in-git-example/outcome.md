# Outcome — Documentation for TCW 3.0: README, guides and the opt-in git example

Implemented on `work/2026-10-01-tcw-75-documentation-for-tcw-3-0-readme-guides-and-the-opt-in-git-example`,
branched from `epic/tcw-3.0` at `5b0dcf95`, in 17 commits (`38595b1c` to
`8e54c026`): one per plan task 1 to 16, plus one fold-in. Two implementation
agents ran in sequence (Tasks 1-7, then 8-17), with a private virtual
environment running the worktree's code. Nothing was pushed, no version was
cut, and Jira was not touched.

## Plan review

Before implementation, one adversarial review of the plan returned NOT DONE
with two must-fix findings (a link Task 2 would add before Task 7 wrote its
target; the `AGENTS.md` section would have been scanned as the whole file)
and eight smaller ones. All were checked against the branch and accepted; they
are the "Amendments after the plan review" section at the end of `plan.md`.

## Commits

| Commit | Task |
| --- | --- |
| `38595b1c` | 1: scans for owned documents (vocabulary, links and anchors, allowance names), with a built-in mutation case |
| `edadc756` | 2: configure skill rewritten (router, `work.md`, `projects.md`, new `jira.md` and `personal.md`, `stores.md`, `docs-sync.md`; `tracker.md` deleted); criteria 6 and 7 tests |
| `95823868` | 3: TCW-74's shipped-text scans read `skills/configure/`; `_names`/`_flag_named` take text |
| `36da5873` | 4: `abstraction.md`, `implementation.md`, `harness.md`; criterion 9 tests |
| `f83a352a` | 5: `AGENTS.md` worktree section |
| `09238785` | 6: `docs/guide/examples/commit-item-after-move.sh` and its four repository cases |
| `e76a3e54` | 7: `docs/guide/configuration.md` with the git example |
| `38e598e7` | fold-in: `tests/test_check_versions.py` skill count 17 → 14 (TCW-74 deleted three skills; the test already failed on the epic branch) |
| `40684b5b` | 8: `docs/guide/cli.md` and `tests/test_cli_guide.py` |
| `df7a435f` | 9: `docs/guide/work.md`; `WORK_GUIDE_VERBS` check |
| `1e902ae5` | 10: `docs/guide/jira.md` |
| `2f4fc8f1` | 11: `docs/guide/multi-repo.md` |
| `0a92c4e0` | 12: `taxonomy-and-capabilities.md`, `linking-and-validation.md` |
| `40c288e8` | 13: README; `docs/work-inbox-template.md` deleted |
| `9da93bee` | 14: allowance shrunk; every remaining entry must still be named somewhere |
| `0d3a6d90` | 15: `OWNED` set derived and pinned (19 documents); criterion 10 checks |
| `8e54c026` | 16: release-notes and changelog entries; upcoming-entry exemption |

## Evidence per criterion

1. **README structure:** five tests in `tests/test_docs_describe_3_0.py`;
   mutation 9 (heading after Overview renamed) fails it.
2. **No 2.x vocabulary:** the scan over all 19 owned documents, plus a pytest
   case that copies a real owned document and inserts `tcw work start`;
   mutation 1 fails it.
3. **Links resolve:** link and anchor check over the owned set; mutation 2
   (missing file, missing heading) fails it.
4. **No phantom commands, allowance not named:** `test_documented_cli_surface.py`,
   the allowance-name check, and the new "every entry still named" check in
   `test_doc_allowance.py`; mutations 3 (`tcw work init` inserted) and 4 (an
   entry nobody names) fail them.
5. **Git example works:** `tests/test_git_example.py` (four repository
   cases, the guide's `sh` block equals the script byte for byte, the
   guide's configuration loads and resolves each prompted stage to the pull
   blob then the built-in prompt, no `pre`); mutation 6 fails each part.
   By hand, in a scratch fixture with the guide's configuration:
   `tcw work stage prompt spec 2026-10-15-add-login` printed the pull text
   before `# Stage: spec`; `tcw work advance 2026-10-15-add-login` printed
   `spec`, exit 0, and made one commit, "Move demo/2026-10-15-add-login to
   spec", changing only that item's `item.yaml`; `git status` clean.
6. **Configure skill consistent** and 7. **override table matches the code:**
   `tests/test_configuration_text_home.py` (57 key paths, one heading and
   label each, table equals `PERSONAL_KEYS`, every `work.*` path loads);
   mutation 5 fails each.
8. **Exit-code table:** `tests/test_cli_guide.py`; mutation 7 fails it.
9. **Lifecycle documents:** criterion 9 tests; mutation 8 fails them.
10. **Inventory:** inbox template and `tracker.md` gone; `cli.md`, the
    script and `personal.md` present (tests); outlines checked by review.
11. **Release notes:** two tests in `tests/test_upcoming_entries.py` (the
    introduction links the migration guide; `combine()` puts it first);
    mutation 10 fails them.
12. **Full suite:** deferred to the end of the epic by the owner's rule.

Collection is clean (4773 tests). Every touched test file plus the standing
guard files: 1077 passed, 5 skipped (parametrized tests over the three
allowance lists that are now empty).

## Mutation checks (Task 17)

Each break was made in the working tree, one test run, then restored:

1. `tcw work start` in `work.md` → vocabulary scan fails.
2. Link to `nowhere.md`, then to `cli.md#no-such-heading` → "broken links", each.
3. `tcw work init` in `jira.md` → "names entries of tests/doc_allowance.py: ['tcw work init']".
4. Unnamed entry added → "no live document names tcw work start".
5. `post` label set to `Shared:` → label mismatch; a `personal.md` row removed → "missing rows"; `work.backend` added to `PERSONAL_KEYS` → table test fails.
6. `-- .` removed → the staged file is committed too; `- inherit: true` removed → prompt check fails; one byte changed in the guide's `sh` block → identity check fails.
7. Extra exit-table row → fails.
8. A backend-interface bullet removed → fails.
9. Heading after Overview renamed → fails.
10. Introduction moved under a `##` → "has no text before its first heading"; leading text added to another entry → that entry's test and the cut-order test fail.
11. `skills/configure/` filtered out of `_shipped_text` → walk test fails.

## Hand checks against the code (fixtures, never this repository)

- `cli.md`: exit codes 2, 3, 4, 5; an unmatched short name exits 4; `list --json` carries `schema: 1`.
- `work.md`: advance, `--dry-run`, a refused skip, a forced move with a reason, the records-gate refusal, discard and reopen, rename, tag any-of.
- `jira.md`: an unreachable site; network commands exit 5, offline ones 0; `new --stage inbox` exits 2.
- `multi-repo.md`: delegation prints the slug and leaves files uncommitted; a second delegation is refused (3) while the store has uncommitted changes; `projects list`.
- Taxonomy and linking guides: `add` from stdin, `--parent`/`--slug`, `drift` exits 0 when clean, `validate` on list-shaped `meta.yaml`/`item.yaml`.
- README: `new` from stdin prints `demo/<date>-export-invoices-as-pdf`; `advance --dry-run` prints `spec`; `config show --origin`, `capabilities list --local`, `taxonomy list --local` exist.
- Records (plan amendment 8): the branch's `tcw validate` on copies of `docs/taxonomy` and `docs/capabilities` reports exactly 13 errors, all "field 'Planning doc' was retired in TCW 3.0", which TCW-76 removes; with those lines removed, 0 errors.
- Note 3 (plan amendment 9): `grep -nE 'consolidate-plans|decompose|delegation|post-mortem' docs/guide/configuration.md` prints nothing.

## Deviations from the plan

- `tcw config show --origin` prints `- builtin: true  # built-in, tcw/work/prompts/<stage>.md`; the spec's shorter form was wrong. The guide, `personal.md` and the allowance follow the code.
- Seven configure files, not six (the router plus six references).
- `jira.md` links `projects.md#creating-an-item-in-another-project`, since the vocabulary scan rejects "connected-projects".
- The release-note links use `../`, the path from `docs/release-notes/v3.0.0.md` after the cut; they do not resolve while the entry sits in `upcoming/`.
- The README's Jira example shows `tcw work show SHOP-42` rather than a forced completion.
- A `GIT_ALLOWED` entry for the anchor of the git example's heading, linked from `stores.md`.

## 2.x tests

Two tests in `tests/test_configuration_text_home.py` (tracker inheritance
sentences; the router's tracker row) were replaced by the criteria 6 and 7
tests, not ported. No other test was deleted or skipped.

## Allowance entries left, and their owners (all TCW-76)

- `tcw work stage gate`: `AGENTS.md` (`CLAUDE.md` links to it), outside the worktree section.
- `tcw work init`: `docs/capabilities/work/configure-the-work-store-location/description.md`.
- `tcw taxonomy check`, `tcw capabilities check`: `docs/capabilities/cli/validate-a-project/description.md`.
- `work.lifecycle`, `work.tracker`, `work.retain`, `work.auto-commit-transitions`, `work.publish-transitions`, `work.trunk-branch`: `docs/capabilities/work/configure-the-work-lifecycle/description.md`.

`REMOVED_FLAGS`, `REMOVED_FORMS` and `REFUSED_VALUES` are empty.

## Notes for other items

- Note 6 (`Planning doc` on 13 records, `skills/configure` among them) is
  TCW-76's (its spec Design 3.7).
- The rest of `AGENTS.md` is TCW-76's, as is `PENDING_TARGETS` in
  `tests/test_docs_describe_3_0.py`.
- Outside this item's files: `skills/README.md:85` still says "TCW-75
  rewrites this skill", and `tcw/store/base.py:5-6`'s docstring says remote
  adapters are "possible but unbuilt".

## Review

Recorded below once the review rounds finish.

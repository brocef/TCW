# Plan — tcw migrate reads a capabilities.yaml taxonomy entry prefixed with a child project's ID as a path in the item's own taxonomy

The spec is `spec/spec.md` beside this folder; "Design n" and "criterion n"
are its sections and acceptance criteria. Every file and line cited was
checked on `main` at `07c31ddb` (2026-11-03). The item folder is
`docs/work/TCW-119-tcw-migrate-reads-a-capabilities-yaml-taxonomy-entry-prefixed-with-a-child-project-s-id-as-a-path-in-the`,
called `<folder>` below.

The change is small and in one place (`tcw/migrate/legacy.py`,
`tcw/migrate/references.py`), so it is one item, not split. It has no
blockers. Each step writes its tests first, sees them fail for the reason
named, then makes them pass; the whole suite passes at the end of every step.

**Tests are run** from the repository root, bare `pytest` as CI runs it. In a
git worktree, use the worktree's own virtual environment (`python -m venv
.venv && .venv/bin/pip install -e '.[dev]'`, then `.venv/bin/pytest`), since
the shared editable install imports the primary checkout's code (CLAUDE.md,
"Working in a git worktree").

## Step 1 — `route_term_entry_3x`, the rule as a function (criteria 4, 7)

**Files:** `tests/migrate/test_migrate_legacy.py` (test added),
`tcw/migrate/legacy.py` (function added).

1. **Test first.** Add
   `test_a_capabilities_yaml_term_entry_is_routed_child_first` after
   `test_a_capabilities_yaml_entry_is_routed_as_3x_routed_it`
   (`tests/migrate/test_migrate_legacy.py:340`), in the same style (a local
   `route(path, **kw)` with defaults `children=["kid"]`, `own=set()`,
   `sources={}`, `project_id="app"`). One assertion per row of Design 1's
   table, in order:
    - `route("invoice") == (None, "invoice")` (no `/`);
    - `route("cli/x") == (None, "cli/x")` (first part not a child);
    - `route("core/auth", sources={"core": {"auth"}}) == ("core", "auth")`
      (a source, not a child: the first row already sends it to
      `bare_owner_3x`). `route("kid/auth", sources={"kid": {"auth"}}) ==
      ("kid", "auth")` is asserted too, but it cannot tell the source row
      from the child row, since both give `("kid", "auth")`, so it is not
      counted as coverage of the source row. The source row is told apart
      by `route("kid/zed", sources={"kid": {"auth"}, "lib": {"kid/x"}}) ==
      ("kid", "zed")`: without the source row, `lib`'s folder `kid` would
      make it a clash;
    - `route("kid/turn", own={"kid/turn"}) == (None, "kid/turn")` and
      `route("kid/turn", sources={"lib": {"kid/turn"}}) == ("lib", "kid/turn")`
      (the whole path is held);
    - `route("kid/turn", own={"kid/other"})` equals
      `legacy.TermClash("kid/turn: ambiguous — 'kid' is both a child project of this project and a namespace in this project's taxonomy", "write it as 'kid.taxonomy/turn' or 'app.taxonomy/kid/turn', then run 'tcw migrate' again")`;
      `route("kid/turn", sources={"lib": {"kid/other"}})` equals
      `legacy.TermClash("kid/turn: ambiguous — 'kid' is both a child project of this project and a namespace in the taxonomy it inherits from 'lib'", "write it as 'kid.taxonomy/turn' or 'lib.taxonomy/kid/turn', then run 'tcw migrate' again")`;
      and `route("kid/turn", own={"kid/o"}, sources={"lib": {"kid/o"}, "core": {"kid/p"}})`
      has a `why` ending `a namespace in this project's taxonomy and the taxonomies it inherits from 'lib' and 'core'`
      and the `fix` `write it as 'kid.taxonomy/turn', 'app.taxonomy/kid/turn', 'lib.taxonomy/kid/turn' or 'core.taxonomy/kid/turn', then run 'tcw migrate' again`
      (criterion 4: own, inherited, and both);
    - `route("kid/turn") == ("kid", "turn")` and
      `route("kid/a/b", own={"invoice"}) == ("kid", "a/b")` (the child);
    - `route("kid") == (None, "kid")` (the child's ID alone, no `/`: as
      today);
    - `pytest.raises(legacy.Ambiguous3)` for
      `route("kid/y", sources={"a": {"kid/y"}, "b": {"kid/y"}})` (3.x's own
      ambiguity still raised, on the held-path row: `kid` is a child, so the
      call reaches the new code rather than leaving by the first row).

   Run it: it fails with `AttributeError: module 'tcw.migrate.legacy' has no
   attribute 'route_term_entry_3x'`.

2. **Code.** Add to `tcw/migrate/legacy.py`, after `route_entry_3x`
   (`legacy.py:958-983`):

    ```python
    @dataclass(frozen=True)
    class TermClash:
        why: str
        fix: str

    def route_term_entry_3x(path: str, *, children: list[str], own: set[str],
                            sources: dict[str, set[str]], project_id: str
                            ) -> tuple[str | None, str] | TermClash:
    ```

   with a docstring saying it is TCW-119 Design 1: what 3.x read (`get`,
   `bare_owner_3x`) wherever 3.x's reading names a source or finds the path,
   the listed child otherwise, and the ambiguity `route_entry_3x` refuses
   when the child's ID is also a first folder of the resolved taxonomy. Body,
   in the table's order: `head, _, rest = path.partition("/")`; if `not rest`
   or `head not in children` or `head in sources`, return
   `bare_owner_3x(path, own, sources)`; if `path in own` or any source's set
   holds `path`, return `bare_owner_3x(path, own, sources)`; if `head` is
   `p.split("/", 1)[0]` for any `p` in `own` or any source's set, return a
   `TermClash` worded as spec Design 1 says, from which of them have the
   folder (the project's own first, then each source in `sources`' order);
   else return `(head, rest)`.

   Run the new test and `tests/migrate/test_migrate_legacy.py`: green. Nothing
   calls the function yet, so no other test can change.

**Done when** the new test passes and the full suite passes.

## Step 2 — `Owners.owner_of` uses it for `taxonomy:` entries (criteria 1-6)

**Files:** `tests/migrate/test_migrate_references.py` (five tests added),
`tcw/migrate/references.py` (one branch and two docstrings).

1. **Tests first**, in a new section `# ── a taxonomy: entry prefixed with a
   child (TCW-119) ──` after `test_a_capabilities_yaml_entry_is_routed_as_3_x_routed_it`.
   A helper `family(tmp_path, a_extra, a_config=None)` (`a_config`, when
   given, replaces `A`'s configuration) builds the spec's Reproduction with
   the file's `make`: `A` with the 3.x config of Reproduction step 2, the two
   items of steps 3 and 4 (item `2026-10-01-a` at `stage: inbox`, so `tcw
   validate` gives no stage-ahead warning; `2026-10-02-b` at `stage:
   completed`), and `a_extra` merged into `A`'s files; `B` as in step 5.
    - `test_a_taxonomy_entry_prefixed_with_a_child_names_the_child_s_term`
      (criteria 1 and 2): `family(tmp_path, {})`; `tcw(["migrate"], A)`
      exits 0 and `"write docs/work/2026-10-01-a/capabilities.yaml: C16"` is
      a line of its standard error; the two files parse to exactly the
      mappings criterion 1 gives; then `tcw(["migrate"], B)` exits 0;
      then `tcw(["validate"], A)` exits 0 and no line of its output
      contains `capabilities.yaml`. Fails today on the first `==`, with
      `a.taxonomy/b/turn`.
    - `test_a_taxonomy_entry_the_parent_s_own_taxonomy_holds_keeps_3x_reading`
      (criterion 3): `family(tmp_path, {"docs/taxonomy/b/turn/meta.yaml":
      "name: Turn\nkind: Vocabulary\n", "docs/taxonomy/b/turn/description.md":
      "A turn.\n"})`; after `tcw(["migrate"], A)` the first item's
      `taxonomy.changed` is `["a.taxonomy/b/turn"]`. Passes today too; it
      guards Design 1's third row against the new code.
    - `test_a_taxonomy_entry_whose_child_is_also_a_taxonomy_folder_is_b10`
      (criterion 4): `family(tmp_path, {"docs/taxonomy/b/other/meta.yaml":
      …, "docs/taxonomy/b/other/description.md": …})`; `tcw(["migrate"], A)`
      exits 3; its standard error contains, word for word,
      `B10 docs/work/2026-10-01-a/capabilities.yaml: b/turn: ambiguous — 'b' is both a child project of this project and a namespace in this project's taxonomy; write it as 'b.taxonomy/turn' or 'a.taxonomy/b/turn', then run 'tcw migrate' again`;
      `A/tcw-config.yaml` still exists, `A/.tcw` does not, and the item's
      `capabilities.yaml` is byte-for-byte what was written. Fails today
      (exit 0).
    - `test_a_taxonomy_entry_whose_child_is_a_folder_of_an_inherited_taxonomy_is_b10`
      (criterion 4, inherited): a 3.x project `lib` beside `A` (`id: lib`,
      a term at `docs/taxonomy/b/other`); `A`'s configuration adds
      `upstream: {lib: ../lib}` and `taxonomy: {extends: [lib]}`, and `A`
      keeps no taxonomy of its own. `tcw(["migrate"], A)` exits 3; its
      standard error contains, word for word,
      `B10 docs/work/2026-10-01-a/capabilities.yaml: b/turn: ambiguous — 'b' is both a child project of this project and a namespace in the taxonomy it inherits from 'lib'; write it as 'b.taxonomy/turn' or 'lib.taxonomy/b/turn', then run 'tcw migrate' again`;
      and nothing is written, as above. Fails today (exit 0).
    - `test_a_capability_subject_prefixed_with_a_child_is_not_routed`
      (criterion 6): `family(tmp_path, {"docs/capabilities/cli/y/meta.yaml":
      "name: Y\nStatus: Supported\nSubject: [b/turn]\n",
      "docs/capabilities/cli/y/description.md": "Y.\n"})`; after
      `tcw(["migrate"], A)`, `Subject` of
      `docs/capabilities/cli/y/tcw-capability.yaml` is
      `["a.taxonomy/b/turn"]`. Passes today; it pins the narrowed sweep.

2. **Code.** In `Owners.owner_of` (`tcw/migrate/references.py:118-136`),
   add a branch between the capability branch and the `else`:

    ```python
    elif row.record == "capabilities-yaml":
        routed = route_term_entry_3x(value, children=self.view.children,
                                     own=own, sources=sources,
                                     project_id=self.project)
        if isinstance(routed, TermClash):
            self.blockers.append(Blocker("B10", where, routed.why, routed.fix))
            return None
        owner, path = routed
    ```

   import `TermClash` and `route_term_entry_3x` beside `route_entry_3x`
   (`references.py:27`), and change the module docstring's sentence "and one
   under `taxonomy:` read as a term is" (`references.py:11`) to say that an
   entry under `taxonomy:` prefixed with a listed child's ID names the
   child's term unless 3.x's reading names a source or finds it, and is B10
   when the child's ID is also a folder of the taxonomy
   (`legacy.route_term_entry_3x`).

3. Run `tests/migrate/`: the five tests and every existing one pass,
   `test_each_entry_of_an_items_capabilities_file` and
   `test_a_capabilities_yaml_entry_is_routed_as_3_x_routed_it` unmodified
   (criterion 5). Then run by name the tests that migrate the recorded
   fixtures and compare what the migration writes:
   `tests/migrate/test_migrate_f_single.py`,
   `tests/migrate/test_migrate_f_full.py` and
   `tests/migrate/test_migrate_monorepo.py` (the monorepo is the fixture with
   children). They must pass unmodified; if one fails, stop and say which,
   since a fixture with a child-prefixed term entry would be a case the spec
   did not foresee. (`tests/migrate/test_goldens_current.py` is not that
   check: it compares each fixture's digest with its recorded golden and
   never runs the migration.)

**Done when** the full suite passes.

## Step 3 — the migration guide (criterion 8)

**Files:** `tests/test_migration_guide_4_0.py` (one test added),
`docs/migration-guide-3.X-to-4.0.0.md`.

1. **Test first.** Add `test_step_3_says_jira_mode_needs_remote_for_records`:
   the body of `### 3. Run it: \`tcw migrate\`` (with the file's `section`
   helper, level 3) contains `tcw validate --remote` and `capabilities.yaml`;
   and the body of `### Jira: \`--no-jira\`, and converting the tickets last`
   contains `tcw validate --remote`. Fails today.
2. **Guide**, Design 3, in plain words:
    - after the paragraph that begins "Then run `tcw validate`"
      (`docs/migration-guide-3.X-to-4.0.0.md:343`), a paragraph: in a
      project whose work is kept in Jira, `tcw validate` without `--remote`,
      and the check `tcw migrate` runs after a real run, do not check the
      records each item's `capabilities.yaml` declares, since the item's
      stage is kept in Jira; once the tickets are converted, run `tcw
      validate --remote`, which checks them for every item not yet
      `completed` or `discarded`; an entry naming a term or capability not
      made yet is reported when the item moves past implementation, not
      before; link [Linking and validation](guide/linking-and-validation.md);
    - the Jira order (`:446-449`) gains a step 4: "`tcw validate --remote`,
      which also checks what items' `capabilities.yaml` files declare";
    - the B10 bullet (`:246-248`) adds: or a `taxonomy:` entry that starts
      with a listed child's ID that is also a folder of the project's
      taxonomy, which could mean either; write it as a full identifier;
    - the "Names and addresses" section gains a paragraph under its table
      (corrected at implement: a row failed
      `test_the_names_search_finds_every_3x_file_name_and_name_form`, since
      each first cell feeds the names search and `capabilities.yaml` is still
      a 4.0 name), carrying what was planned as a row: first cell
      `` `<child>/<path>` in an item's `capabilities.yaml` ``, second cell
      `` `<child>.capabilities/<path>`, and under `taxonomy:`
      `<child>.taxonomy/<path>`, for a child the project lists ``, followed
      in the same cell by: unless, under `taxonomy:`, the project's own or
      inherited taxonomy has a term at that whole path, which keeps it; and
      one sentence saying this differs from a capability entry on purpose,
      since each half does what 3.x did and 3.x read every term entry in the
      project's own taxonomy.
3. Run `tests/test_migration_guide_4_0.py` and `tests/test_migration_guide.py`:
   green (the new row's first cell starts with a 3.x form and its second cell
   is not empty, as `test_every_row_says_what_replaces_it` needs; the scan
   tests read only 3.x names and commands).

**Done when** the full suite passes.

## Step 4 — the capability record (criterion 9)

**Files:** `docs/capabilities/cli/migrate-a-tcw-3-x-project-to-tcw-4/description.md`.

Change the sentence "every reference the project's files make to its own
objects is written as a full identifier" to say every reference the project's
files make is written as a full identifier, naming the project that owns the
object: the project itself, one it inherits from when the reference is
prefixed with that project's ID, and, in an item's `capabilities.yaml`, a
child project the entry is prefixed with, in the taxonomy lists as in the
capability lists. Its `tcw-capability.yaml` is unchanged.

**Done when** `tcw validate` in this repository passes and the item's
declared change (`changed:` this capability, `<folder>/capabilities.yaml`)
is the capability whose description changed.

## Step 5 — Documentation Sync

Invoke the `documentation-sync` skill and evaluate each entry `tcw work docs`
lists:

| Entry | Fires? | Action |
| --- | --- | --- |
| `docs/changelogs/upcoming/<folder>.md` [Any-Code-Change] | yes | Create `docs/changelogs/upcoming/TCW-119-tcw-migrate-reads-a-capabilities-yaml-taxonomy-entry-prefixed-with-a-child-project-s-id-as-a-path-in-the.md` with `## Fixed`: `tcw migrate` (C16) converts an item's `capabilities.yaml` `taxonomy:` entry prefixed with a listed child's ID to `<child>.taxonomy/<rest>` (`legacy.route_term_entry_3x`), as `route_entry_3x` did for capability entries; B10 when the child's ID is also a first folder of the resolved taxonomy. `## Changed`: the 3.x to 4.0 migration guide says plain `tcw validate` in Jira mode does not check declared records. No `#` title. |
| `docs/release-notes/upcoming/<folder>.md` [Public-API] | yes | Create `docs/release-notes/upcoming/<folder>.md` (same file name) under `## Fixes`: migrating a project that lists child projects now writes a child's term for a `taxonomy:` entry such as `b/turn` in an item's `capabilities.yaml`, as it already did for capability entries; a project migrated with 4.0.0 holds `<project>.taxonomy/<child>/<term>` there, and should change each such line by hand to `<child>.taxonomy/<term>`, unless the project's own taxonomy has a term at that path (those lines are correct, by the spec's own rule). To find them, a search the user can run: `grep -rn '<project>.taxonomy/<child-id>/' docs/work/*/capabilities.yaml` (or the item folders wherever the work store is). `tcw validate --remote` does not find them all: it skips `completed` and `discarded` items and items whose ticket is at a status no stage names; lines in finished items are history, worth fixing only for consistency. One clause: a migration left unfinished by 4.0.0 finishes with 4.0.0's conversion when resumed (its plan was made then), so fix those lines the same way. And a note that in a Jira-mode project `tcw validate --remote` is the check that reads these files. Plain language, no module names. |
| `docs/guide/<topic>.md` [Guide-Topic-Change] | no | The linking and validation guide already says plain validate skips declared records in Jira mode (`docs/guide/linking-and-validation.md:216-225`); no guide in `docs/guide/` describes the migration's routing of `capabilities.yaml` entries. The migration guide, which does, is changed in Step 3. |
| `docs/guide/jira.md` [Jira-Change] | no | No ticket, `work.jira` key or status behavior changes. |
| `README.md` [Public-API] | no | It does not describe how `tcw migrate` converts references. |
| `skills/<component>/SKILL.md` [Skill-Driven-Component] | no | No CLI surface, field or lifecycle changes; the skills do not describe C16's routing (checked: `grep -rn "capabilities.yaml" skills/` names no migration routing). |
| `skills/configure/references/<document>.md` [Configuration-Key-Change] | no | No configuration key changes. |
| `docs/use-cases.md` [Project-Setup-Change] | no | The fix makes the migration do what UC-3 and UC-4 expect; it adds no setup and finishes no recorded known gap. The unmapped-status skip (spec Notes) belongs to its own item, which would add its known gap. |

**Done when** both entry files exist, `python scripts/cut_version.py`'s
merge rules are met (headings `## Fixed`/`## Changed` and `## Fixes`, no
`## ` inside a code block), and the full suite passes.

## Verification

Beyond the tests:

1. **The full suite as CI runs it:** bare `pytest` from the repository root
   (in a worktree, `.venv/bin/pytest`), and `tcw validate` in this repository
   (criterion 10).
2. **The reproduction, by hand, against the changed code:** build the spec's
   Reproduction family in a scratch folder, run this checkout's `tcw migrate`
   in `A`, then in `B`, and `tcw validate` in `A`. Expected: the files read
   as criterion 1 says; validate gives no finding naming `capabilities.yaml`.
   Then repeat with `A` given a term at `b/other`, and confirm the exact B10
   line and that nothing was written. Record the output in the review round.
3. **What cannot be tested here:** the evaluator's Jira-mode family and its
   `tcw validate --remote` run. The Jira-mode behavior of the records check
   is unchanged by this item, and the converted files are the same in both
   modes (the conversion does not read the backend), so the files-mode tests
   stand for it. Which of the evaluator's three unreported lines were in
   finished items and which at an unmapped status stays an assumption (spec
   Problem, part 3).

## Self-review

- Criterion 1, 2 → Step 2 (first test); 3 → Step 2; 4 → Steps 1 and 2; 5 →
  Step 2.3; 6 → Step 2; 7 → Step 1; 8 → Step 3; 9 → Step 4; 10 →
  Verification 1. Every step names a criterion.
- One function name throughout, `route_term_entry_3x`; the B10 texts are the
  spec's Design 1, both halves (`why` and `fix`) built by the function as a
  `TermClash` (Step 1) and passed to `Blocker` unchanged (Step 2), the way
  `Blocker` prints `"{code} {where}: {why}; {fix}"`.
- `capabilities.yaml` exists and the QA plan comment is posted (spec stage).

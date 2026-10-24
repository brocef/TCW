# Implement round 1 — TCW-108

Built on the `v4` branch in the worktree `.claude/worktrees/v4`, with the code
under test run from its own virtual environment (`.venv/bin/pytest`,
`.venv/bin/tcw`). Hand runs of `.venv/bin/tcw` were made only in throwaway
projects in the scratchpad, with `HOME` and the XDG folders set there. The
records of Step 14 were written in their 3.x form and checked with the
released 3.x CLI on PATH. The lifecycle was not driven by any CLI: the
dispatching session makes every move. This is the first implement round, so
it answers no rejection. It gives no verdict.

## What was done, step by step

- **Step 0 — the starting point** (`35309a11`). TCW-106, TCW-107 and TCW-110
  are on `v4`. The spec records the two decisions the dispatching session
  made on 2026-10-23 (a manifest that disagrees with the search; the resolved
  folder in "not on this machine").
- **Step 1 — reading `parents:` and `children:`** (`3ddf1458`).
  `tcw/store/links.py` (`parse_parents`, `parse_children`) and `ParentLink`
  in `tcw/store/base.py`, not yet used.
- **Step 2 — the load order** (`8da16311`). `LoadOrder`, `load_order_of` (C3
  with the depth-first fallback and its warning), `find_loop`,
  `loop_message` and `passing`, in one store-neutral place.
  `tests/test_load_order.py`, with a property test against Python's own C3
  over graphs of up to eight projects.
- **Step 3 — exit code 7** (`5df81df0`). `INHERITED_UNAVAILABLE`,
  `InheritedUnavailable`, the `--help` text, `docs/guide/cli.md`, the
  output-contract capability and `skills/work/references/commands.md`, and
  the tests that pin the codes.
- **Step 4 — the reader's temporary translation of `projects:`**
  (`4b4056e4`), removed again in Step 8b.
- **Step 5 — the single-parent helpers go** (`cfd235d4`), keeping what their
  tests covered through `ancestors()`, `descendants()` and `children()`.
- **Step 6 — the `jira` block and `entry()` go** (`63978474`): filing works
  only into a project on this machine.
- **Step 7 — the switch** (`e4613092`). The registry walks up through
  `parents:` and down through listed `children:`, never to a sibling; a
  project read only to look another up is kept apart from the family;
  TCW-107's lookup order asks the manifests of every parent; a search answer
  that a manifest contradicts is a graph problem (AC 35). New
  `tests/test_parent_links.py` and `tests/test_parent_links_cli.py`. Every
  test whose outcome changed was rewritten with the rule that changed it;
  the list is under "Tests changed by the switch" below.
- **Step 8a — the fixtures** (`e92bbfa5`). Every fixture writes `parents:`
  and `children:`; `connect_projects(root, relation, *ids, inherit=...)` and
  `connect(a, b, relation, *, inherit=...)` take what a parent passes, and
  refuse any other relation. A production defect was found and fixed here:
  `tcw/config.py`'s `_list_problems` took `inherit` inside a parent entry for
  a chain list's `inherit` entry, so any `{id, inherit}` parent stopped every
  command; a CLI test is red without the fix.
- **Step 8b — `projects:` refused** (`5110da86`). `projects` and
  `connected-projects` give Design 3.5's message; in the active project or a
  descendant it is a graph problem, in an ancestor or an outside project it
  leaves that project's links unknown. The translation, `ConnectedProject`
  and `parse_connected_entry` are gone. `tests/test_parent_links_static.py`
  holds the AC 8 search (with a test of the shapes it must catch), AC 28 and
  a search for the 3.x bookkeeping names.
- **Steps 9 and 10 — personal children, and `sources(axis)`** (`113fa07a`).
  `children` is allowed in `.tcw/tcw-config.local.yaml` only
  (`LOCAL_ONLY_KEYS`), added after the committed list, and read only from the
  active project's personal file. `sources(axis)` gives the projects that
  pass an axis, in load order, raising `InheritedUnavailable` with Design
  6.2's sentence for the first one not available.
- **Step 11 — `extends` held to the parent links** (`ff09a966`).
  `_extends_target` in `tcw/store/fs.py` decides for both stores and both
  `extends add` methods, through the command's registry and the load order
  of the store's own project: an ID the links pass and that is here is
  opened; one passing but not here, or any ID while a passing project is not
  here, raises `InheritedUnavailable` (exit 7); any other ID is refused with
  Design 3.6's message (exit 1 when read, exit 2 from `extends add`, nothing
  written). `tcw validate` collects each such error and adds row (c),
  `; could not check the <axis> inherited from it`, to that project's one
  finding, or gives it one.
- **Step 12 — `tcw projects list --json` and the warning** (`bcd2efc1`).
  `inherit`, `personal`, `read-only`, `load-order`, `load-order-complete` and
  `load-order-warning`; the fallback warning is a `tcw validate` warning at
  `.tcw/tcw-config.yaml` and is printed by no other command.
- **Step 13 — the web app** (`a35c69af`). The project answer gives
  `readOnly` in place of `upstream`; the create form reads
  `<id> (read-only from here)`; the bundle is rebuilt.
- **Step 14 — records** (`de9887d2`). See below.
- **Step 15 — documentation entries** (`393d2b54`). See the table below.
- **Step 16 — notes for the later children.** Under "Notes for the later
  children" below, for the dispatching session to post.
- **Step 17 — the suite as CI runs it.** See the end.

## Decisions

Each decided by the implementing agent, the simpler and safer option where
there was a choice.

- **A problem's key path counts entries from 0** (`parents[0].id`), as Python
  does and as the AC 2 messages read.
- **Tests between steps ran in parallel** (`pytest -n 8`); the final run is
  the bare, serial one CI makes.
- **The plan's check that every link was appended in order was skipped**: the
  load-order tests cover the order directly.
- **A wholly unreadable ancestor file stays a graph problem**, as today;
  which configuration problems cross a link is TCW-109's.
- **A listed child counts as writable whether or not it names the lister
  back**: the name-back is a separate graph problem (Design 2.5), and making
  the write rule depend on it would report one fault twice.
- **The wording of "named both as a parent and as a child"** is the spec's,
  with both IDs quoted.
- **The translation's and the retired keys' problems in a descendant are
  graph problems** (Design 3.5, 6.6).
- **The handling of `connected-projects` by role was brought forward from
  Step 8b to Step 7**, because a test of an ancestor holding it changed
  outcome at the switch.
- **Reading a project only for a lookup rolls back the problems found
  reading its file**, so an outside project never adds a finding to the
  reader's run.
- **`ancestors()` includes outside projects read for a descendant's load
  order**, so the load order and the ancestors agree.
- **AC 35's comparison with the search runs only when another project's
  manifest decides**; the active project's own manifest is checked by
  `manifest_findings` already.
- **Which file a validate finding names**: a missing project names the file
  that declared it (`UnreachableProject.declared_in`); an unreadable one the
  file whose link reached it.
- **For a broken own `parents:` in the active project the links are none**,
  so its load order is the project alone and the graph is invalid; TCW-109
  can rely on that.
- **Step 8a was converted by hand**, by three helper agents with one brief,
  in one commit, instead of a script and a hand commit: 89 of the 132 call
  sites were built texts the script would have passed to the hand commit
  anyway. The recorders and the comparison of outcomes before and after are
  the check.
- **The tests TCW-110's `connect_projects` places by the search, and the
  parent-link tests, get no manifest entries**: they place projects side by
  side on purpose, and an entry would stop the duplicate-folder tests from
  reaching the search. So the search-off run of Step 8a's proof 3 leaves
  them red, as recorded below.
- **Two expected-bytes assertions in `tests/test_config_edit_writers.py`
  moved from four-space to two-space indentation**: the editor copies its
  indentation from a nested mapping, and `parents:` is a list. What the tests
  are about, where the editor puts a key and that it keeps comments, is
  unchanged.
- **The 3.x inversions were made by hand** where a test extended a listed
  child or an upstream (the extended project made a parent passing that
  axis, the child link dropped from both files where keeping it would be a
  loop). The sites are named in the TCW-116 note below.
- **Steps 9 and 10 share one commit**, since `sources` is tested on the
  personal children's layout.
- **`_tree_roots` in `tcw/validate.py` records an `InheritedUnavailable`**
  like a store that cannot open: the store opens what it extends as it opens,
  so its own files cannot be scanned either, and its check says it could not
  be checked.
- **`extends` is decided from the store's own project's load order**, which
  may lie outside the active project's family (a sibling's store read by its
  full identifier, AC 9), using the command's one registry.
- **Self-extension is refused before the links are asked**, so "cannot
  extend itself" keeps its wording.
- **The tests whose outcome Design 3.6 and 6.3 changed** were rewritten to
  the new outcome: `test_check_federation_cycle` (now `b`'s
  `extends_add("a")` exits 2 and leaves the file unchanged),
  `test_extending_a_declared_but_absent_project_says_so` and
  `test_extends_add_names_a_declared_but_absent_project` (exit 7),
  `test_extending_a_project_that_was_never_declared_is_unchanged` and
  `tests/test_taxonomy.py::test_check_unknown_extends_project` (Design 3.6's
  message), `test_a_cycle_is_reported_from_the_top_of_the_chain` and
  `tests/test_taxonomy.py::test_check_cycle` (the refusal of a project
  extending its descendant, which is what now stops the cycle), and
  `test_an_absent_upstream_is_a_warning_and_extends_says_unreachable`
  (exit 7).
- **AC 27's test watches every file opened** (`open` and `Path.read_text`),
  not only the registry's reads, and checks that it saw the project's own
  configuration read, so it would see the other's.
- **The spec is not reformatted.** `spec/spec.md` failed `prettier --check`
  before this item's one edit to it (`35309a11`); `prettier --write` would
  re-indent its YAML example and break a code span that wraps a line, so it
  was left as reviewed. Every other file this item changed passes.

## Tests changed by the switch (Step 7)

Each with the rule that changed it:

- `tests/test_worktree_sibling_nodes.py`: three tests look a sibling up from
  its parent or with `project_folder`, since a sibling is not in the family
  (Design 3.3, 3.7); the duplicate across two repositories is still raised
  (TCW-107 Design 2.9).
- `tests/test_projects_list.py`: parents in listing order, then children; a
  3.x upstream is a parent row (Design 8.1, 3.5).
- `tests/test_validate_command.py::test_the_former_child_warning_names_its_file_once`:
  removed; the read-as-upstream warning has no 4.0 counterpart.
- `tests/test_store_nodes.py`, `tests/test_project_registry.py`:
  `ancestors()` is farthest first (Design 3.2); the 3.x single-parent calls
  rewritten on `parents()` and `get()` (AC 28); the name-back message is
  Design 2.5's (AC 6).
- `tests/test_project_graph_paths.py`, `tests/test_override_in_linked_worktree.py`
  (4), `tests/test_override_letter_case.py` (4): run from the parent, since a
  descendant's siblings are never looked up (Design 3.1).
- `tests/test_upstream_projects.py`: an upstream is a parent passing nothing;
  a self-upstream is the loop `app -> app`; an upstream that is also a child
  is "named both"; the sibling and grandparent upstream problems, the two
  declarers test and the read-as-upstream warning are removed (each is a
  valid parent graph, or has no counterpart).
- `tests/test_project_lookup.py`, `tests/test_manifest_cli.py`: the resolved
  folder (AC 36), the loop's message (Design 4.7), a former upstream's
  manifest read as an ancestor's (Design 3.4), every parent found before any
  child is looked up (Design 3.4, TCW-107 2.11 a).

Removed in Step 8a: seven tests (10 IDs) of the retired writers in
`tests/test_projectfiles_helper.py`. Removed in Step 8b (20 IDs): the
translation tests; tests of the 3.x entry form, which no longer exists; the
`jira` block tests, duplicates of AC 8 now; and
`test_the_workspace_migration_passes_through_no_blocked_state`, already
skipped as not ported, with its line in `tests/not_ported.py`.

## Mutation checks

Each mutation was applied in a test plugin (reaching `tcw` subprocesses
through a `sitecustomize` folder), the suite run with the search for
project folders turned off, and compared with the same run unmutated (80
red, every one a test that places projects by the search on purpose). The
reasons were read for 13 of the red tests across 12 files; each was the
removed link.

- `parse_children` returns no children: 92 more red across 31 files.
- `inherit` forced to none: 1 more red at `113fa07a`, since nothing outside
  `sources` read `inherit` until Step 11; after Step 11, 202 more red across
  24 files.
- links with a partial `inherit` dropped: 111 more red across 27 files.
- every parent list reversed: 0 more red with the search off at `113fa07a`,
  because every test of the order of several parents places its projects by
  the search; after Step 11, 4 more red across 3 files with the search off,
  and with the search on 12 of the 37 tests of `tests/test_parent_links.py`
  red. A first run of this mutation under several workers applied the
  reversal twice, which undid it; the plugin now applies each mutation once
  per process.
- AC 27: a read of the neighbouring project's configuration added to
  `tcw projects list` turns the test red, naming that file.
- AC 33's client test: the label rule changed so `readOnly: true` no longer
  matches turns it red.
- `tests/test_parent_links_static.py`: removing an allowed test turns the
  AC 8 search red; a planted definition turns AC 28 and the name search red.
- AC 32's test was not mutation-checked.

## Handoffs folded in

- **TCW-110:** every `projects:` fixture went through `connect_projects`,
  converted in Step 8a; `_store_overlaps` now lists `ancestors()` and
  `descendants()` only, with no `declared_upstream_ids()`; a sibling is read
  by full identifier (Design 3.7, AC 9).
- **TCW-115:** a search answer that a manifest contradicts is a graph
  problem naming both folders and the personal manifest entry (AC 35).
- **TCW-107's qa:** "not on this machine" names the resolved folder, in a
  linked worktree the folder beside the main checkout (AC 36).
- **TCW-114:** the lookup starts only read-only git. This item adds no git
  call: every added line of `git diff 35309a11~1 HEAD -- tcw` was searched
  for `subprocess`, `"git"`, `_git(` and `_git_lines`; the only matches are
  two calls of the message helper `_holds_only_git`.

## Notes for the later children

- **TCW-109:** the spec's handoff as written. `sources("config")` and
  `ParentLink.inherit` are the inputs; `children` is in `LOCAL_ONLY_KEYS`,
  not `PERSONAL_KEYS`, and its merge is in `_merge` (`tcw/config.py`). For a
  broken own `parents:` in the active project the links are none, so the
  load order is the project alone. The conflict the spec names about
  `work.backend` and `work.tags` stands.
- **TCW-111:** fixtures cannot write `projects:`: the reader refuses it, and
  `tests/test_parent_links_static.py` fails on one outside the tests of its
  refusal. Write `parents:` and `children:`, or call
  `connect_projects(root, relation, *ids, inherit=...)`.
- **TCW-112:** `_extends_target` in `tcw/store/fs.py` is what it replaces: it
  asks `registry.passing_in(order, axis)` over the load order of the store's
  own project, which may be outside the family. `sources(axis)` gives the
  projects whose content reaches a project, in load order. Design 4.8 with
  AC 11's shape as a test. The capabilities store's federation cycle check
  can no longer fire once `extends` names only ancestors (a cycle needs a
  project to extend its descendant, which is refused), and goes with
  `extends`.
- **TCW-113:** `ancestors()`, `descendants()`, `declared_child_ids()`,
  `personal_child_ids()` and `load_order(id)` for a descendant.
  `InheritedUnavailable` reaches the web app as an HTTP 500, as any
  `TcwError` with no rule does.
- **TCW-114:** `read_only_reason`, the `read-only` row field and `readOnly`
  are interim (Design 7.1, 8.2, 8.5).
- **TCW-115:** `tcw project info` prints what `tcw projects list --json` now
  gives: `inherit`, `personal`, `read-only`, `load-order`,
  `load-order-complete` and `load-order-warning`.
- **TCW-116:** Step 4's `translate_projects` in `tcw/store/links.py` was the
  spec's mapping, with tests in `tests/test_projects_translation.py`, both
  deleted in Step 8b (`4b4056e4` holds both). It refused what TCW-107's
  reader refused, and left alone an `extends` naming a listed child. Step 8a
  inverted those by hand — the extended project made a parent passing the
  axis, and the child link dropped from both files where keeping it would be
  a loop — which `tcw migrate` must do too, and report. The sites:
  `connect_sources` in the taxonomy tests, `connect_many` in the capabilities
  tests, `_chain`, the ambiguous reference in `tests/test_capabilities.py`,
  the `rm` and `reset` tests, the reference wording, partial removal, the
  store editor twice, `PARENT`'s `other` in `tests/test_config_edit_writers.py`,
  the legacy store configuration, `tests/serve/test_records.py`,
  `_monorepo` in `tests/test_multiproject.py`, and `_federation_pair` in
  `tests/test_store_provisioning.py`. This repository's ledgers are still in
  3.x form.
- **TCW-117:** what each deferred document must say. `README.md`,
  `docs/guide/multi-repo.md`, `docs/guide/taxonomy-and-capabilities.md` and
  `skills/configure/references/projects.md`: parent links, `inherit`,
  children in either file (never the user-wide one), the load order and its
  warning, no `projects:` and no upstream, `extends` held to the links.
  `docs/guide/jira.md`: `:245`'s upstream, and filing through a `jira` block
  is gone. `docs/use-cases.md`: UC-2, UC-3, UC-4, UC-6 and S-6, as the spec's
  Notes list. The three skill passages: `skills/work/SKILL.md:103-115`
  (filing into a project not on this machine exits 3 whatever its entry
  says, since the `jira` block is gone; filing into a project reached through
  a parent that does not list the child exits 3 as read-only from here; and
  "On exit 7, report which project the command needs and pass on how to
  fetch it; do not retry"), `skills/taxonomy/SKILL.md:108-109` and
  `skills/capabilities/SKILL.md:120-121` ("A project may inherit the taxonomy
  of an ancestor whose parent links pass `taxonomy`", and the same for
  `capabilities`, until TCW-112 removes `extends`).

## Records

With the released CLI's format, in their 3.x form (`de9887d2`):

- New capabilities, status Supported, feature `project-registry`:
  `cli/name-a-projects-parents`, `cli/list-a-projects-children` and
  `cli/read-ancestors-in-one-load-order`.
- Changed, each description given what the spec's "Capability changes" says:
  `cli/host-multiple-projects-in-one-repo`, `cli/list-connected-projects`
  (its subjects now `parent-link` and `load-order`), `cli/validate-a-project`,
  `cli/override-the-team-configuration-for-myself`,
  `cli/declare-a-connected-projects-home-repository`,
  `cli/reference-a-tcw-object`, `taxonomy/federate-shared-vocabulary`,
  `capabilities/federate`, `work/delegate-a-work-item-to-another-project`
  and `web/editing`; `cli/rely-on-one-output-contract` was changed in Step 3.
  `cli/record-where-other-projects-are-in-a-manifest` also named `projects:`
  and was brought up to date.
- New taxonomy entries `parent-link` and `load-order`; `project`,
  `project-registry` and `personal-configuration` changed.
- Removed `cli/read-from-an-upstream-project` and `upstream-project`, after
  every reference to them was changed.

`tcw validate` with the released CLI: `0 errors, 0 warnings, 0 unresolved`.
`tests/test_documented_cli_surface.py` passes. Three changed records were
reformatted with `prettier`.

## Documentation entries

| Entry                                                                  | Answer                                                                                                                                            |
| ---------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| `README.md` [Public-API]                                               | Fires. Deferred to TCW-117; what it must say is in the notes above.                                                                               |
| `docs/guide/jira.md` [Jira-Change]                                     | Fires. Deferred to TCW-117, with the two facts in the notes above.                                                                                |
| `docs/guide/<topic>.md` [Guide-Topic-Change]                           | Fires. `docs/guide/cli.md`'s exit-code table changed in Step 3; `multi-repo.md` and `taxonomy-and-capabilities.md` deferred to TCW-117.           |
| `docs/release-notes/upcoming/<folder>.md` [Public-API]                 | Written: `docs/release-notes/upcoming/TCW-108-tcw-4-0-parent-links-per-parent-inheritance-and-the-load-order.md`.                                 |
| `docs/changelogs/upcoming/<folder>.md` [Any-Code-Change]               | Written: `docs/changelogs/upcoming/TCW-108-tcw-4-0-parent-links-per-parent-inheritance-and-the-load-order.md`.                                    |
| `skills/<component>/SKILL.md` [Skill-Driven-Component]                 | Fires. `skills/work/references/commands.md` changed in Step 3; the three `SKILL.md` passages deferred to TCW-117, as the spec's Non-goals record. |
| `skills/configure/references/<document>.md` [Configuration-Key-Change] | Fires. Deferred to TCW-117.                                                                                                                       |
| `docs/use-cases.md` [Project-Setup-Change]                             | Fires (UC-2, UC-3, UC-4, UC-6, S-6). Deferred to TCW-117.                                                                                         |

## Not done

- `tcw work advance TCW-108 --dry-run` (the records gate) is the dispatching
  session's to run.
- The QA plan's scenarios by hand, the web form in a browser, and
  `pnpm test:e2e` are for qa, as the plan says.
- The three helper agents of Step 8a could not be stopped by this agent
  (`TaskStop` answered that each is owned by itself); they are idle.

## The web client

`pnpm install --frozen-lockfile`, `pnpm check:build`, `pnpm exec tsc
--noEmit`, `pnpm test` (15 files, 188 tests) and `pnpm lint` pass at
`393d2b54`, and `pnpm exec prettier --check` passes over every file this item
changed or created outside `tcw/serve/dist`, except `spec/spec.md` (see
Decisions).

## The suite

`.venv/bin/pytest -q -p no:cacheprovider`, bare and serial as CI runs it, in
the foreground, split into two halves by folder to fit the time limit of one
run:

- `tests/work tests/serve`: `1912 passed, 2 skipped in 219.07s`
- `tests --ignore=tests/work --ignore=tests/serve`: `3987 passed, 111 skipped in 331.13s`

`5899 passed, 113 skipped`, at `393d2b54` (2026-10-23).

# Plan — TCW 4.0: parent links, per-parent inheritance and the load order

All work is on the `v4` branch, in the worktree `.claude/worktrees/v4`, with
its own virtual environment (`.venv/bin/pytest`, `.venv/bin/tcw`).

**Where the references point.** File and line references are to commit
`40d19b82` on `v4`, where TCW-106 is partly landed and TCW-107 and TCW-110 are
not built. Both rewrite much of the code this item changes: TCW-107
`tcw/store/project.py`, `tcw/store/base.py` and the test helpers, TCW-110
`tcw/work/open.py`, `tcw/work/gates.py`, `tcw/validate.py` and the reference
code. Where a step changes code one of them writes, it names that code by the
name their plans give it (TCW-107's plan, TCW-110's plan, cited by step), and
Step 0 re-reads every citation on the merged `v4` and corrects this plan before
Step 1. A citation that cannot be found then is fixed in this plan, never
worked around in the code.

**The gate at every step boundary.** Every step writes its tests first and
sees them fail for the reason they name, then makes the change, and ends with
the named tests passing and the **whole Python suite** passing:
`.venv/bin/pytest` with no arguments, from the worktree's root, as CI runs it.
A step that touches the web client also ends with TCW-110's web gate, from the
worktree's root: `pnpm exec tsc --noEmit`, `pnpm test`, `pnpm lint`,
`pnpm exec prettier --check <every file the step changed or created that
.prettierignore does not exclude>`, and `pnpm build` (which rewrites the
committed `tcw/serve/dist`). A step that cannot end green is two steps.

**Which `tcw` drives this repository's lifecycle, and keeping 4.0 code off
the live Jira board.** This item follows TCW-110's plan header exactly, rules
1-8 of its table: the lifecycle is driven with the `tcw` first on `PATH` (the
primary checkout's editable install of `main`, 3.x), never `.venv/bin/tcw`;
`.venv/bin` is never put first on `PATH` in a shell that runs a lifecycle
command; the 4.0 code is run only by the suite and in throwaway project
folders under the scratchpad, with the current folder set there; and
`scripts/remote_session_setup.sh` is never run from the worktree. This
repository's records stay in the 3.x format until TCW-116.

## What this plan relies on

From **TCW-106** (landing now; `git log` shows its steps through
`39603cc4`):

- `tcw/project_files.py`: `SENTINEL`, `LOCAL_SENTINEL`, `CONFIG_NAME`,
  `LOCAL_CONFIG_NAME`, `root_of`, `version_problem`, `KEY_PATTERN`.
- `tests/projectfiles.py`: `config_file`, `write_config`, `write_config_file`,
  `write_local_config`, and `_versioned` (`tests/projectfiles.py:42-63`),
  which every configuration writer goes through, and, once TCW-107 adds the
  two manifest names to `_CONFIG_NAMES` (`:25`, TCW-107 Step 2), every
  manifest writer too. So nothing in this plan hooks into `_versioned`: a
  manifest's own top-level key is `projects:` (TCW-107 Design 1.2), and a
  rule there would rewrite or refuse every manifest a test writes.
- `_read_config` refusing a 3.x project and an unreadable version
  (`tcw/store/project.py:559-563`, `:599-603`).

From **TCW-107** (its plan, steps named):

- `FsProjectRegistry.project_folder(project_id, named_by)` and its four
  outcomes (Step 3), `_locate` with its memo `_answers`, the `_Answer` record
  and its "named by the walk" test, which decides "not on this machine" against
  "unknown" (Step 3, the "Otherwise" bullet).
- `_read_text`, `_list_folder` and `_search`, the module-level functions every
  registry read goes through, which tests replace to count reads or to turn the
  search off (Step 3, choice 3).
- `UnreachableProject.message` (Design 6.2's sentence, rendered once) and
  `UnreachableProject.decided_by` (Step 3), `found(project_id)` (Step 3),
  `manifest_findings()` and `_cmd_validate`'s rule that drops a walk record
  whose deciding entry is in the active project's own manifests (Step 4,
  choice 2).
- One registry per command: `begin_command`, `end_command`,
  `forget_registries` (Step 5).
- `personal_file(root, name)`, which reads the main checkout's personal file
  from a linked worktree that has none (Step 6), and
  `personal_files_skipped()` in `tcw/project_files.py` (Step 1).
- `checkout_of` reading the manifests of the family in Design 2.2's order
  (Step 8).
- `ProjectGraphError` and `UnknownProject` in `tcw/errors.py` (Step 3).
- In the tests: `write_manifest`, `write_connected_config` and
  `write_connected_config_file` in `tests/projectfiles.py`, the `connect()`
  helper writing IDs under `projects:` and paths into a manifest
  (`tests/work/projects.py:45-54` today), the `tmp_path` override in
  `tests/conftest.py`, and the scratchpad plugin that turns the search off
  (Step 9's "Proves it", item 2), whose method this plan repeats.
- `ConnectedProject` reduced to `id` and `jira`, `parse_connected_entry`
  refusing locators, and `UnreachableProject.declaration` gone (Step 10).

From **TCW-110** (its plan, steps named):

- `tcw/locate.py`: `Locator.of(active_root)`, holding the command's one
  registry, `owner_root`, `read` and `find_tree` (Steps 7 and 8).
- Every tree store carrying the command's `Locator` as `self.locator` and its
  own project's ID as `project_id` (Steps 6 and 7).
- `open_project` locating any ID with `project_folder` (Step 7), so a sibling
  stays readable by full identifier once the walk stops reaching it (spec
  Design 3.7).
- The records gate routing a `capabilities.yaml` entry by its full
  identifier, with `project_reader` no longer asking `declared_child_ids()`
  (Step 11), which spec Design 2.6 and AC 32 rely on.
- `_store_overlaps(locator)` in `tcw/validate.py`, whose project list reads
  `ancestors()`, `descendants()` and the upstreams (Step 14).
- `print_json` writing `"schema": 2` (Step 4).
- `connect_projects(root, relation, *project_ids)` in `tests/projectfiles.py`
  (Step 3): "the one place this item's tests write a `projects:` entry",
  writing each ID under `projects.<relation>` of `root`'s configuration, by
  ID; its Step 17 note hands this item the job of converting its body.
- The tests its Step 17 note lists as connecting projects under `projects:`
  (`tests/test_locate.py`, `tests/test_links_full_identifiers.py`, the AC 12
  and AC 23 cases of `tests/work/test_gates.py`,
  `tests/test_tree_full_identifiers.py`,
  `tests/serve/test_full_identifiers.py`), and its "named by a manifest or
  `projects:` entry" condition from its spec's Design 6.1 table.

## Readings and choices where the spec leaves room

Choices 1 to 4 of the first draft were gaps in the spec; the plan review
agreed, and the spec now settles each one, so they are no longer the plan's
own readings:

1. **One finding, several rows**: spec Design 6.5 ("One finding per
   project"): the Design 6.2 sentence, then the suffix of each row that
   applies, (a), (b), (c) in order; for an unreadable project, row (d)'s text
   then (c)'s suffix; `where` the file of the first row that applies.
2. **An `extends` ID when what lies above is unknown**: spec Design 3.6.
   When the ID does not pass the axis and a project that passes it is
   missing **or** unreadable, `InheritedUnavailable` is raised for the first
   such project in load order (exit 7), in `tcw taxonomy|capabilities
   extends add` too, and `tcw validate` reports row (c), not an error.
3. **`projects:` or `connected-projects` in another project's file**: spec
   Design 3.5 and 6.6. In the active project or a descendant it is a graph
   problem; in an ancestor, or a project read only for a lookup, that
   project's links are unreadable (row d; exit 7 only for the axes it
   passes). `connected-projects` gets Design 3.5's message with its own key
   named, since its message today (`tcw/store/base.py:473-479`, "renamed to
   'projects'") would be wrong.
4. **Problems in another project's `children:`**: spec Design 6.6, last
   paragraph. An ancestor's `children:` is read only as names (Design 2.5):
   an entry that is not a valid ID is dropped there, and "named both as a
   parent and as a child" counts as a `children:` problem, so it is not
   checked in an ancestor or a project read only for a lookup. A
   descendant's committed `children:` problems, the name-back check on it,
   and "named both" in a descendant stay graph problems.
5. **A loop found after the walk.** A loop among projects read only for a
   descendant's load order (Design 4.6) or for a lookup (Design 3.4) is found
   when that question is asked, after `require_valid` has passed. It is
   raised there as `ProjectGraphError` (exit 1), with Design 4.7's message,
   and recorded in `check()` for `tcw validate`.
6. **`children` in `tcw config show`.** The configuration reader keeps a
   personal `children` list and merges it as Design 2.1 says (the committed
   list, then the personal additions), so `tcw config show --origin` shows each
   entry with its file. The registry reads the lists itself and checks their
   entries; the configuration reader decides only which file may hold the key.
7. **Exit 7 in the web app.** `tcw serve` answers an `InheritedUnavailable`
   as it answers any `TcwError` it has no rule for (HTTP 500,
   `tcw/serve/server.py:90-91`). The spec asks nothing of the web app here
   beyond `readOnly`; a better answer is left to TCW-113 (Step 17's note).
8. **The write rule's message names one link.** For a project reached across
   several links, the `read-only` message (Design 7.1) names the first
   one-sided link on the first upward route in walk order.

## Step 0 — start from what TCW-106, TCW-107 and TCW-110 left

Checks, before any change:

- TCW-106, TCW-107 and TCW-110 are completed and on `v4`; none of this item's
  code is (`projects:` still holds `parent`, `children` and `upstream`, by ID
  only).
- `pnpm install --frozen-lockfile` has been run at the worktree's root.
- Every function, file and line this plan cites is re-read and corrected in
  this plan. In particular, by `grep` on the merged tree: TCW-107's `_locate`,
  `_Answer`, `_follow_edges`, `checkout_of`, `manifest_findings`, the
  "named by the walk" test and the exact wording of its Design 6.2 sentence
  and where it is rendered (Step 10 stores the part after its colon as a
  field of its own, `remedy`, spec Design 6.2); TCW-110's
  "manifest or `projects:` entry" condition (`grep -rn "projects" tcw/locate.py
  tcw/store/project.py`), `Locator`'s attribute holding the registry,
  `_store_overlaps`, and whether `_extended_component_stores`
  (`tcw/store/fs.py:991-1075`) still opens a registry at the extending
  project's root (`:1010`); the callers of `entry()` in `tcw/work/open.py`
  (`:95`, `:131`, `:145`, `:172` today).
- Every caller of every registry method whose answer this item changes in
  `tcw/`, listed with
  `grep -rn "\.parent(\|\.ancestors(\|\.descendants(\|declared_child_ids\|declared_upstream_ids\|declared_parent_id\|read_only_reason\|\.entry(\|unreachable_project(\|\.unreachable(\|\.children(\|\.projects()\|registry\.get(" tcw --include=*.py`,
  so Step 7 changes each one and misses none. `get` now answers for the
  family only (spec Design 3.3), and at `40d19b82` its callers are
  `tcw/projects_cli.py:38`, `tcw/cli.py:293`, `:443`,
  `tcw/work/open.py:93`, `:131`, `:143`, `:171`, `:183`, `:198`,
  `tcw/work/gates.py:470`, `tcw/serve/work.py:558` and `tcw/store/fs.py:1013`,
  `:1972`, `:2727` (the helpers at `:438`, `:516`, `:527` go in Step 5);
  `unreachable()` is read by `tcw/cli.py:428` and `unreachable_project`
  (`tcw/store/project.py:1124`). `tcw/validate.py:684` (`_shared_work_paths`,
  which TCW-110 replaces with `_store_overlaps`) lists `ancestors()` and
  `descendants()` and so changes meaning too.

**Inventories**, taken now and kept in the scratchpad (not the repository),
for Steps 7 and 8:

- `pytest --collect-only -q` (every test ID), and, from a one-off script that
  walks each test function's syntax tree, the number of `assert` statements
  and `pytest.raises` blocks per test function (TCW-107 Step 9's method).
- The files that write a 3.x relation:
  `grep -rlE "projects:|\"projects\"|'projects'|setdefault\(\"projects\"|connect\(|connect_projects\(|upstream" tests`
  (53 files at `40d19b82`, before TCW-107 and TCW-110 add theirs), with the
  lines that are arguments of `write_manifest` or a manifest file's
  `write_text` left out by reading them, since a manifest's own key is
  `projects:`; and among them the files that write a configuration without
  going through `tests/projectfiles.py`
  (`grep -rln "tcw-config" tests | xargs grep -ln "write_text\|write_bytes\|safe_dump"`).
- The files that use `extends` (`grep -rl "extends" tests`, 31 at
  `40d19b82`), and among them **every test whose `extends` names a project
  its fixture connects as a listed child or as a 3.x upstream**, whichever
  way the `extends` is written: in configuration text; through
  `declare_extends` or `set_component_key` (`tests/nodeconfig.py`, used by
  `write_config` in `tests/test_taxonomy.py:42-46`); through
  `extends_add` (`tcw/store/fs.py:1963-1981`, `:2718-2736`); or through `tcw
  taxonomy|capabilities extends add`. At `40d19b82` the listed-child shape is
  `connect_sources` in `tests/test_taxonomy.py:49-58` (17 call sites, e.g.
  `:187-188`, `:331-332`, `:543-544`, `:569-571`, `:848`), `connect_many` in
  `tests/test_capabilities_federation.py:62-70` followed by `extends_add`
  (`:196-199`, `:220-222`, `:362-365`, `:387-390`) and
  `tests/test_store_editor.py:213-216`; the upstream-then-CLI shape is
  `tests/test_upstream_projects.py:294-295`, `:374`, `:591`, `:656`; and
  TCW-110 adds the `connect_projects` callers whose tests extend (its Step 17
  note). This list is Step 8a's by-hand work; each entry names the test and
  the axis or axes it extends.

**Proves it:** bare `.venv/bin/pytest` passes on the merged `v4`; its count is
recorded in the implement round as the baseline.

## Step 1 — reading `parents:` and `children:`, not yet used

**Tests first.** New `tests/test_parent_links_parse.py`, unit tests of the
parser alone on literal mappings, one per rule:

- The three entry forms of spec Design 1.1 and every `inherit` value of 1.2
  (`all`, absent, `none`, `[config, taxonomy]` giving `{taxonomy, config}`,
  all three giving the same set as `all`).
- Every refusal of Design 1.3 and AC 2, each with its key path
  (`parents[2].inherit`) and file: `parents: core`; an entry `5`;
  `{inherit: none}`; `{id: Core}`; `{id: core, path: ../core}`;
  `inherit: some`; `inherit: [taxonomy, taxonomy]`; `inherit: [work]`;
  `inherit: []` (the message contains `inherit: none`); `parents: [core,
  core]`.
- `children:` (Design 2.1): not a list; a non-string entry; an invalid ID;
  a duplicate within the list; the project listing itself.

**Creates** `tcw/store/links.py`, the files store's reading of the two keys.
It reads no file and imports only `tcw.project_files` and `tcw.store.base`:

- `parse_parents(value, file) -> tuple[list[ParentLink] | None,
  list[tuple[str, str]]]`: the links in order, or `None` when there is any
  problem, and the problems as `(key path, message)`. `None` for the value
  means no `parents:`.
- `parse_children(value, file, *, own_id) -> tuple[list[str], list[tuple[str,
  str]]]`: the IDs in order, the invalid ones left out, and the problems.

**Changes** `tcw/store/base.py`, beside `Project` (`:111-121`), the model
types of spec Design 3.2: `AXES = ("taxonomy", "capabilities", "config")`,
`ParentLink(id, inherit: frozenset[str])` and `LoadOrder(ids, missing,
unreadable, warning)`, frozen dataclasses.

**Proves it:** the new test file; the full suite (nothing calls the new code).

## Step 2 — the load order, computed in one store-neutral function

The riskiest logic of the item, built alone with no registry around it.

**Tests first.** New `tests/test_load_order.py`, on parent links given as
plain data (a mapping from ID to a list of `ParentLink`, plus the sets of IDs
that are missing or unreadable):

- AC 10, 11 and 12 (the design's C3 examples, spec Design 4.2), each with
  `warning` `None`.
- AC 13 and 14 (the fallback, Design 4.4), with the warning of Design 4.5
  exactly as AC 13 gives it, and AC 14's `(at 'ee': 'cc', 'dd' cannot be
  placed)` with each name once; AC 14's two failing merges (`pp: [ee, ii]`
  names `ee`, `pp: [ii, ee]` names `ii`: the first merge to fail in the
  order merges are made, Design 4.5).
- AC 17's `passing(axis)`: `[kk, ll, gg]` for taxonomy and `[gg]` for the
  other two; with `ll: [{id: kk, inherit: [config]}]`, `[ll, gg]` for
  taxonomy.
- Design 6.4: a missing project and an unreadable one are placed as projects
  with no parents and listed in `missing` and `unreadable`; AC 20's `core,
  lib, app`.
- Loops (Design 4.7): `aa: [bb]`, `bb: [aa]` gives `aa -> bb -> aa` when `aa`
  was read first; `aa: [aa]` gives `aa -> aa`; AC 15's descendant loop gives
  `cc -> ee -> dd -> cc` with the read order `ws, cc, dd, ee`.
- **A property test** (spec Risks, "C3 is subtle"): 2,000 parent graphs with
  no loop, at most eight projects, some of them marked missing or unreadable,
  generated with `random.Random(108)` (no new dependency: `pyproject.toml:27`
  lists `pytest`, `jsonschema` and `setuptools` only). Each is checked three
  ways:
  - **Against an independent C3, Python's own** (Design 4.1). Python orders
    a class's bases by the same method, so the test builds one class per
    project, its parents first, with `type(id, tuple(<its parents' classes,
    in reverse listing order>), {})`; a missing or unreadable project gets no
    bases (Design 6.4). The class's `__mro__`, reversed and without `object`,
    must equal `load_order_of(...).ids` with `warning` `None`; a `TypeError`
    while building any class of the graph means the implementation must have
    fallen back (Design 4.4: any merge failing). Checked by hand before this
    plan was revised: it gives AC 10, 11 and 12 exactly and raises for AC 13,
    AC 14 and both orders of AC 14's two-failure graph.
  - **Against a transcription of Design 4.4 and 4.5**, written in the test,
    for the graphs that fall back: the depth-first order, `<Q>` (the first
    merge to fail, each project's merge after its parents', parents in
    listing order) and its heads.
  - **Rules that hold for any graph**: each project appears once; the
    project comes last; each project comes after all of its own ancestors
    (Design 4.3); and when there is no fallback, each project's parents
    appear in its listing order.

  The generator counts the graphs that fall back and the test requires at
  least 10% of them to (and at least 10% with a missing or unreadable
  project), so a generator that stopped producing hard cases would fail
  rather than pass quietly. **Mutation check**, recorded in the implement
  round: with the implementation's parent lists not reversed (plain C3), the
  property test goes red, and the failing graph it prints is read.

**Changes** `tcw/store/base.py`, module-level functions given parent links and
nothing else, so any store can call them (spec litmus table, "Load order,
fallback and loop"):

- `find_loop(links, read_order) -> list[str] | None`: a loop through the
  links, as the list Design 4.7 prints, starting at the member that comes
  first in `read_order`, each next one a parent of the one before.
- `load_order_of(project_id, links, *, missing, unreadable) -> LoadOrder`:
  Design 4.1 (C3 over the reversed parent lists), 4.3, 4.4 (if any merge fails,
  the whole order is depth-first) and 4.5's warning text, with `<Q>` the first
  project whose merge failed, the merges made each after its parents' and
  the parents taken in listing order, and its distinct heads in list order. A missing
  or unreadable project has no parents (6.4). Assumes no loop; it guards with
  a depth limit and raises `ValueError` rather than recursing without end.
- `passing(axis, project_id, links) -> set[str]`: Design 5.1.
- `loop_message(loop) -> str`: `loop in parents: a -> b -> a`.

**Proves it:** the new test file and its mutation check; the full suite.

## Step 3 — exit code 7

**Tests first:**

- `tests/test_cli_help_standard.py:151`: `range(8)`.
- `tests/work/test_errors.py:18`: the tuple ends `…, 6, 7)` and names
  `codes.INHERITED_UNAVAILABLE`; a new assertion that
  `InheritedUnavailable("x").code == 7`.
- New `tests/test_exit_code_tables.py` (AC 25): each of `docs/guide/cli.md`,
  `docs/capabilities/cli/rely-on-one-output-contract/description.md` and
  `skills/work/references/commands.md` has a table row starting `| 7 |`, and
  none of the three tables' rows for 3 or 5 contains `upstream` or `jira`
  block. Each table is found by its header row, not by line number.

**Changes**

- `tcw/exit.py`: `INHERITED_UNAVAILABLE = 7  # something this project inherits
  is not available here`.
- `tcw/errors.py`: `InheritedUnavailable(TcwError)` with that code, carrying
  `project` (the one that is not available), `axis` and `reason`
  (`"missing"` or `"unreadable"`) as attributes, so `tcw validate` can turn
  one into a finding (Step 11).
- `tcw/cli_help.py:38-49` (`EXIT_CODES`): a line
  `7  inherited unavailable: a project this one inherits from is not on this
  machine, or its parent links could not be read`.
- The three tables, with spec Design 8.3's meaning for 7:
  `docs/guide/cli.md:140-148` (also rows 3 and 5 lose "creating an item in an
  upstream project" and "has no `jira` block", and row 5's example names
  TCW-107's manifest entry rather than `tcw provision`, as TCW-107 left it),
  `docs/capabilities/cli/rely-on-one-output-contract/description.md:27-35`
  and `skills/work/references/commands.md:33-41`.

**Proves it:** the three test files; the full suite. Nothing raises the new
error yet.

## Step 4 — the reader's temporary translation of `projects:`, not yet used

**Why the translation is in the reader, for a few commits.** The first draft
put the conversion of 3.x `projects:` into the test helpers (`_versioned`).
The plan review showed three ways that fails: `_versioned` also writes
manifests, whose top-level key is `projects:`; an `extends` written after the
relation (by `declare_extends`, `extends_add` or the CLI) never passes through
a helper; and TCW-110's `connect_projects` might bypass it. A translation in
the configuration reader sees every file whatever wrote it, and never sees a
manifest. It is transitional production code, removed in Step 8b, before the
item completes; nothing is released in between (spec Risks).

**Tests first.** New `tests/test_projects_translation.py`, unit tests of the
function alone on literal mappings (the parsed configuration):

- `projects: {parent: {ws: }}` gives the `parents` value `[ws]`;
  `projects: {children: {a: , b: }}` gives the `children` value `[a, b]`.
- `projects: {upstream: {core: }}` with no `extends` gives
  `[{id: core, inherit: none}]`; with `taxonomy: {extends: [core]}`,
  `[{id: core, inherit: [taxonomy]}]`; with both axes extending it,
  `inherit: [taxonomy, capabilities]`.
- An `extends` naming a project the same file does not name under
  `projects:` (a sibling, in 3.x) appends `{id: <it>, inherit: [<the axes
  extending it>]}` after the translated parents (after, so that a sibling
  listed after the shared parent keeps C3's order: `x: [p, y]`, `y: [p]`
  gives `p, y, x`). One already a translated parent adds nothing.
- An `extends` naming a project the same file lists under
  `projects.children` adds nothing and changes nothing: at Step 7 that child
  is a descendant, which `get` still finds, so the test keeps working; Step
  8a inverts each such fixture by hand (Step 0's list).
- **What TCW-107's reader refused is still refused, with the same
  messages**, so a test of invalid input still tests a refusal (the review's
  S2): an entry whose value is not null or `{}` (TCW-107's
  `parse_connected_entry` refusal of a locator); a `projects.parent` with more
  than one entry (`projects.parent must contain at most one entry`,
  `tcw/store/project.py:640-641`); a `projects:` value that is not a mapping.
  Each entry is checked by calling `parse_connected_entry` itself, so a
  `jira` key is refused here from Step 6 on, when that function starts
  refusing it (Step 6 adds that case to these tests). The function returns
  the problems and no links.
- A file holding `projects:` together with `parents:` or `children:` is a
  problem naming both keys, so nothing is merged silently while fixtures are
  half rewritten.
- A file with no `projects:` is returned unchanged, so a `parents:` or
  `children:` file passes through as it is: applying it twice changes
  nothing.

**Changes** `tcw/store/links.py`: `translate_projects(raw, file) ->
tuple[dict, list[tuple[str, str]]]`, the mapping of the spec's Design 3.5
and Notes (TCW-116's), returning `raw` with `projects` replaced by `parents`
and `children` values, and the problems. A module-level `_on_translate`
hook (default `None`), called with the file each time the function changes
something, which Step 8a's scratchpad plugin sets to record which tests
still rely on it. Nothing calls the function yet. Its docstring says it is
transitional: it exists only while this repository's own fixtures move off
`projects:`, and goes before the item completes.

**Proves it:** the new tests; the full suite.

## Step 5 — the single-parent helpers go

Spec Problem 7, Design 8.4, AC 28 (for these names). Done while `projects:`
still works, so that what their tests covered can be kept, and the switch in
Step 7 has fewer things to change.

**Changes**

- `tcw/store/fs.py:406-543` and `:584-592`: removes `child_projects`,
  `_routed`, `routed_children`, `routed_unreachable_children`,
  `parent_project`, `registered_parent`, `registered_children`,
  `unreachable_parent`, `unreachable_children`, `descendant_projects` and
  `registered_project_id`, with the comment above them (`:406-411`).
  `_has_work_store` (`:545-561`) stays if anything else calls it, otherwise it
  goes too.
- `tests/test_store_nodes.py:5-10`, `:71-90`: the two tests that reach only
  the helpers are rewritten on the registry, keeping what they cover: the
  topology is transitive and does not depend on folder layout
  (`children()`, `descendants()`, `ancestors()` from
  `FsProjectRegistry.open`), and a decoy project under `node_modules/` or a
  `.worktrees/` copy is never a descendant.
- `tests/test_environment_hardness.py:38-39`, `:268-269`, `:338-342`, `:381`,
  `:415-423`: the same, on `ancestors()`, `children()` and `descendants()`,
  keeping each assertion about worktrees and environment hardness. Each
  single-parent assertion is written so it holds under 4.0 as well (one
  parent, so "nearest first" and "farthest first" agree).
- `tests/test_multiproject.py:123-170` uses `tcw projects list` and is
  unaffected; its docstring's mention of `child_projects` (`:160`) is
  reworded.

**Proves it:** `grep -rn` for the eleven names finds nothing in `tcw/` or
`tests/`; the rewritten tests; the full suite; the step's inventory (no test
ID gone except the ones rewritten, each listed with Design 8.4).

## Step 6 — the `jira` block and `entry()` go

Spec Design 7.2 and the `entry()` half of 3.2. Also done while `projects:`
works, because neither depends on parent links.

**Tests first.** In `tests/work/test_open.py`: with `ws` declared under
`projects.children` and not on this machine, `tcw work new --project ws 'x'`
exits 3 and its message names no `jira` block (AC 21, last sentence); an entry
holding a `jira` block is now a configuration problem (`tcw validate` exits 1
naming the key), since `parse_connected_entry` no longer accepts one; and in
`tests/test_projects_translation.py`, Step 4's translation refuses it.

**Changes**

- `tcw/work/open.py`: `entry()`'s callers (`:95`, `:131`, `:145`, `:172`
  today; Step 0's list) ask `unreachable_project` instead (spec Design 3.2);
  `delegate`'s branch for a project not here with a `jira` block
  (`:172-176`) and `_check_target`'s message about it (`:145-149`) go, so such
  a filing is refused as any project not on this machine.
- `tcw/work/jira/tickets.py:323-358`: `delegate_to_jira` loses its `block`
  parameter and the branch that reads it; `tcw/work/jira/config.py:67` onwards
  (`DelegationTarget`), `:229-260` (`parse_delegation_block`) and `:262-280`
  (`connected_block_problems`) go when nothing else calls them (checked by
  `grep`); `tcw/validate.py:560`, `:567-568` stop calling
  `connected_block_problems`.
- `tcw/store/base.py`: `ConnectedProject` (`:699-720`) loses `jira`;
  `parse_connected_entry` (`:865-916`) refuses a `jira` key with a message
  saying TCW 4.0 files only into a project on this machine.
- `tcw/store/project.py:391-399`: `entry()` goes.
- Tests: `tests/work/jira/test_jira_delegation.py`'s two tests of the block
  (`:80`, `:100`) are removed with Design 7.2; `:93` (a target not here with
  no block, exit 3) stays, as it is now the only outcome; the tests of filing
  into a Jira-mode project that **is** on this machine stay.
  The others found by `grep -rn "jira:" tests | grep -i "projects\|block"` are
  read one by one and listed in the round.

**Proves it:** the new tests; `grep -rn "def entry\|connected_block_problems"
tcw/` finds nothing; the full suite.

## Step 7 — the switch: the registry follows parent links

This is the core of the item and its riskiest step, put here so that the load
order (Step 2), the parser (Step 1), the error code (Step 3) and the
translation of `projects:` (Step 4) exist and are tested before it, and the
removals of Steps 5 and 6 are already done. The switch is split three ways,
each with one possible cause of failure (the review's S1):

- **Step 7**: the registry follows parent links, reading `parents:` and
  `children:`, and translating `projects:` with Step 4's function. No
  fixture changes, so every failure is a behaviour the spec deliberately
  changed (siblings, upstream bookkeeping, the write rule): the 7f table,
  with nothing about conversion mixed in.
- **Step 8a**: the fixtures are rewritten while the translation still runs,
  and the set of passing tests must not change: the same reader reads two
  spellings of the same graph.
- **Step 8b**: the translation goes and Design 3.5's refusal lands.

Step 7 itself cannot be split further and stay green: the walk, the lookup
order and the write rule change together, because each reads the others'
answers.

### 7a. Tests first

New `tests/test_parent_links.py`, calling `FsProjectRegistry.open(<root>)`
directly, on fixtures written in `parents:` and `children:` with
`write_config` and TCW-107's `write_manifest` under `tmp_path`:

- The walk and the family (Design 3.1, 3.3): AC 9's registry part
  (`get("b")` is `None`, `descendants()` is `[]`, `ancestors()` is `[ws]`);
  AC 16 (`load_order("a").ids == ("core", "ws", "a")`, `get("core")` is
  `None`, `descendants()` is `[a]`); `descendants()` breadth first.
- `parents()`, `declared_child_ids()`, `children()`, `ancestors()` in load
  order, `projects()` holding the family only.
- AC 10-14 at the registry level, through real projects, each load order
  equal to Step 2's answer for the same links.
- AC 15's three loops, as graph problems with their messages, and no "named
  both as a parent and as a child" problem in the descendant loop.
- AC 22, 29 and 30 (TCW-107's lookup with parent links, Design 3.4): each
  `found(...)["file"]` as the criterion says; AC 29 with the entry in `app`'s
  personal manifest (personal files turned on for that test, since
  `tests/conftest.py:176` turns them off) and again in its shared manifest.
- A sibling not on this machine is "not on this machine", not unknown
  (Design 3.4, the 2.12 rows): from `a`, `project_folder("b", a)` raises
  `Unreachable` when `ws` lists `b` and `b`'s folder is absent, and
  `UnknownProject` when nothing names `b`.
- Design 6.6's first two bullets: `lib`'s `parents: core` (not a list) is not
  a graph problem from `app` (`require_valid()` passes), `lib` is in
  `load_order().unreadable`, and nothing above `lib` is looked up (counted
  through `_read_text`).
- Design 7.1 (`read_only_reason`): AC 21's `lib`, `ws`, `top` and `sib`.

New `tests/test_parent_links_cli.py`, running `tcw` in the folder the test
builds, as `tests/test_project_files_cli.py:42-49` does:

- AC 2 (every case, `tcw projects list` exit 1, the `where` of `tcw validate`'s
  error), AC 3 (`parents:` in `tcw-config.local.yaml` and in the user-wide
  file; today's "a shared key" refusal, `tcw/config.py:398-404`, with no code
  change), AC 4, AC 6 (its committed part), AC 9 (the
  plain listing, `tcw work show b.work/<folder>` with `b` here and absent, and
  no finding naming `b`), AC 13's last sentence (`tcw work list` in `zz`
  prints nothing on standard error), AC 15 (exit codes), AC 21, AC 23's plain
  listing, AC 31's sentences on `lib` itself, the loop and "named both"
  (`tcw projects list` in `lib` exits 1; the loop through `top` makes `tcw
  work list` in `app` exit 1; `lib: [top]` with `children: [top]` gives no
  finding in `app` and the complete order `top, lib, app`, choice 4). Its
  `projects:` sentences are Step 8b's.

### 7b. The registry

`tcw/store/base.py`, `ProjectRegistry` (`:184-310`):

- Adds the abstract `parents(project_id=None) -> list[ParentLink]`.
- Adds concrete `load_order(project_id=None)`, built from `parents()` and a
  new concrete `link_state(project_id) -> "here" | "missing" | "unreadable"`
  (default: `"here"` when `get` answers, `"missing"` otherwise) by calling
  Step 2's `load_order_of`; so the order is the declared links' property, as
  spec Design 3.2 asks. `sources` is added in Step 10.
- Removes `parent()`, `declared_parent_id()` (`:192-205`),
  `declared_upstream_ids()` (`:212-220`); rewrites the docstrings of
  `declared_child_ids` (now including personal children, Step 9),
  `read_only_reason` (`:222-232`, Design 7.1), `ancestors` (load order without
  the project), `descendants` (breadth first, `:283-285`) and `projects` (the
  family, no siblings, `:287-296`).
- `ConnectedProject` and `parse_connected_entry` (`:699-720`, `:865-916`)
  stay until Step 8b, called only by Step 4's translation, which keeps their
  refusals; `retired_key_problem` (`:473-479`) is unchanged until Step 8b.

`tcw/store/project.py`, `FsProjectRegistry` (as TCW-107 leaves it):

- `_Config` (`:161-168`) holds `project`, `path`, `links: list[ParentLink] |
  None` (`None` when unreadable, Design 6.6), `link_problem: str | None`,
  `children: list[str]` (the committed list; for an ancestor, names only) and
  `raw`. `parent`, `children` and `upstream` as mappings of
  `ConnectedProject` go.
- `_read_config` (`:554-652`) takes the project's role in the walk
  (`active`, `ancestor`, `descendant`, `outside`). A `projects` key is
  passed through Step 4's `translate_projects` first, in every role, its
  problems treated as `parents:` problems of that role (below); a
  `connected-projects` key keeps today's problem. Then the links are read
  with `parse_parents` and `parse_children`. In the `active`
  role every problem is a graph problem against the file and key; in another
  role a `parents:` problem is recorded as `link_problem` and the links as
  unknown (Design 6.6), not a graph problem; `children:` problems are graph
  problems in the `active` and `descendant` roles and dropped in the
  `ancestor` and `outside` roles (choice 4). "Named both as a parent and as a
  child" (Design 1.3) is checked in the `active` and `descendant` roles. The
  `projects.parent must contain at most one entry` problem (`:640-641`) moves
  into Step 4's translation, which goes in Step 8b; `quiet_connections`
  (`:642-644`) goes.
- The walk (Design 3.1) replaces `_follow_edges` (`:543-552`) and the
  upstream branches of `_visit` (`:497-507`, `:519-523`, `:537-539`):
  `_walk_up(cfg)` takes each parent in listing order, locates it with
  `_locate(parent_id, named_by=cfg's root)`, reads it in the `ancestor` role
  and walks up from it before the next parent; then `_walk_down()` takes the
  active project's listed children, then each descendant's, breadth first,
  each read in the `descendant` role. A descendant's parents other than the
  one it came from are not followed; a project reached twice is read once;
  nothing above an unreadable project is looked up. A project not on this
  machine is recorded by TCW-107's `_unreachable_edge` (`:1091-1111`) with its
  message, as TCW-107 leaves it, changed to keep **one record per ID**, the
  first in walk order: today it skips a record only when it is equal in every
  field, `declared_in` included (`:1110`), so a project reached by two
  links from two files, which several parents make common (a diamond), would
  give two records and two findings (AC 20's "exactly one"). Its readers are
  `unreachable_project` (`:1113-1124`, which already takes the first match)
  and `tcw/work/open.py`'s calls to it; both are re-read at Step 0.
- `_locate`'s Design 2.2 order (TCW-107 Step 3), as spec Design 3.4 rewrites
  it: after the asking project's own manifests, (b) the manifests of its
  ancestors found so far in the reverse of `load_order_of` computed over the
  configurations read so far, without the asking project, and with no warning
  when that order falls back (4.4); then (c) the manifests of every project
  read so far from which a chain of parent links leads up to the asking
  project, fewest links first and, at one distance, in the order the walk read
  them. Its "named by the walk" test reads: named by a `parents:` or
  `children:` entry of a project whose manifests the lookup consulted, an
  ancestor's `children:` names included. TCW-110's copy of that condition
  (Step 0's `grep`) is changed the same way.
- `project_folder`'s reading of a `named_by` not in the graph (TCW-107 Step
  3) walks upward only, every ancestor, in the `outside` role, into a separate
  `_outside` map that `get`, `ancestors`, `descendants` and `projects` never
  read (Design 3.3, the 2.12 bullet).
- `load_order(project_id)` for a descendant (Design 4.6) walks that
  descendant's parents with the same `_walk_up`, any not in the family read in
  the `outside` role into `_outside`. A loop found there is raised as
  `ProjectGraphError` (choice 5).
- **`load_order(id)` and `parents(id)` for a project outside the family**
  (spec Design 4.6's last sentence; the review's M4). When `id` is neither in
  the family nor already in `_outside`, the registry locates it with
  `project_folder(id, named_by=<the active project's root>)` (TCW-107's four
  outcomes propagate: `Unreachable`, `UnknownProject`, `ProjectGraphError`),
  reads it in the `outside` role and runs `_walk_up` from it into
  `_outside`, the same upward walk as the 2.12 bullet's. So `passing(axis,
  id, ...)` and the Step 10 `sources(axis, id)` are defined for every project
  TCW-110's `Locator.read` can open, which Step 11 relies on.
- `parents(id)`, `declared_child_ids(id)` (the active project's list, a
  descendant's committed list, an ancestor's names), `children(id)` (those of
  `declared_child_ids` the family holds), `ancestors(id)` (the load order
  without the project, those here), `descendants(id)` (breadth first, those
  here), `get(id)` and `projects()` (the family only), `link_state(id)`
  (`unreadable` for a configuration whose `link_problem` is set; `here` for one
  read into `_outside`).
- `_validate_name_back()` replaces `_validate_reciprocity` (`:878-938`): for
  the active project's list and each descendant's committed list, each listed
  child that is here and readable must name the lister among its parents, or
  the graph problem `'<child>' is listed as a child of '<parent>' but does not
  name '<parent>' among its parents` against the lister's file (Design 2.5).
  A child not here or unreadable is skipped (reported at 7d).
- `_validate_loops()` replaces `_validate_cycles` (`:982-1020`): `find_loop`
  over the links of every configuration read, in read order, as a graph
  problem against the first member's file (Design 4.7).
- `read_only_reason(project_id)` (`:356-389`), Design 7.1: `None` when the
  project is reached from the active one by links both sides declare (up only
  across a parent whose `children:` names the child, down across listed
  children); otherwise `'<X>' is read-only from here: '<parent>' does not
  list '<child>' among its children` (choice 8); `None` for a project the
  family does not hold, which `_check_declared` refuses on its own.
- Removed: `_upstream_only`, `_upstream_declarers` (`:203-209`),
  `_upstream_reader`, `_read_as_upstream` (`:863-876`), `_validate_upstreams`
  (`:940-959`), `declared_upstream_ids` (`:275-277`), `parent` and
  `declared_parent_id` (`:248-253`, `:265-269`), and their warnings.
- `checkout_of` (TCW-107 Step 8) reads the family's manifests in the order of
  `_locate` from the active project: its own, (b), then (c).

### 7c. The callers

- `tcw/projects_cli.py:21-51` (`connected`): rows for the current project,
  then each of `parents()` in order (`relation: "parent"`), then each of
  `declared_child_ids()` (`relation: "child"`), each once, with `present`,
  `path` and TCW-107's `found`. No upstream rows, no ancestors beyond the
  parents (Design 8.1). The module docstring (`:1-6`) says so. The JSON
  additions are Step 12's.
- `tcw/work/open.py`: `_check_declared` (`:129-136`) raises
  `Refused(reason)` with Design 7.1's text, without "an upstream project is
  read-only from here"; its docstring loses "not upstream".
- `tcw/validate.py`: TCW-110's `_store_overlaps` lists `registry.current`,
  `ancestors()` and `descendants()`, with no upstreams.
- `tcw/serve/work.py:147-148`: unchanged in this step (`upstream` is now
  always false); Step 13 replaces it.
- **Every caller of `get` and `unreachable()`** in Step 0's list is read
  against `get`'s new meaning (the family only, Design 3.3), and each is
  recorded in the round as unchanged or changed, with its reason. The ones
  expected to need a look: `tcw/work/open.py` (`:93`, `:131`, `:143`,
  `:171`, `:183`, `:198`, as TCW-110 leaves them: its `open_project` already
  locates with `project_folder`, so a sibling opened for reading stays
  readable, Design 3.7, while `_check_declared` refuses writing into it,
  Design 7.1); `tcw/work/gates.py:470` (TCW-110's records gate, which routes
  by full identifier and must not fall back to `get` for a sibling);
  `tcw/serve/work.py:558` (rows from `connected`, so family only already);
  `tcw/cli.py:293` and `:443` (as TCW-107 leaves them); and
  `tcw/store/fs.py:1013`, `:1972`, `:2727`, which keep `get` until Step 11
  replaces them with the passing set.
- The comments that describe the relation as "upstream"
  (`tcw/config.py:578`, `tcw/store/fs.py:326`, and any Step 0's search finds)
  are reworded. The override code's "upstream" (`tcw/store/fs.py:2348-2452`,
  `:2584-2687`), which means the extended project's own capability, is not
  the relation and stays.

### 7d. `tcw validate` for projects not available

Spec Design 6.5 rows (a), (b) and (d), so that a problem Design 6.6 stops
treating as a graph problem is still reported in this step:

- `FsProjectRegistry.availability()`: one record per project of the family's
  load order or of a listed child that is missing or unreadable, with the rows
  that apply to it (an ancestor: a; a listed child: b; unreadable: d), the
  file that names it, and, for a missing one, its `UnreachableProject`.
- `_cmd_validate` (`tcw/cli.py:427-436` today, as TCW-107 rewrites it): the
  loop over `registry.unreachable()` that makes one finding per record is
  **replaced** by one over `availability()`, so no project gets a finding
  from both. One `unresolved` finding per record, its message built by spec
  Design 6.5's rule (choice 1) from
  TCW-107's Design 6.2 sentence (`UnreachableProject.message`) and the row
  texts: (a) `; could not check what it passes down to '<P>' or the projects
  above it`, (b) `; could not check that it names '<P>' as a parent`, (d) the
  row's own message. Where TCW-107's `manifest_findings()` already reports
  the project (its deciding entry is in the active project's manifests,
  choice 2 of TCW-107's plan), the row texts are appended to that finding
  instead of making a second (last paragraph of Design 6.5).

### 7e. The fixtures are not touched

No test helper and no fixture changes in Step 7: the reader translates
`projects:` (7b), whatever wrote it, so `connect()`, TCW-110's
`connect_projects`, `connect_sources`, `connect_many`, `declare_extends`,
`extends_add` and the CLI all keep working, and manifests are never read by
the translation. The fixtures move in Step 8a.

### 7f. Reading every failure

The full suite is run, and every failure is read one by one. An assertion is
changed only where the spec deliberately changed the behavior it checks, and
each change is listed in the implement round with the design rule that changed
it. The ones expected, by file:

| File | What changes, and the rule |
| --- | --- |
| `tests/test_upstream_projects.py` | Upstream bookkeeping (the read-as-upstream warning, the "declared upstream but also connected" problem, an upstream's connections not followed, `tcw projects list`'s upstream rows) has no 4.0 counterpart and is removed (Design 3.5); its read-only tests are kept against Design 7.1's message; a test that an upstream's broken connections do not stop the reader is kept as Design 6.6 (its library's links are now followed, so it now proves the reader is unaffected through `availability()`). |
| `tests/test_project_registry.py` | Reciprocity: "nonreciprocal connection" (`:141-151`) becomes AC 4 (a parent need not list the child) and AC 6 (a listed child must name the parent), each with its own message; the cycle tests become Design 4.7's loop; the single-parent rule goes. |
| `tests/test_projects_list.py`, `tests/test_multiproject.py` | No upstream rows; a sibling never listed (Design 8.1). |
| `tests/test_capabilities_federation.py`, `tests/test_multiproject.py`, `tests/test_taxonomy.py` (`:566`), `tests/test_store_editor.py`, and the other users of `extends` | An `extends` of a listed child (`connect_sources`, `connect_many`) is unaffected: the child is a descendant, which `get` still finds (Step 8a inverts it). An `extends` of a sibling goes through the parent the translation appends (Design 3.6's form); a cycle of sibling `extends` becomes a parents loop (Design 4.7). An upstream extended through `extends_add` or the CLI after the relation (`tests/test_upstream_projects.py:294-295`, `:374`, `:591`, `:656`) gets an `inherit` holding that axis, since the translation reads the file's `extends` each time it reads the file. |
| `tests/test_config_edit_writers.py` (`PARENT`, `:23-24`; `ANNOTATED`, `:121-132`), `tests/test_store_editor.py` | Nothing: the file bytes they compare are not rewritten in Step 7. Converted by hand in Step 8a, never re-dumped, since they compare bytes. |
| The tests of an invalid `projects:` (TCW-107's locator refusals in `tests/test_manifest_cli.py`, the 2.x key in `tests/test_projects_list.py`, the one-parent rule) | Nothing: the translation keeps every refusal, with its message (Step 4). In an ancestor's file such a problem now makes that ancestor unreadable, not a graph problem (spec Design 6.6); each test that fails for that reason is listed with that rule. |
| `tests/work/test_open.py`, `tests/serve/test_work_write.py` (`:48-64`, `:200-204`) | Writing into a sibling is refused (Design 7.1, AC 21); an upstream is read-only by Design 7.1's message. |
| `tests/test_store_provisioning.py` (the registry rung, TCW-107 Step 8) | Manifest order from Design 3.4. |
| `tests/work/test_gates.py`, `tests/test_locate.py`, `tests/test_links_full_identifiers.py`, `tests/test_tree_full_identifiers.py`, `tests/serve/test_full_identifiers.py` (TCW-110) | `projects.upstream` naming `core` with no `extends` is read as `parents: [{id: core, inherit: none}]` (Design 3.5); `projects.children` naming `server` as `children: [server]`, with `server` naming `app`. No assertion is expected to change. |

**Proves it:** the new test files; the full suite with the translation in the
reader; `grep -rn "def parent\b\|declared_parent_id\|declared_upstream_ids\|_upstream_only\|_validate_reciprocity\|_validate_cycles" tcw/`
finds nothing; the inventory against Step 0's, every test ID that
disappeared or was renamed listed with the design rule that removed it.

## Step 8a — the fixtures are rewritten while the translation runs

No production code changes in this step, and the reader still translates
`projects:`, so a failure here can only come from the rewrite, and the set of
passing tests must not change.

**The work list.** Before commit 1, a one-off pytest plugin kept in the
scratchpad sets `tcw.store.links._on_translate` (Step 4) to record the test
running (`os.environ["PYTEST_CURRENT_TEST"]`) and the configuration file each
time the translation changes something, and the full suite is run with it.
The tests it records are the ones still relying on `projects:`. Tests skipped
in the local run (the `chmod` skips, live Jira) are never recorded; Step 8b's
static test is the backstop for them.

**Commit 1, mechanical.** A one-off script, kept in the scratchpad, walks each
test file's syntax tree and finds every call of a configuration writer
(`write_config`, `write_local_config`, `write_config_file`,
`write_project_config`, TCW-107's `write_connected_config` and
`write_connected_config_file`, and any other Step 0 finds) whose text argument
is a string constant, or `dedent(...)` / `textwrap.dedent(...)` of one,
holding a block-style `projects:` key. It replaces only that block's lines
with the `parents:` and `children:` lines `translate_projects` gives,
leaving every other byte of the constant as it was, in the same quoting and
indentation. `write_manifest` is not a configuration writer, so no manifest
text is ever touched. A constant whose block cannot be cut out cleanly (flow
style, a comment inside it), a call whose text is built (an f-string, a
variable, a dictionary dumped with `yaml.safe_dump`), and a test on Step 0's
`extends` list are not touched and are listed for commit 2.

**Commit 2, by hand**, so a reviewer can read the hand edits on their own:

- The calls commit 1 listed, and every dictionary-built configuration
  (`setdefault("projects")` and the like), written as `parents` and
  `children`.
- `connect()` (`tests/work/projects.py:45-54`, as TCW-107 leaves it): writes
  `parents:` for `"parent"`, `children:` for `"children"`, and
  `{id, inherit: none}` under `parents:` for `"upstream"`, with an `inherit`
  keyword its callers can set; the location in the manifest as now.
- **`connect_projects`** (TCW-110 Step 3, `tests/projectfiles.py`; the
  review's M3): the same change to its body, with the same `inherit` keyword
  (`"all"`, `"none"` or a list of axes); its docstring no longer says
  `projects:`. Each caller on Step 0's list whose test extends the project it
  connects passes `inherit=` with the axes extended; a caller whose test
  extends a project it connects as a child is inverted, as below. TCW-110's
  tests of the helper itself, if it has any, move with it.
- **The inversions** (the review's M2), each test on Step 0's `extends` list
  whose `extends` names a listed child: the extended project becomes a
  parent of the extender, with `inherit` holding the axes extended, and the
  child link between them is dropped from both files (spec Design 3.5).
  `connect_sources` (`tests/test_taxonomy.py:49-58`) and `connect_many`
  (`tests/test_capabilities_federation.py:62-70`) are rewritten to write that
  shape (the consumer names each source under `parents:` with `inherit:
  [taxonomy]` or `[capabilities]`; the sources name nothing), and each of
  their callers is read for an assertion that relied on the consumer listing
  its sources (a `tcw projects list` row, a `descendants()` call), which is
  changed to the parent row and listed with Design 3.5. An `extends` written
  later by `extends_add` or the CLI stays as it is: it now names an ancestor
  passing the axis, which Step 11's rule allows. Each 3.x upstream on the
  list that a test extends through the CLI (`tests/test_upstream_projects.py`)
  gets an `inherit` holding that axis. Each inverted test is run green under
  Step 7's rules before the next is started.
- **One test whose subject has no 4.0 form:**
  `test_check_federation_cycle`
  (`tests/test_capabilities_federation.py:217-222`), two projects extending
  each other. It is written here as `a: [b]` with `b` listing `a`, so that
  under Step 7 both `extends` still resolve (`a` is `b`'s descendant) and the
  test stays green; Step 11 rewrites it to assert Design 3.6's refusal of
  `b`'s `extends_add("a")` (exit 2), since an `extends` of a descendant is
  what 4.0 refuses.
- The byte-comparison tests (`tests/test_config_edit_writers.py`'s `PARENT`
  and `ANNOTATED`, `:23-24`, `:121-132`; `tests/test_store_editor.py`),
  edited in their text constants only, never re-dumped (the review's S2).
- TCW-107's `write_connected_config` and `write_connected_config_file`
  retired with their tests in `tests/test_projectfiles_helper.py` (their
  callers use `write_config` and `write_manifest`), as TCW-107's plan says
  this item does.

**Proves it**, each result recorded in the implement round:

1. The full suite passes, and the set of passing test IDs equals Step 7's.
2. The plugin of "The work list" records nothing: no test still relies on
   the translation.
3. **The search turned off**, as in TCW-107 Step 9: a one-off pytest plugin in
   the scratchpad replaces `tcw.store.project._search` with a function that
   finds nothing, and the full suite is run with it, leaving out the files
   whose subject is the search (TCW-107's three, and this item's search cases
   of AC 9 and AC 29, each named). Every test must still pass, which shows
   each converted fixture's projects are placed by its manifest. A test that
   fails is fixed by writing the manifest entry its fixture lacked.
4. **The inventory**: against Step 0's, no test ID disappeared in this step,
   and no test's count of `assert` statements and `pytest.raises` blocks
   dropped, except those listed in Steps 5-7 with their reason.

## Step 8b — `projects:` is refused, and the translation goes

Spec Design 3.5 and 6.6 (choice 3), AC 8.

**Tests first**, in `tests/test_parent_links_cli.py` and
`tests/test_parent_links.py`:

- AC 8: `projects: {parent: {ws: }}` in `a`'s configuration makes `tcw
  projects list` exit 1 and `tcw validate` report an error containing
  `parents:` and `tcw-manifest.yaml`; `connected-projects` the same, its own
  key named.
- AC 31's `projects:` sentences: in `lib` (an ancestor) every outcome in
  `app` is the one for `parents: core` (exit 0, row d with `'projects' is not
  a TCW 4.0 key`, `lib` in `load_order().unreadable`, `sources("taxonomy")`
  raising once Step 10 lands, so that part is written in Step 10); in `kid`
  (a descendant of `ws`) `tcw validate` in `ws` exits 1. The same for
  `connected-projects` in `lib`.

**Changes**

- `tcw/store/project.py`, `_read_config`: no longer calls
  `translate_projects`. A `projects` or `connected-projects` key gives Design
  3.5's message; in the `active` and `descendant` roles it is a graph problem
  against the file and key, and in the `ancestor` and `outside` roles it is
  recorded as `link_problem`, the links unknown (Design 6.6).
- `tcw/store/base.py`: `retired_key_problem` (`:473-479`) gives Design 3.5's
  message for `connected-projects`; `ConnectedProject` and
  `parse_connected_entry` (`:699-720`, `:865-916`) go, since nothing calls
  them any more.
- `tcw/store/links.py`: `translate_projects`, `_on_translate` and
  `tests/test_projects_translation.py` are deleted. The mapping stays in the
  spec's Notes and in this step's parent commit, for TCW-116 (Step 16).
- The tests whose subject was a refusal inside `projects:` (TCW-107's locator
  refusals in `tests/test_manifest_cli.py`, the one-parent rule, the
  `connected-projects` rename message) now meet Design 3.5's refusal first;
  each is rewritten as a test of that refusal or removed as a duplicate of
  AC 8's, and listed with Design 3.5.

**New** `tests/test_parent_links_static.py`:

- AC 8's search, by rule rather than by a list of exceptions (the review's
  M1). It parses each file under `tests/` and finds every string constant
  (alone, in `dedent(...)`, or as the literal parts of an f-string) that
  holds a top-level block `projects:` key, and every dictionary literal
  whose `"projects"` value has a `parent`, `children` or `upstream` key. A
  text is a **configuration text** when it is the text argument of a
  configuration writer (the names of commit 1) or holds a top-level `id:`
  key; a manifest holds neither (`write_manifest`'s arguments, and manifest
  texts, which never carry `id`), so manifests are left out by that rule.
  Any configuration text or dictionary found fails the test, except in the
  Design 3.5 refusal tests, each named in the test.
- `grep -rn "declared_upstream_ids\|_upstream_only\|def entry\|translate_projects" tcw/`
  finds nothing.
- AC 28: none of the names of spec Problem 7, nor `ProjectRegistry.parent`,
  `declared_parent_id` or `declared_upstream_ids`, is defined anywhere in
  `tcw/`, checked by parsing each module's syntax tree for definitions.

**Proves it**, each result recorded in the implement round:

1. The full suite passes, and the set of passing test IDs equals Step 8a's,
   apart from the refusal tests rewritten or removed above, each listed.
2. **Mutation checks**, with the search turned off as in Step 8a, each aimed
   at a choice the rewrite made (the review's S3), each a temporary change to
   production code that is reverted:
   - (i) `parse_children` returns no IDs: every converted test that asserts a
     child or a descendant goes red;
   - (ii) every link's `inherit` forced to `none`: every test that depends on
     inheriting through a link (an `extends` that resolves, an inherited
     entry) goes red;
   - (iii) every link whose `inherit` is not `all` dropped (the ones the
     rewrite made from upstreams and from `extends`): every test that
     depends on one of them goes red;
   - (iv) every parent list reversed: the tests that assert a load order of
     several parents go red (a fixture with one parent cannot notice, so
     this one is expected to be narrow; the count is recorded).

   A mutation that makes `parse_parents` return no links at all is not used:
   every listed child would then fail the name-back rule, and nearly every
   connected test would go red for that one reason, whatever it asserts.
   For (i) to (iii), every converted file holding such a test is confirmed
   to have at least one red test; for each of the four, the number that went
   red is recorded, and the failure reasons of at least ten red tests across
   different files are read and confirmed to be the changed relation, not an
   unrelated crash.
3. **The inventory**: against Step 8a's, no test ID disappeared, and no
   test's count of `assert` statements and `pytest.raises` blocks dropped,
   except those listed above with their reason.

## Step 9 — personal children

Spec Design 2.1-2.4 and 2.6.

**Tests first**, in `tests/test_parent_links_cli.py` and
`tests/test_parent_links.py`:

- AC 5 (the committed and personal lists combined, `personal` flags in Step
  12's JSON tested there; here the plain listing and
  `TCW_NO_PERSONAL_CONFIG=1`), `children:` in the user-wide file refused
  naming that file, `children: [a, a]` in either file, `children: null` in the
  personal file (`null has no meaning in a personal file`).
- AC 6's personal half.
- AC 7: `descendants()` from `ws` is `[a, b]` and from `a` is `[kid]`.
- AC 24: a real git repository with a linked worktree (`git worktree add`,
  never a simulated one), the main checkout's personal file listing `b`.
- AC 32: `tcw work advance <item> --dry-run` gives the same exit code and the
  same standard error with and without `TCW_NO_PERSONAL_CONFIG=1`.
- `tcw config show --origin` lists `children` with the committed entries from
  `.tcw/tcw-config.yaml` and the additions from `.tcw/tcw-config.local.yaml`
  (choice 6).

**Changes**

- `tcw/config.py:369-405` (`_allowed`): a key path allowed in the project's
  personal file only, `LOCAL_ONLY_KEYS = ("children",)`, beside
  `PERSONAL_KEYS` (`:44-51`). In the `local` layer it is kept, and `null` gets
  the existing null rule (`:378-381`); in the `user` layer it is a problem
  naming that file: `children may be listed only in this project's own
  files, .tcw/tcw-config.yaml or .tcw/tcw-config.local.yaml; the user-wide
  file applies to every project`. The docstring of `PERSONAL_KEYS` says why
  `children` is not in it (Design 2.2).
- `tcw/config.py:485-526` (`_merge`): `children` from the `local` layer is the
  lower list followed by its IDs the lower list does not hold, each entry's
  origin kept (choice 6).
- `tcw/store/project.py`: the active project's personal list is read with
  `personal_file(root, LOCAL_CONFIG_NAME)` (TCW-107 Step 6), unless
  `personal_files_skipped()`, through `_read_text`, parsed with
  `parse_children`; its problems are graph problems against that file. Its IDs
  that the committed list does not hold are added after it (Design 2.1), and
  recorded as personal for Step 12. No other project's personal file is read
  (Design 2.4).

**Proves it:** the tests above; `tests/config/` (the personal-file suites);
the full suite.

## Step 10 — what reaches a project for an axis, and exit 7

Spec Design 5, 6.1, 6.2, 6.4 and 6.6's third bullet.

**Tests first**, in `tests/test_parent_links.py`:

- AC 17 at the registry level (`sources` of each axis).
- AC 18: `sources("taxonomy")` is `[core, app]` and raises nothing;
  `load_order()` is `ws, core, app`, its `missing` holding `ws`.
- AC 19's first part: `InheritedUnavailable`, code 7, its message containing
  `'app' inherits its taxonomy from project 'core', which is not on this
  machine:` and `not on this machine` once; with `app`'s manifest entry for
  `core` giving a repository, `tcw project provision core`.
- AC 20: `sources("capabilities")` raises naming `core`.
- AC 26's `sources("config")` is `[app]`.
- AC 31: `sources("taxonomy")` raises with `'app' inherits its taxonomy
  through project 'lib', whose parents could not be read`; with
  `app: [{id: lib, inherit: none}]`, `[app]` and no error.

And in `tests/test_parent_links_cli.py`: AC 18's and AC 20's `tcw work list`
and `tcw validate` (one `unresolved` finding naming the project, with row
(a)'s text), AC 26 with two real git repositories (repository B cloned inside
A and ignored by it; `ws`'s manifest places `app`, since the search never looks
downwards; then a separate clone of B alone), and AC 31's first three
sentences.

**Changes**

- `tcw/store/base.py`: concrete `ProjectRegistry.sources(axis,
  project_id=None) -> list[Project]`: the load order filtered by `passing`
  (Step 2), ending with the project. When a project that passes the axis is
  missing or unreadable, raises `InheritedUnavailable` for the first such in
  load order, with Design 6.2's first or second message. The text after the
  first message's colon comes from a concrete hook `absent_note(project_id)`
  (default: `project '<id>' is not available here`), and the second
  message's problem from `link_problem(project_id)`.
- `tcw/store/project.py`: `absent_note` returns a new field of TCW-107's
  `UnreachableProject`, `remedy`: the part of Design 6.2's sentence after its
  colon (where the deciding entry places the project, and `tcw project
  provision <id>` when it gives a repository, or "add an entry"), which this
  step stores on its own where TCW-107 renders the sentence, with `message`
  then built from the lead and `remedy`. So nothing parses presentation text
  (the review's S9). `link_problem` returns the recorded problem, naming the
  file and key.
- `LoadOrder.missing` and `unreadable` are filled for every caller (they were
  computed in Step 7 for the order; the AC 18 and 20 tests read them here).

**Proves it:** the tests above; the full suite. Nothing outside the tests
calls `sources` until Step 11 (`extends`) and TCW-109 and TCW-112.

## Step 11 — `extends` is held to the parent links

Spec Design 3.6 and 6.3, and Design 6.5 row (c).

**Tests first**, in `tests/test_parent_links_cli.py`:

- AC 19's `extends` sentences: `tcw taxonomy list` in `app` exits 7 with the
  message of Step 10; `tcw validate` exits 0 with one `unresolved` finding
  naming `core` that contains both `could not check what it passes down to
  'app'` and `could not check the taxonomy inherited from it` (spec Design
  6.5's rule), and no error. The project's own description holds a `tcw://` link to one of its
  own capabilities, so that every store `tcw validate` opens on the way is
  covered, not only `_run_check`'s.
- The three refusals of AC 19 (`other` outside the family; `core` behind
  `inherit: none`; `kid`, a descendant), each `tcw taxonomy list` exit 1 and
  a `tcw validate` error whose message contains `does not inherit its
  taxonomy from it` and `parents:`; `tcw taxonomy extends add other` exits 2
  with the same message and leaves the file unchanged byte for byte. The same
  three for `capabilities.extends`.
- **When what lies above is unknown** (spec Design 3.6; AC 19's last
  sentences): `app: [lib]` with `lib` not on this machine and
  `taxonomy.extends: [core]`: `tcw taxonomy list` exits 7 with Design 6.2's
  first message naming `lib`; `tcw validate` exits 0 with one `unresolved`
  finding naming `lib` that holds row (a)'s and row (c)'s suffixes, and no
  error; with no `extends`, `tcw taxonomy extends add core` exits 7 and the
  file is unchanged byte for byte. The same with `lib` unreadable (Design
  6.2's second message, row (d) then (c)).
- **A project outside the family** (spec AC 9's last sentences, Design 4.6;
  the review's M4): `ws` lists `a` and `b`, both name `ws`; `b: [ws, bp]`,
  `bp` here, `b` holding `taxonomy.extends: [bp]` and its own term `t`. In
  `a`, `tcw taxonomy show b.taxonomy/t` exits 0 and prints the term; from
  `a`'s registry `get("bp")` is `None`. This is the case where TCW-110's
  `Locator.read` opens `b`'s store from `b`'s root and that store resolves
  its `extends` on the command's one registry; it also covers, through
  `_extended_component_stores`, the rule TCW-110's handoff (item 4 on the
  ticket) asks for in `tcw/locate.py` (`read`, `find_tree`), the stores'
  `_found` and `route_capability_path`: each reaches an inherited object
  only through the stores this step opens, so the passing set decides for
  all of them. Step 0 re-reads those four on the merged tree and adds a test
  for any that resolves an `extends` ID without going through
  `_extended_component_stores`.
- **The federation cycle** (`test_check_federation_cycle`, as Step 8a left
  it): rewritten to assert that `b`'s `extends_add("a")`, `a` being `b`'s
  descendant, exits 2 with Design 3.6's message; listed with Design 3.6. The
  cycle check in the capabilities store can no longer fire (an `extends`
  names only an ancestor, and ancestors have no loop); it stays until
  TCW-112 removes `extends` (Step 16).

**Changes**

- `tcw/store/fs.py:991-1075` (`_extended_component_stores`): asks the
  command's registry, through the store's `Locator` (TCW-110 Step 7), for the
  projects that pass the store's axis (`config` never; `taxonomy` or
  `capabilities` by the store) to the store's own project (`project_id`,
  TCW-110 Step 6), not a registry opened at `project_root` (`:1010`). For each
  `extends` ID: not passing, while some project that passes the axis is
  missing or unreadable → `InheritedUnavailable` for the first such in load
  order (exit 7, Design 3.6's "when what lies above is unknown"); not
  passing otherwise → the `ValueError` of Design 3.6 (exit 1); passing and
  missing or unreadable → `InheritedUnavailable` (exit 7, Design 6.3),
  replacing the message at `:1013-1022`; otherwise the store is opened as
  now. The store's own project may be outside the family (Step 7b's
  `load_order` for any located project), so the passing set is always the
  store's project's, never the active project's.
- `tcw/store/fs.py:1963-1981` and `:2718-2736` (`extends_add`): the same
  three-way decision before anything is written: not passing with an
  unknown above → `InheritedUnavailable` (exit 7); not passing → Design
  3.6's message as a `UsageError` (exit 2), replacing "is not registered";
  the file is unchanged in both.
- `tcw/validate.py:241-263` (`_run_check`), and every other place Step 0's
  search found where `validate` opens a tree store: an `InheritedUnavailable`
  is collected rather than raised, into a list `validate()` (`:384`) takes as
  a new keyword, `unavailable`. `_cmd_validate` passes it, and adds row (c),
  `; could not check the <axis> inherited from it`, to the finding Step 7d
  makes for that project, or makes one when there is none. Another caller of
  `validate()` (`tcw/serve/records.py:50`) passes no list, and then
  `_run_check` returns an `unresolved` finding itself.

**Proves it:** the tests above; `tests/test_capabilities_federation.py`,
`tests/test_taxonomy.py`, `tests/test_capabilities.py`; the full suite.

## Step 12 — `tcw projects list --json`, and the load-order warning

Spec Design 4.5 and 8.2.

**Tests first**, in `tests/test_parent_links_cli.py`: AC 1 (each `inherit`
row), AC 5's `personal` flags, AC 6's `present: false`, AC 12 (`load-order-
warning` null and no `tcw validate` warning), AC 13 (the warning in
`tcw validate` at `.tcw/tcw-config.yaml` and in `load-order-warning`, the same
text), AC 18 and 20 (`load-order-complete: false`), AC 21 and 33's
`read-only` values, AC 23 (exactly the five top-level keys) and AC 27: a
project with no `parents:` or `children:` next to another project, whose
`tcw work list`, `tcw projects list` and `tcw validate` print what they print
for the same project alone in an empty folder, with one row, `load-order`
its own ID, `load-order-complete: true`, `load-order-warning: null`, and
`_read_text` (TCW-107's counting) never reading the other project's
configuration.

**Changes**

- `tcw/projects_cli.py`: each parent row adds `inherit`, its axes in `AXES`'
  order (`[]` for `none`); each child row adds `personal`; every row but the
  current one adds `read-only` (`read_only_reason` is `None` → false, a
  reason → true, a project not here → `null`). `_list` (`:54-64`) prints
  `print_json(None, {"projects": rows, "load-order": [...],
  "load-order-complete": ..., "load-order-warning": ...})`, so `schema` is the
  value `print_json` writes (2, after TCW-110). The `--json` help (`:76-77`)
  names the new keys. The plain listing is unchanged.
- `tcw/cli.py`, `_cmd_validate`: when `registry.load_order().warning` is set,
  a `warning` finding with it, `where` the active project's
  `.tcw/tcw-config.yaml`. No other command prints it (Design 4.5).

**Proves it:** the tests above; `tests/test_projects_list.py`,
`tests/test_cli_contract.py`; the full suite.

## Step 13 — the web app shows what the CLI decides

Spec Design 8.5, AC 33.

**Tests first**

- `tests/serve/test_work_read.py:93` and a new case in
  `tests/serve/test_work_write.py`: in AC 21's layout, `tcw serve`'s project
  answer has rows for `lib` with `readOnly: true` and for `ws` with
  `readOnly: false`, and no row has an `upstream` key; the same values as
  `tcw projects list --json`'s `read-only`.
- `web/client/src/ui/work-forms.test.tsx`: the create form's target for a
  project with `readOnly: true` reads `lib (read-only from here)`; the mocked
  refusal at `:204`, `:229` says `q is read-only from here`.

**Changes**

- `tcw/serve/work.py:143-148` (`_projects`): `"readOnly": row["read-only"]`
  in place of `"upstream"`.
- `web/client/src/model/types.ts:30-31` (`TConnectedProject`): `readOnly:
  boolean | null`, its comment "creating into it is refused, as the CLI
  decides"; `web/client/src/ui/work-forms.tsx:587-588`: `${id} (read-only
  from here)`; `web/client/src/test-fixtures.ts:57`: `readOnly: false`.
- `pnpm build`.

**Proves it:** the tests above; the full suite; the web gate.

## Step 14 — this repository's records

In this repository's 3.x-format ledgers, with the lifecycle CLI (the header),
as TCW-107 Step 11 and TCW-110 Step 16 do:

- New capabilities, with `tcw capabilities add`, status `Supported`:
  `cli/name-a-projects-parents`, `cli/list-a-projects-children`,
  `cli/read-ancestors-in-one-load-order`, each with the spec's sentence, and
  `Subject` naming the new terms.
- Changed, the `description.md` of each capability in the item's
  `capabilities.yaml` `changed:` list, with the sentence the spec's
  Capability changes gives it (`cli/rely-on-one-output-contract`'s table was
  already changed in Step 3).
- New taxonomy terms `parent-link` and `load-order` (`tcw taxonomy add`),
  relating to `project`; the descriptions of `docs/taxonomy/project/`,
  `project-registry/` and `personal-configuration/`.
- Removed: first every reference to them is changed
  (`docs/taxonomy/project-registry/meta.yaml` relates to `upstream-project`;
  `docs/capabilities/cli/list-connected-projects/meta.yaml` names it; the
  descriptions found by `grep -rln "upstream-project\|read-from-an-upstream-project" docs/capabilities docs/taxonomy`),
  then `tcw capabilities rm cli/read-from-an-upstream-project` and
  `tcw taxonomy rm upstream-project`.

The descriptions are Markdown outside `docs/work/`, so
`tests/test_documented_cli_surface.py` checks every `tcw …` command they put
in backticks; they never put `tcw project provision` in backticks (not yet a
command).

**Proves it:** with the lifecycle CLI, from the worktree: `tcw validate`, and
`tcw work advance TCW-108 --dry-run` at the end of implement (the records
gate); `tests/test_documented_cli_surface.py` in the full suite.

## Step 15 — Documentation Sync

Each documentation entry, evaluated with the `documentation-sync` skill:

| Entry | Fires? | Answer |
| --- | --- | --- |
| `README.md` [Public-API] | yes: how projects are connected (`projects:` is gone), upstream projects, exit 7 | Deferred to TCW-117, which rewrites the user-facing documents for 4.0 in one pass (spec Non-goals); what it must say is in Step 16's note. |
| `docs/guide/jira.md` [Jira-Change] | yes: filing into a project not on this machine through a `jira` block goes (Design 7.2); `:245` names an upstream project | Deferred to TCW-117, with the two facts in Step 16's note. |
| `docs/guide/<topic>.md` [Guide-Topic-Change] | yes: `docs/guide/multi-repo.md`, `docs/guide/taxonomy-and-capabilities.md`; and `docs/guide/cli.md`'s exit-code table | `docs/guide/cli.md`'s table changed in Step 3 (spec Design 8.3 makes it this item's); the rest deferred to TCW-117 (spec Notes list). |
| `docs/release-notes/upcoming/<folder>.md` [Public-API] | yes | Written, in plain language: a project names its parents under `parents:`, in order, and says what each passes down; it may list its children, in its shared or personal file; how the order of ancestors is decided and the warning when it cannot be kept; a project that is missing or broken stops only a command that needs what it passes down, with exit code 7, and `tcw validate` reports it as "could not check"; `projects:` and upstream projects are gone; `extends` may name only a project a parent link passes that axis from; a sibling can no longer be written into; the web app marks a project that is read-only from here. |
| `docs/changelogs/upcoming/<folder>.md` [Any-Code-Change] | yes | Written, under Added (`tcw/store/links.py`, `ParentLink`, `LoadOrder`, `load_order_of`, `find_loop`, `passing`, `ProjectRegistry.parents`, `load_order`, `sources`, `link_state`, `InheritedUnavailable`, exit 7, the `--json` keys, `readOnly`), Changed (the walk, TCW-107's lookup order, `ancestors`, `descendants`, `get`, `projects`, `read_only_reason`, `_extended_component_stores`, `extends add`, `_cmd_validate`'s findings, `_allowed` and `_merge` for `children`, `unreachable()` keeping one record per project), Removed (`projects:`, the upstream relation and its bookkeeping, `parent()`, `declared_parent_id`, `declared_upstream_ids`, `entry()`, `ConnectedProject`, `parse_connected_entry`, the `jira` block path, the eleven single-parent helpers, `_validate_reciprocity`, `_validate_cycles`) and Internal (the fixtures rewritten to `parents:` and `children:`, `connect_projects` and `connect()` with `inherit`, the static guard, the property test against Python's own C3). The reader's temporary translation of `projects:` is added and removed within this item, so it is not listed. |
| `skills/<component>/SKILL.md` [Skill-Driven-Component] | yes: the exit-code table agents read; `skills/work/SKILL.md:103-115` ("Another project's exit codes": the `jira` block exiting 0, filing into an upstream, and the advice on exit 5, which should also cover exit 7); `skills/taxonomy/SKILL.md:108-109` and `skills/capabilities/SKILL.md:120-121` (`extends` may name "a parent, a child, or an `upstream`") | `skills/work/references/commands.md` changed in Step 3 (spec Design 8.3). The three `SKILL.md` passages wait for TCW-117, decided by the dispatching session on 2026-10-22 and recorded in the spec's Non-goals: nothing ships between this item and the 4.0 release, and TCW-117 lands before TCW-118. The exact text is in Step 16's note to TCW-117. |
| `skills/configure/references/<document>.md` [Configuration-Key-Change] | yes: `parents:`, `children:` (and the personal file), `projects:` gone, `extends` held to the links; `projects.md` | Deferred to TCW-117. |
| `docs/use-cases.md` [Project-Setup-Change] | yes: UC-2, UC-3, UC-4, UC-6, S-6 | Deferred to TCW-117, with the spec Notes' list. |

The two `upcoming/` files are named
`TCW-108-tcw-4-0-parent-links-per-parent-inheritance-and-the-load-order.md`,
and are formatted with `prettier`.

## Step 16 — notes for the later children

Comments the dispatching session posts (the text is in the implement round),
the spec's handoffs (Notes) plus what planning added:

- **TCW-109:** the spec's handoff as written; `sources("config")` and
  `ParentLink.inherit` are the inputs; `children` is in `LOCAL_ONLY_KEYS`, not
  `PERSONAL_KEYS`, and its merge in `_merge` (Step 9); the conflict the spec
  names about `work.backend` and `work.tags`.
- **TCW-111:** its fixtures cannot write `projects:`: the reader refuses it
  (Step 8b) and `tests/test_parent_links_static.py` fails on one; write
  `parents:` and `children:`, or call `connect_projects(root, relation, *ids,
  inherit=...)` (Step 8a); the spec's AC 15 conversion.
- **TCW-112:** `_extended_component_stores` asks the registry's `passing`
  set of the store's own project, which may be outside the family (Step 11),
  and is what it replaces; `sources(axis)`; Design 4.8 with AC 11's shape as
  a test. The capabilities store's federation cycle check can no longer fire
  once `extends` names only ancestors, and goes with `extends`.
- **TCW-113:** `ancestors()`, `descendants()`, `declared_child_ids()`,
  `load_order(id)` for a descendant; `InheritedUnavailable` reaches the web
  app as an HTTP 500 (choice 7).
- **TCW-114:** `read_only_reason`, the `read-only` row field and `readOnly`
  are interim (Design 7.1, 8.2, 8.5).
- **TCW-115:** `tcw project info` prints what Step 12 puts in
  `tcw projects list --json`.
- **TCW-116:** Step 4's `translate_projects` in `tcw/store/links.py` was the
  spec's mapping, with tests in `tests/test_projects_translation.py`, both
  deleted in Step 8b (the commit before it holds both). It refused what
  TCW-107's reader refused, and left alone an `extends` naming a listed
  child; Step 8a inverted those by hand (the extended project made a parent
  passing the axis, the child link dropped from both files, since keeping it
  is a loop), which `tcw migrate` must do too, and report.
- **TCW-117:** what each deferred document of Step 15 must say:
  `README.md`, `docs/guide/multi-repo.md`,
  `docs/guide/taxonomy-and-capabilities.md` and
  `skills/configure/references/projects.md` (parent links, `inherit`,
  children in either file, the load order and its warning, no `projects:`
  and no upstream, `extends` held to the links); `docs/guide/jira.md` (`:245`'s
  upstream; filing through a `jira` block is gone); `docs/use-cases.md` as the
  spec's Notes list; and the three skill passages Step 15 names:
  `skills/work/SKILL.md:103-115` (filing into a project not on this machine
  exits 3 whatever its entry says, since the `jira` block is gone; filing
  into a project reached through a parent that does not list the child exits
  3 as read-only from here; and "On exit 7, report which project the command
  needs and pass on how to fetch it; do not retry"),
  `skills/taxonomy/SKILL.md:108-109` and `skills/capabilities/SKILL.md:120-121`
  ("A project may inherit the taxonomy of an ancestor whose parent links pass
  `taxonomy`", and the same for `capabilities`, until TCW-112 removes
  `extends`).

## Step 17 — the suite as CI runs it

Spec AC 34, done locally as TCW-110 Step 19 does, since CI does not run on
`v4`: bare `.venv/bin/pytest` from the worktree's root, never `python -m
pytest`; `pnpm install --frozen-lockfile` and `pnpm check:build`; and beyond
CI, `pnpm test`, `pnpm exec tsc --noEmit`, `pnpm lint` and `pnpm exec
prettier --check` over every file this item changed or created that
`.prettierignore` does not exclude. Not `pnpm typecheck`, whose
repository-wide `prettier --check .` spec AC 34 excludes. A failure is fixed
in the step it belongs to, not with a skip.

## Verification the tests cannot do

- **The QA plan's scenarios** (the ticket's QA plan comment, sections 1-5 and
  the two-repository check) are run by hand at qa with `.venv/bin/tcw` in
  throwaway folders under the scratchpad, with the current folder set there,
  never inside the worktree (header).
- **The web form in a browser** (QA 5.4): `tcw serve` on a scratchpad
  project, in the dedicated Claude Chrome profile, never the default one.
- **The released 3.x CLI still reads this repository** after Step 14 changes
  the ledgers: `tcw work show TCW-108` and `tcw validate` with the lifecycle
  CLI, `which tcw` checked first.
- **The property test's coverage** is limited to graphs of eight projects;
  that bound is a choice, stated in the test, not a proof.

## Self-review against the spec

| AC | Step |
| --- | --- |
| 1 | 1 (parsing), 12 (rows) |
| 2 | 1 (parser), 7 (commands) |
| 3 | 7 |
| 4 | 7 |
| 5 | 9 (listing, refusals), 12 (`personal`) |
| 6 | 7 (committed), 9 (personal), 7d and 12 (absent: finding, `present: false`) |
| 7 | 9 |
| 8 | 8b (refusal, the static test, the `grep`), 8a (no fixture writes `projects:`) |
| 9 | 7 (registry, listing, `tcw work show`), 11 (a project outside the family with its own `extends`) |
| 10, 11, 12, 14 | 2 (function, and AC 14's two failing merges), 7 (registry), 12 (12's warning) |
| 13 | 2, 7 (`tcw work list` silent), 12 (`tcw validate`, JSON) |
| 15 | 2 (messages), 7 (graph problems, exit codes) |
| 16 | 7 |
| 17 | 2 (`passing`), 10 (`sources`) |
| 18, 20 | 7 (load order), 10 (`sources`, findings), 12 (`load-order-complete`) |
| 19 | 10 (`sources`), 11 (`extends`, row c, `extends add`, and the case where what lies above is unknown) |
| 21 | 6 (no `jira` block), 7 (write rule) |
| 22, 29, 30 | 7 |
| 23 | 7 (plain listing), 12 (keys) |
| 24 | 9 |
| 25 | 3 |
| 26 | 10 |
| 27 | 12 |
| 28 | 5 (helpers), 7 (`parent`, `declared_parent_id`, `declared_upstream_ids`), 8b (the static test) |
| 31 | 7 (exit 1 cases, 6.6 bookkeeping, "named both" in an ancestor), 8b (`projects:` in an ancestor and in a descendant), 10 (`sources`, findings, exit 0 cases) |
| 32 | 9 |
| 33 | 12 (`read-only`), 13 (`readOnly`, the client) |
| 34 | 17 |

Every design rule of the spec's Coverage table falls in a step through these
criteria. 4.8 has no step, as the spec's Coverage table says (no axis applies
it in this item; Step 16 hands it to TCW-109 and TCW-112). Steps that trace
to no single criterion: 0 (the starting point), 4 (the translation the
fixtures are read through while they move), 8a (the rewrite, proved by an
unchanged passing set), 14 (records, the spec's Capability changes), 15
(documentation), 16 (handoffs).

**The suite at each step boundary**, each claim checked against what it
depends on:

- 1→2, 2→3, 3→4: runnable; each adds code nothing calls yet, or an error
  nothing raises yet.
- 4→5, 5→6: runnable; `projects:` still works, and each removal takes its
  only tests with it (Step 5: the helpers' tests rewritten on the registry;
  Step 6: the `jira` block's tests).
- 6→7: runnable by construction of Step 7: the registry and its callers
  change together, the reader translates every `projects:` whatever wrote
  it (manifests are never read by it), and 7f reads every failure; each is a
  behaviour the spec changed, since no fixture changed.
- 7→8a: runnable; Step 8a changes no production code, the translation still
  runs, and its first proof is that the passing set did not change and that
  no test relies on the translation any more.
- 8a→8b: runnable; Step 8b removes the translation that 8a's second proof
  showed unused, and changes the refusal tests whose subject it replaces in
  the same step. A fixture the local run skips would still fail at its next
  run; the static test finds it first.
- 8b→9: runnable; a personal `children` is refused as "a shared key" until
  Step 9 allows it, as it was before.
- 9→10: runnable; `sources` has no caller outside the tests until Step 11.
- 10→11: runnable. Step 11's refusal of an `extends` that does not pass the
  axis would break every test whose `extends` names a listed child or a
  3.x upstream with `inherit: none`; Step 0 listed each one and Step 8a
  inverted or gave it its `inherit`, each checked green under Step 7's rules,
  so the only tests Step 11 changes are the ones whose subject is the refusal
  (`test_check_federation_cycle`, listed). A store opened for a project
  outside the family gets a passing set from Step 7b's `load_order` for any
  located project, so TCW-110's full-identifier reads of a sibling
  (`tests/test_tree_full_identifiers.py`, `tests/test_locate.py`) do not
  fall into an undefined case.
- 11→12, 12→13: runnable; Step 12 adds JSON keys and one `tcw validate`
  warning, and the tests that pin the JSON's keys (`tests/test_cli_contract.py`)
  move with it; Step 13 changes the server's key and the client together.

## Spec defects found while planning

The first draft found four; the plan review agreed with each, and the spec
now settles them, so the plan no longer plans around them:

1. **AC 34** names the CI gate exactly (bare `pytest`; `pnpm install
   --frozen-lockfile` then `pnpm check:build`) and, from the root, `pnpm
   test`, `pnpm exec tsc --noEmit`, `pnpm lint` and `prettier --check` over
   the changed files, not `pnpm typecheck` (Step 17).
2. **Design 8.2** says `schema` is what `print_json` writes, 2 after TCW-110
   (Step 12).
3. **Design 6.5** states what one finding says when several rows apply
   (Step 7d, Step 11).
4. **Design 3.6** covers an `extends` ID when a project that passes the axis
   is missing or unreadable: exit 7, in `extends add` too (Step 11).

The same revision settled the review's three questions for the user, by the
dispatching session following the user's decision recorded in spec Design
6.6: `projects:` in an ancestor makes its links unreadable (spec 3.5, Step
8b); "named both as a parent and as a child" counts as a `children:` problem
(spec 6.6, Step 7b); and the skill passages wait for TCW-117 (spec
Non-goals, Steps 15 and 16).

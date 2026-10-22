# Plan — TCW 4.0: inheriting taxonomy and capabilities, and overrides by path

Child 7 of TCW-99. The spec (`spec/spec.md` beside this folder, 44
criteria) is accepted after review; AC 44 and the last paragraph of Design
4.5 were added after this plan's first review (the spec's Notes, "Revised
after the plan review"). "Design n" and "AC n" are the spec's; "TCW-1xx Step
n" is a step of that item's plan.

**Landing order.** TCW-106, TCW-107, TCW-110, TCW-108, TCW-111, TCW-109,
then this item, then TCW-114, TCW-113, TCW-115. This plan starts from the
state the six earlier items leave, as their plans describe them. TCW-109's
plan was revised alongside this one (`62d9eaba`), so this plan takes from it
only names and signatures (`known_keys()` in `tcw/config_keys.py`,
`ProjectRegistry.source_entries`, `ProjectRegistry.unavailable`), never
line numbers. Code citations are to commit `d2d02829` on `v4`, whose
`tcw/store/fs.py`, `tcw/store/base.py`, `tcw/work/gates.py`, the two axis
CLIs and `tcw/serve/` are identical to `67c4c15a`, the commit the spec cites
(`git diff --stat 67c4c15a d2d02829 -- tcw/` touches only `tcw/config.py`,
`tcw/store/project.py` and `tcw/work/config.py`, none of them cited here).
Most of what is cited is rewritten by TCW-108, TCW-110 and TCW-111 before
this item starts, so **Step 0 re-finds every citation** on the tree they
leave, and each step names the code by function as well as by line.

**Blockers.** TCW-108, TCW-111 and **TCW-109**: this plan uses TCW-109's
`known_keys()`, `ProjectRegistry.unavailable` and its unreadable-ancestor
rule, and lands after it. The dispatching session records TCW-109 on the
ticket as a blocker (`tcw work edit TCW-112 --blocked-by TCW-109`).

## How the steps are grouped

| Part | What | Steps | Ends with |
| --- | --- | --- | --- |
| 0 | the starting state, the inventory, the outcome record | 0 | nothing changed |
| 1 | the one combining function, and exit 7's third message | 1, 2 | suite green |
| 2 | inheritance from parent links; `extends` goes | 3, 4, 5a, 5b, 5c | suite green, a commit after each |
| 3 | overrides by path | 6, 7, 8, 9, 10, 11 | suite green after every commit |
| 4 | clashes, missing parents, unreadable sources, checks | 12, 13, 14, 15 | suite green, a commit after each |
| 5 | the gate, drift, the web app, `tcw project info` | 16, 17a, 17b, 18 | suite green |
| 6 | shipped text, the guard, records, notes, documentation, CI | 19-24 | the move to review |

28 steps in all. Steps 4, 6, 9, 10 and 11 are the **mass test
conversions**. Each is split from the behaviour change it serves, so that a
failure can only come from one of the two (TCW-107 Step 9, TCW-108 Steps
7-8b), and each uses all of the safeguards described under "The conversion
safeguards" below. **Every commit is green**: where a new check would fire
on fixtures not yet converted, the conversion is committed first and the
check after it (Steps 9, 10, 11).

**Which `tcw` drives this repository's lifecycle.** The `tcw` first on
`PATH`, the primary checkout's editable install of `main` (3.x), exactly as
TCW-111's plan header says (its plan.md:53-74), and for the same reason:
this repository's own `tcw-config.yaml`, `meta.yaml` and `item.yaml` stay in
3.x form until TCW-116. So:

- the 4.0 code is run only by the suite (projects under `tmp_path`) and in
  throwaway projects under the session's scratchpad with the current folder
  set there, never as `.venv/bin/tcw` from a folder inside the worktree;
- lifecycle commands for this item (`show`, `advance`, `comment`) use the
  `tcw` on `PATH`, checked first with `which tcw`;
- this repository's capability records keep `meta.yaml`, `id: cap-…` and,
  where they have it, every 3.x key, and are edited in that form (Step 21),
  because the lifecycle `tcw` reads them, and its records gate checks this
  item's `capabilities.yaml` against them.

**How the suite and this repository's ledgers stay green on `v4`.** Three
facts, each checked in Step 0 and again in Step 24:

1. No test runs the 4.0 code against this repository's `docs/taxonomy` or
   `docs/capabilities` through a store. The tests that read them read files
   by name (`tests/test_ledger_3_0.py:17-18`, `:31`, `:45-46`, `:52`, plain
   YAML reads of `meta.yaml`; `tests/test_repo_config_pair.py:20-45`, the
   two configuration files as YAML), and `tests/test_documented_cli_surface.py:145-147`
   runs `main([..., "--help"])` with `cwd=REPO`, which stops at argument
   parsing and opens no store. Step 0 re-runs the search in its wider form:
   every test file that takes a path from `Path(__file__)` (under any name:
   `REPO`, `ROOT`, `parents[1]`) and also opens a store or calls `main`
   with a current folder outside `tmp_path`; any new hit is added to this
   list.
2. **Four tests read this repository's Markdown with the 4.0 code**: the
   three shipped-text scans of Design 8.1
   (`tests/test_shipped_text.py:313-323`,
   `tests/test_docs_describe_3_0.py`, `tests/test_documented_cli_surface.py:238-247`),
   which check one direction only, that a command a document names exists;
   and **`tests/test_configuration_text_home.py`**, which runs the other
   way: its hand-kept `KEY_PATHS` (`:38-46`) lists `taxonomy.extends` and
   `capabilities.extends` (`:40-41`), and for each key requires exactly one
   heading in `skills/configure/references/*.md` and exactly one row in
   `personal.md`'s table (`:123-149`). So the documentation changes first
   (Step 5a, with the two keys leaving `KEY_PATHS` in the same commit), and
   the commands go after it (Step 5b): a document that no longer names a
   command that still exists passes all three scans, since the only reverse
   check, "a shipped verb must be documented", lists only `tcw work stage
   prompt` (`tests/test_documented_cli_surface.py:260`).
3. The records gate this repository's own lifecycle runs is the lifecycle
   `tcw`'s (3.x), reading 3.x records, so nothing this item changes in
   `tcw/work/gates.py` reaches it. Step 21 writes the records in 3.x form,
   and `tcw work advance TCW-112 --dry-run` with the lifecycle `tcw` is the
   proof.

## What this plan relies on

**From TCW-106 (on `v4` in part; its plan).** `.tcw/tcw-config.yaml`
(`SENTINEL`), `tcw-version` on every file, `tcw/project_files.py`'s
`version_problem` and `version_line` (rows a-d of TCW-106 Design 3.4), and
`tests/projectfiles.py`'s `write_config(root, text)` and
`write_config_file(path, text)` (TCW-106 plan, Step 3).

**From TCW-107 (its plan).** `project_folder` and the command's one registry
(Step 5); `tests/projectfiles.py`'s `write_manifest(root, entries)` and the
`tmp_path` guard in `tests/conftest.py` (Step 2); the conversion safeguards
of Step 9 (an inventory, the search turned off, a mutation check, a
mechanical commit apart from the hand edits).

**From TCW-110 (its plan).** `tcw/ids.py`'s `FullId`, `parse_full_id`,
`parse_stored`, `sort_input` (Step 1); `tests/fullids.py`'s `fid(project,
namespace, id_path)` (Step 3); `FsTreeStore.project_id`, `Term.owner` /
`full_id`, `Capability.owner` / `full_id`, the records' `full-id` and
`owner` keys and `"schema": 2`, `show`'s `owner:` line in place of
`origin:` (Step 6); `tcw/locate.py`'s `Locator.of(root)`, `read(full_id,
named_by)`, `owner_root`, `find_tree(store, namespace, text)` and
`find_tree_writable`, which refuses an owner that is neither the active
project nor one it extends with `belongs to project '<id>'; change it
there` (Steps 7, 8; its plan.md:785-787, :802-809); `resolve_address`
reading an object address through `Locator.read` (Step 10, its
plan.md:925-931); **the store lookups of Step 8**: `get_local(id_path)`
(the store's own project's raw entry, its plan.md:746-747),
`get_inherited(owner, id_path)`, `get_view(id_path)` on both tree stores
and declared abstract in `tcw/store/base.py`, and each store's
`_found(target: FullId | str)`, with `get` deleted in Step 11;
`_stored_ref(value, namespace) -> Outcome` for stored references, reading
through `parse_stored` and `Locator.read` (Step 9); `route_capability_path`
routing by full identifier, keeping rule 1 for an owner in `own.extends`
(Step 11, its plan.md:983-990). TCW-110's Step 11 moves the tests that
called `get` onto `get_view`, `get_local` or `get_inherited` (its
plan.md:1019-1021), so some tests call those directly (Step 0's list).
TCW-110's handoff to this item (its Step 17, plan.md:1303-1305): the
inherited-view rule lives in `find_tree`, `Locator.read`, `_found` and
`route_capability_path`, and the collision findings and the `overrides:`
pointer were kept for the 3.x override folders. Those four are what Steps
7, 8 and 16 replace.

**From TCW-108 (its plan).** `tcw/store/base.py`'s `load_order_of`,
`passing(axis, project_id, links) -> set[str]` and `LoadOrder` (Step 2);
`ProjectRegistry.load_order(project_id=None)` and `sources(axis,
project_id=None) -> list[Project]`, ending with the project, raising
`InheritedUnavailable` for the first missing or unreadable project that
passes the axis (Steps 7, 10); `tcw/errors.py`'s `InheritedUnavailable`,
code 7, carrying `project`, `axis` and `reason` (`"missing"` or
`"unreadable"`) (Step 3); `tcw validate`'s `unavailable` keyword and the
finding rows (a)-(d) of TCW-108 Design 6.5, with row (c) added to the
finding for the missing project (Step 11, plan.md:1268-1276);
`connect_projects(root, relation, *ids, inherit=...)` writing `parents:`
(Step 8a); `extends` held to the parent links by
`_extended_component_stores` asking the registry for the projects that
pass the store's axis to the store's own project, which may be outside the
family (Step 11, plan.md:1243-1262), and by `extends_add` (`:1263-1267` of
its plan); `test_check_federation_cycle` rewritten to assert Design 3.6's
refusal (Step 11, plan.md:1238-1242). TCW-108 leaves the web app answering
`InheritedUnavailable` with HTTP 500 (its choice 7, plan.md:150-153), which
Step 17a here replaces.

**From TCW-111 (its plan).** `tcw/object_folders.py`'s `STATE_FILES`,
`walk`, `object_paths`, `is_object`, `folder_parent`, `disagreement`,
`read_state`, `state_text`, `removal_blockers`, `shape_problems` (Step 1);
`tests/statefiles.py`'s `CAPABILITY_STATE`, `TAXONOMY_STATE`, `write_state`,
`write_state_data` and `read_state` (Step 3); `FsTreeStore._state(d)`,
`StateFileProblem` (exit 1), `FsTreeStore.unreadable`, which the listers
fill and each `check()` clears before a full listing, and the listing
commands printing each unreadable file on standard error and exiting 1
(Step 5, its plan.md:469-477); `_object_dirs` replacing `_all_meta_dirs`,
with the callers still separating 3.x override folders by their
`overrides:` key (Step 6, its plan.md:631-634); `resources/` for
attachments and for `prependedDocs` / `appendedDocs` (Step 7); `Term.parent`
and `Capability.parent`, `_CAP_STRUCTURAL` holding `parent` so that it is
never one of `Capability.fields`, and the interim `Refused` of `set
--parent` on an inherited capability (Step 13, its plan.md:1239-1257); row m
through `folder_parent` and `disagreement` (Step 14); taxonomy row k, an
`id` equal to the folder's name, with capabilities exempt (Step 5, its
plan.md:483-486).

**From TCW-109 (its plan as revised at `62d9eaba`; names and signatures).**
`tcw/config_keys.py`'s `known_keys()`, the table of keys TCW knows, which
lists `extends` under `taxonomy` and `capabilities`; the messages `no
configuration key is written` and `is a shared key`;
`ProjectRegistry.source_entries(axis, project_id=None, *, root=None)`, the
non-raising form of `sources` returning each gap's state;
`ProjectRegistry.unavailable(project_id, gap_id, axis, *, subject=None)`,
the one place an `InheritedUnavailable` message is built, which takes the
error's `reason` from `link_state(gap_id)` and the words standing for the
axis from `subject` (the axis name by default); a configuration
`InheritedUnavailable` having `axis == "config"`; and an ancestor whose shared
file cannot be read being unreadable in the `ancestor` role. TCW-109's
handoff to this item says the two `extends` entries come out of
`known_keys()` here.

## Choices this plan makes where the spec leaves room

1. **The store interface after this item** (`tcw/store/base.py`, both tree
   stores). Each of these is a question any store can answer by path and
   project, so each passes the litmus test as the spec's table does:
   - `own_paths() -> list[str]`: the id-paths of the project's own objects.
     Reads no other project.
   - `has_own(id_path) -> bool`: whether the project has an object of its
     own there (TCW-111's `is_object` in the files store). Reads no other
     project and no state file's contents.
   - `declaration(id_path) -> Term | Capability | None`: the project's own
     object read alone, with `partial=True` (Design 3.4). Reads no other
     project.
   - `get_local(id_path)`: the project's own object as the project sees
     it, combined over its sources (Design 3.1, second row). **This changes
     TCW-110's meaning** (the raw own entry): from Step 7 on, `get_local`
     builds the view. Every route by which a command that must not stop
     (Design 3.5) reaches an own object is moved off it in Step 13 and
     named there.
   - `get_view(id_path)`: the object at the id-path in the project's view
     (Design 3.1, first row), named by its chain's first member. Builds the
     view.
   - `chain(id_path) -> list[FullId]`: Design 2.1's chain at the id-path,
     nearest first, empty when nothing has an object there. Builds the
     view. `set` and `reset` need it to accept "the full identifier of an
     object in the chain" at any depth (Design 4.2, 4.3); `get_view` and
     `inherited_at` give only the first two members.
   - `inherited_at(id_path) -> FullId | None`: Design 2.7.
   - `view_warnings(id_paths=None) -> list[str]`: Design 2.5's warnings, in
     its order, for the given id-paths or the whole view.
   - `override_target(target) -> FullId` (capabilities) and
     `removal_target(target) -> FullId` (both): choice 9.
   - `get_inherited` is **deleted**: Design 3.1 has no row that reads one
     owner's object through another project's view, and its callers
     (`_found`, `Locator.read`, `route_capability_path`) move to `get_local`
     of the owner's store.
   `Term` and `Capability` gain `overrides: FullId | None` and `partial:
   bool = False`; `Capability` loses `id` (Step 10). `CapabilityDetail`
   gains `declared_description: str | None` (Step 17b).
2. **The combining function's shape** (Design 2.6). `combine(id_path,
   declarers, passes)` in `tcw/store/base.py`, beside `load_order_of`:
   `declarers` is the list of `(project_id, Declaration)` in the active
   project's load order for every source with an object at the id-path, a
   `Declaration` being `fields: Mapping` (the state file without
   `tcw-version` and `id`) and `description: str | None` (None: no
   description declared); `passes(a, b)` says whether `a` passes the axis
   to `b`. It returns a `Combined`: `chain` (project IDs, nearest first),
   `fields`, `description`, `declared_by` (for each list key and for the
   description, the project whose declaration supplied it, so the files
   store reads `resources/` from that member, Design 2.3), `overrides` (the
   second member's project ID or None) and `unused` (each unused declarer
   with its `W` and whether it is warned about). It also takes an
   `unreadable` set and reports a chain member in it (Design 1.3) rather
   than combining. It reads no file and knows no folder. `parent`, `name`,
   `kind` and the two docs lists are in `fields` for `combine` like any
   key; whether the files store then exposes them as `Capability.fields` is
   `_CAP_STRUCTURAL`'s business, a different question (Step 7).
3. **"Passes the axis to"** is `a in {p.id for p in registry.sources(axis,
   b)} and a != b`: TCW-108's `sources` already filters the load order by
   `passing`, so no second relation is written. For `b` outside the active
   project's family this is TCW-108 Step 7b's load order of any located
   project.
4. **Sources are opened as other projects' stores.** A source's store is
   opened from its own committed configuration through the command's one
   registry (`Locator.owner_root`, then `STORE_CLASSES[axis].open(root,
   as_other=True)`). `as_other=True` means the store is not the active
   project's: its file's `extends` key is not read or refused (Design 1.5,
   "in another project's file"), and it **never opens its own sources**:
   the active project's `sources(axis)` is already the whole flattened
   list, so a source store is asked only for its own declarations
   (`_declarations()`). Its own view is built only if a caller asks it for
   one, as `Locator.read` does for `show <owner's full id>` (Design 3.1,
   third row). Building that view needs the owner's own sources, so from
   Step 7 an `as_other` store's `_sources` is built on first use, from
   `_source_stores(axis)` over `registry.sources(axis, <its own project>)`;
   before Step 7 it has none (Step 3). The active project's store builds its
   sources when it is opened until Step 13 makes that lazy too.
5. **A body set to empty by the web app** (`update_capability`,
   `tcw/store/fs.py:3031-3074`). Today an override's cleared body deletes
   its `description.md` and a standalone object's is written empty
   (`:3058-3068`), which needs to know which it is. With Design 2.3 an empty
   declared description adds no text, exactly as one not declared, so the
   store always writes an empty `description.md` for a body set to `""`, and
   writes no `description.md` when no body is given and none exists. The
   combined body is the same either way, and Design 6.1 stays satisfied for
   an object that overrides nothing. No view is needed, as Design 4.2 asks
   of `set`. With Design 4.5's last paragraph the body sent is always the
   declared description (Step 17b), so this rule writes what the editor
   showed.
6. **`update_term`** (the web app's edit of a term, `:2124-2198`) on an own
   override writes in place, and checks the combined term (a Feature's
   vocabulary) before writing, as Design 4.1 asks of `add`: the combined
   declaration is computed with `combine` over the new own declaration.
7. **Record key order.** `overrides` follows `parent` in every record;
   `partial` follows it when present. `show` prints `overrides:` after
   `owner:` and `parent:` (Design 3.3).
8. **The interim between Step 3 and Step 7.** Step 3 replaces `extends` as
   the source of inherited stores while keeping the 3.x reading rules
   (override pointers, ambiguity, the prefix-free lookups TCW-110 left), so
   that Step 7, which replaces the reading rules, starts from fixtures that
   already inherit through parent links. A test whose outcome Step 3
   changes only because a middle project's 3.x override pointer is no
   longer applied in a lower project's view (sources are flattened, and a
   source store opens no sources of its own, choice 4) is marked
   `pytest.mark.xfail(strict=True, reason="TCW-112 Step 7: a middle
   project's override applies again once overrides combine by path")` in
   Step 3's commit, and the marks are removed in Step 7's. `strict=True`
   makes an unexpected pass a failure, so a mark cannot outlive the change
   that fixes its test, and Step 7's proof includes `grep -rn "TCW-112 Step
   7" tests/` finding nothing.
9. **Where a write's target is decided, and where the refusals live**
   (Design 4.2-4.4; the plan review's B4). `find_tree_writable` (TCW-110)
   refuses an owner the active project does not extend; once `extends` is
   gone that test means nothing, and `set core.capabilities/cli/x` must
   pass (AC 20, AC 24) while AC 21's and AC 25's must not. So from Step 8:
   - `FsCapabilitiesStore.override_target(target: FullId | str) -> FullId`
     answers, for `set` and `reset`, the active project's own full
     identifier at the id-path the input names, which may be an id-path,
     the active project's full identifier, or the full identifier of any
     object in that id-path's `chain()`. It decides in this order:
     1. the active project's own full identifier: accepted when the project
        has an object of its own there (`has_own`), else `NotFound` (exit
        4), as `show` of that identifier is (AC 26; spec 4.2 accepts only
        an own object, an id-path or a member of the chain);
     2. another project's full identifier naming a project that is not one
        of the active project's sources for the axis at all (TCW-109's
        non-raising `source_entries(axis)`, gaps included): `Refused` with
        Design 4.2's message, before any view or other store is read, so
        `set zz.capabilities/cli/x` exits 3 even when one of the active
        project's ancestors is missing (TCW-114 spec 1.1);
     3. an id-path at which the active project has an object of its own:
        that object, with no view (Design 3.5);
     4. otherwise the view is built: another project's full identifier
        not in the id-path's chain is `Refused` with Design 4.2's message,
        and an id-path nothing has an object at is `NotFound` (exit 4). With
        a source missing, this case is TCW-108's exit 7, which TCW-114 spec
        1.1 and 1.5 accept: whether the object is in the chain cannot be
        known without the view.
   - `removal_target(target: FullId | str) -> FullId` (both stores) answers,
     for `rm`, the active project's own full identifier when it has an
     object there (`has_own`, no view). Another project's full identifier
     is refused with Design 4.4's message **first, before any view or store
     is read**, so `rm core.capabilities/cli/x` exits 3 even when `core` is
     not on this machine (TCW-114's handoff of 2026-10-22 relies on this
     order; Step 13 tests it). The active project's own full identifier at
     a path where it has no object is `NotFound`, as in
     `override_target`. An id-path the view shows as another project's is
     refused with Design 4.4's message, and an id-path nothing has, or one
     the active project has no object at when the view cannot be built, is
     `NotFound` (Design 4.4).
   - `find_tree_writable(store, namespace, text, *, removing: bool) ->
     FullId` (`tcw/locate.py`) is `sort_input`, then `removal_target` when
     `removing`, else `override_target`; it no longer refuses anything
     itself, and what it returns is always the active project's own full
     identifier. `removing` has no default, so every caller says which rule
     it means; `removing=False` needs a capabilities store, since a taxonomy
     store has no `override_target` (the taxonomy's one caller is `rm`). The stores' `set`, `reset`, `remove` and `_write_target`
     call the same two methods, so the CLI, the web app and a test calling
     the store directly meet one rule and one message each.
   - `reset` of another project's full identifier that is not in the
     id-path's chain is refused with Design 4.2's message: the spec names
     what `reset` accepts (4.3) but not this refusal's wording, and 4.2's
     reason ("'<P>' does not inherit it") is the true one.
   So TCW-114 has exactly two refusal sites to reword (Handoffs).

## The conversion safeguards

Used by every step that changes many tests (4, 6, 9, 10, 11) and by the
two switches (3, 7). All scripts are one-off and kept in the scratchpad,
never in the repository.

- **The inventory** (TCW-107 Step 9, TCW-111 Step 4): `.venv/bin/pytest
  --collect-only -q` (every test ID), and from a script walking each test
  function's syntax tree, its count of `assert` statements and
  `pytest.raises` blocks. Taken in Step 0 and again at the end of each
  conversion step. Proof: no test ID disappeared and no count dropped,
  except the ones on the step's allowed list, each with its design rule.
- **Assertions unchanged across a mechanical commit.** The same script
  prints, per test function, `ast.dump` of every `assert` statement and
  `pytest.raises` call. For each mechanical commit, the dumps before and
  after must be identical, apart from the functions the script listed for
  the hand commit. So a weakened assertion (`assert x == "Supported"`
  turned into `assert x`) can only appear in a hand commit, where every
  changed assertion is listed with its design rule.
- **The outcome record and comparison** (TCW-108 Step 7, plan.md:819-832):
  `.venv/bin/pytest -q --junitxml=<scratchpad>/outcomes-step<N>.xml` from
  the worktree's root, bare pytest as CI runs it. `compare_outcomes.py
  <before.xml> <after.xml> <allowed.txt>` is written again from TCW-108's
  description if TCW-108's copy is gone: it exits non-zero, printing each
  offending ID, when an ID in `before` is missing from `after` and not in
  `allowed.txt`; an ID in both has a different outcome and is not in
  `allowed.txt`; an ID in `allowed.txt` is still present with its old
  outcome (the list must be exact, not a cover); or an ID in `after` has
  outcome `failed` or `error`. A new ID must be `passed`. Two differences
  from TCW-108's: an allowed ID may be one whose outcome is expected to
  stay `passed` with a rewritten assertion, listed with `assertion:` before
  the ID and checked against the inventory's per-test dumps instead; and an
  ID listed with `xfail:` before it must be `xfailed` in `after` (choice
  8). **The record is saved at the end of every step** from Step 0 on, as
  `outcomes-step<N>.xml`, so each comparison is against the step before it
  and any change of outcome belongs to one step.
- **A recording plugin** (TCW-108 Step 8a's work list): a pytest plugin
  given with `-p`, recording the running test
  (`os.environ["PYTEST_CURRENT_TEST"]`) each time a private hook in the
  code fires. Each step that uses one names its hook; the hook is a
  module-level `None` that the code calls when set, added in that step and
  deleted at the step's end.
- **A mutation check, per test**: the code under the converted tests is
  broken in the named way and the converted tests are run. Every converted
  test that asserts the converted behaviour must go red; one that does not
  is listed with the reason (for example, it asserts only an exit code
  that the broken code also gives), and the list is read. The failure
  reasons of at least ten red tests across different files are read and
  confirmed to be the broken behaviour, not an unrelated crash.
- **Commits per conversion**: a mechanical commit made by a script, then a
  commit of hand edits, so a reviewer can read each alone; where a check
  goes with the conversion, the check is its own commit, last.
- **Finding a failure list before the check exists** (Steps 10, 11): the
  check is written in the working tree, the suite is run once to record
  which tests it turns red, and the check is then set aside as a patch
  file in the scratchpad (`git diff -- <its files> > <scratchpad>/step<N>-check.patch`,
  then `git apply -R` of that same patch, which undoes only those edits;
  never `git stash`, whose stack other sessions share). After the
  conversion commits, `git apply` puts it back for the check's commit.
- **Every failure is read.** An assertion changes only where the spec
  deliberately changed the behaviour it checks (Risks, "Every federation
  fixture is written with `extends`"), and each such change is listed in the
  implement round with its design rule.

## Step 0 — start from what TCW-106 to TCW-109 left

No code changes.

1. `git log --oneline` shows each of TCW-106, TCW-107, TCW-110, TCW-108,
   TCW-111 and TCW-109 completed on `v4`, and `git status` is clean.
2. **Re-find every citation** of the spec and of this plan on the merged
   tree, by function name, and write the new line numbers into the implement
   round: `_extends_ids`, `_FederationWalk`, `_FederationCycles`,
   `_extended_component_stores` (as TCW-108 Step 11 left it),
   `_persist_extends`, `_extends_label` (and each caller:
   `_legacy_config_problems`, both stores' `__init__`, `_extends_ids`'
   callers, `_override_problem`), `_legacy_config_problems`, both stores'
   `__init__`, `_term`, `_capability`, `_compose_body`, `_apply_override`,
   `_override_index` (and each caller: `list_all`, `get`, `_status_is_local`,
   `reset`, `_write_target`, `get_capability_detail`), `_override_fields`
   (and its callers, `check` and the taxonomy's `_capability_referrers`),
   `_set_fields`, `_local_paths`, `_object_dirs`, `get_local`,
   `get_inherited`, `get_view`, `_found`, `get_by_id` (and its callers in
   `_override_problem`), `list_all`, `search`, `add`, `remove`, `reset`,
   `_write_target`, `_merge_meta`, `set`, `extends_add`, `extends_remove`,
   `_status_is_local`, `unreviewed_inherited`, both `check`s (the
   override-folder loop and the `missing id` / `duplicate id` checks
   included), `_override_problem`, `_referrers`, `_capability_referrers`,
   `_validation_resources`, `get_term_detail`, `get_capability_detail`,
   `update_term`, `update_capability`, `_mint_cap_id`, `_CAP_STRUCTURAL`
   (`tcw/store/fs.py`); `Term`, `Capability`, `CapabilityDetail`,
   `TaxonomyStore`, `CapabilitiesStore`, `load_order_of`, `passing`,
   `ProjectRegistry.sources`, `source_entries`, `unavailable`
   (`tcw/store/base.py`); `InheritedUnavailable` (`tcw/errors.py`);
   `find_tree`, `find_tree_writable`, `Locator.read`, `owner_root`
   (`tcw/locate.py`); `resolve_address` (`tcw/refs.py`); `_stored_ref`;
   `route_capability_path`, `_LedgerReader.capability`, `.removal`,
   `INHERITED`, `_READ_ERRORS` (`tcw/work/gates.py`); `_run_check`, the
   `unavailable` keyword and `_cmd_validate`'s row (c) (`tcw/validate.py`);
   `_record`, `_detail`, `_show`, `_drift`, the `extends` groups
   (`tcw/capabilities/cli.py`, `tcw/taxonomy/cli.py`); `jsonable`,
   `get_capability`, `create_capability`, `update_term`,
   `update_capability`, the `read_only` checks (`tcw/serve/records.py`);
   `error_answer` (`tcw/serve/server.py`); `CapabilityDetail` and the
   editor's draft and save (`web/client/src/model/types.ts`,
   `web/client/src/ui/app.tsx:620-650`, `:715-745`); `known_keys()`
   (`tcw/config_keys.py`). A name that no longer exists, or behaves
   otherwise than this plan assumes, is reported to the dispatching session
   before Step 1, and the affected step is rewritten in the round.
3. **Re-check what each earlier item says it left**: `extends` still
   exists, held to the links (TCW-108 Step 11); `get_inherited` is still the
   path by which `_found` and `Locator.read` reach an inherited owner
   (TCW-110 Step 8); `find_tree_writable` still refuses an owner not in
   `extends` (TCW-110 Step 8); the walk still returns 3.x override folders
   and the listers separate them by `overrides:` (TCW-111 Step 6);
   capabilities are exempt from row k (TCW-111 Step 5); `set --parent` on an
   inherited capability is refused (TCW-111 Step 13); `_CAP_STRUCTURAL`
   holds `parent` (TCW-111 Step 13). **And for TCW-109**: whether
   `known_keys()` is used for anything besides decoding environment
   variables, in particular whether TCW-109's loader reports a key in a
   file that the table does not list (as a problem, or by making the file
   unreadable in the `ancestor` role). If it does, Step 5c's refusal of
   `extends` in the active project's file must be raised before that
   report, and `extends` in another project's file must not make that
   project unreadable (Design 1.5, AC 15); the round says which held, and
   Step 5c is rewritten accordingly. A test is written for none of these:
   Steps 3-10 replace each.
4. **Lists**, each kept in the scratchpad and pasted into the round:
   - `grep -rln "extends" tests/` (31 files at `d2d02829`;
     `tests/test_taxonomy.py`, `tests/test_config_edit.py`,
     `tests/test_capabilities_federation.py` and
     `tests/test_config_edit_writers.py` hold most of the uses), sorted **by
     test function**, not by file, into: uses `extends` to connect projects
     (Step 4 converts it); tests `extends` itself (Steps 5b and 5c rewrite or
     delete it); uses the word as an arbitrary configuration key for the
     line editor (`tests/test_config_edit.py`,
     `tests/test_config_edit_writers.py`, whose subject is
     `tcw/store/config_edit.py`, a generic editor: left alone unless it
     calls a store); TCW-108's own tests of Design 3.6. Several files mix
     the first two classes (`tests/test_taxonomy.py`,
     `tests/test_capabilities_federation.py`), which is why the list is per
     function.
   - The 3.x override fixtures: `grep -rln "overrides" tests/` minus the
     registry's own "overrides" (`tests/test_project_overrides.py`,
     `tests/test_project_registry.py`, `tests/test_project_graph_paths.py`,
     `tests/test_remote_session_setup.py`, which mean `TCW_PROJECT_<ID>`
     overrides). At `d2d02829`: `tests/test_capabilities_federation.py`,
     `tests/test_override_references.py`, `tests/test_store_editor.py`,
     `tests/serve/test_records.py`, `tests/test_store_provisioning.py`,
     `tests/conftest.py`, `tests/not_ported.py`, plus every helper that
     writes an `overrides:` key (TCW-111 Step 5 converted their file names).
     Each is marked with its pointer's form: a bare `<id>` (12 writes at
     `d2d02829`, for example `write_cap(child, "ov/login",
     overrides="cap-aaa111", ...)`, `tests/test_capabilities_federation.py:106`)
     or `<alias>/<id>` (3), and whether its folder is the original's path,
     `<alias>/<path>`, or an unrelated path (`ov/login` for `base`'s
     `auth/login`). The pointer-subject tests (`dangling id`, `unknown
     alias`, `targets a local capability`, `ambiguous id`,
     `tests/test_capabilities_federation.py:160-200`) are marked apart.
   - The opaque ids: `grep -rlnE "cap-[0-9a-f]{6}|_mint_cap_id|get_by_id|\.id\b" tests/`
     (32 files at `d2d02829`), read to separate a capability's `id` from
     other `.id` attributes (a project's, a ticket's).
   - **Direct calls of the store lookups**: `grep -rn "get_inherited\|get_local\|get_view" tests/`,
     each sorted into: `get_inherited` (deleted in Step 7; moves to the
     owner store's `get_local`, through `Locator.read` or by opening the
     owner's store); `get_local` of an override (returns the combined
     object from Step 7); `get_local` or `get_view` of anything else
     (unchanged).
   - `AmbiguousRef`: `tcw/refs.py:122`, `tcw/serve/records.py:17`, `:143`,
     `tcw/store/base.py:30`, the store's callers (Design 3.6), and the
     tests: `tests/test_capability_ref_wording.py`,
     `tests/test_capabilities.py`, `tests/test_capabilities_rm.py`,
     `tests/test_refs.py`, `tests/test_capabilities_federation.py`,
     `tests/test_capabilities_reset.py`, `tests/test_tree_store_raises.py`,
     `tests/test_taxonomy.py`.
   - The record writers tests use for terms and capabilities (TCW-111 Step
     4's list: `write_cap`, `write_term`, `term`, `cap`, `_write_term`), with
     whether each writes `name` and a `description.md` (Step 11's input).
     `tests/test_capabilities_federation.py:28-39`'s `write_cap` already
     writes both.
   - **Every branch on `InheritedUnavailable.reason` or `.axis`**
     (`grep -rn "\.reason\b\|\.axis\b" tcw/`, each hit read to keep only
     those on this error): Step 2 adds the reason `"store"`, and TCW-109 has
     added the axis `"config"`, so each branch must say what it does with
     both. `_cmd_validate`'s row (c) is one (Step 3); any other is listed,
     and Step 3 handles it in the same commit.
   - The nested command groups the help walk sees
     (`tests/test_cli_help_standard.py:160` uses `"taxonomy extends"` as its
     proof that the walk sees one; Step 5b's input).
5. **The shipped-text sweep** of Design 8.1, run as the spec gives it, and
   `grep -rn extends skills/ agents/` for files that are not Markdown. At
   `d2d02829` it finds the passages Step 5a lists; any change since (TCW-108
   to TCW-111 may have edited some of them) is folded into Step 5a's list.
   Also `grep -rn "opaque\|overrides:\|must-be-inherited\|dangling" skills/ docs/guide/`
   for the passages that state the removed override rules without naming a
   removed command (Step 19's list).
6. The **inventory** and the **outcome record** `outcomes-step0.xml`, taken
   as "The conversion safeguards" says. The suite must be green; a red test
   here is reported, not fixed.
7. **TCW-115.** Whether `tcw project info` exists on `v4`
   (`grep -n '"project"' tcw/cli.py`). It decides Step 18.

**Proves it:** the round lists the re-found citations, the answers of point
3, the lists, the sweep's output, the inventory's size and
`outcomes-step0.xml`'s count of passed and skipped tests.

## Step 1 — the combining function

Design 2.1, 2.2, 2.3 (the description rule), 2.4, 2.5, 2.6; AC 9, 10, 11,
43 at the level of the function. The riskiest rule of the item, built alone
with no store around it, as TCW-108 built the load order (its Step 2).

**Tests first.** New `tests/test_combine.py`, on declarations given as
plain data (a load order, a mapping from project ID to its declaration at
one id-path, and the "passes the axis to" relation as a set of pairs):

- **The chain** (Design 2.1): `app` over `core` gives `[app, core]`; AC 9's
  shape (`bb` the parent of `cc` and `dd`, `ee: [cc, dd]`, `bb` and `cc`
  declaring) gives `[cc, bb]`, `overrides` `bb`, no unused declarer; AC 10's
  (`cc` and `dd` unrelated) gives `[dd]`, `overrides` None, `cc` unused with
  `W` = `dd`; AC 11's (`bb`, `cc` and `dd` declaring) gives `[dd, bb]`, `cc`
  unused, and `fields` with `Status` from `bb` and `Priority` from `dd`
  (`cc`'s `Status` not used); the active project declaring gives a chain
  starting with it and never names it unused; three levels (`app` over
  `lib` over `core`, all declaring) give `[app, lib, core]`.
- **Combining the fields** (Design 2.2): a value replaces; `null` removes
  (`Priority: null` gives no `Priority`); an absent key leaves; `Subject`,
  `relatesTo`, `vocabulary`, `prependedDocs`, `appendedDocs` are replaced
  whole (`[app.taxonomy/money]` over two entries gives exactly one);
  `parent`, `name` and `kind` combine the same way; `tcw-version` and `id`
  given in a declaration are not in `fields`; `declared_by` names the member
  that supplied each list key.
- **The description** (Design 2.3): the nearest member whose declared
  description is not empty or white space; an empty declared description
  and an undeclared one both fall through; none declared anywhere gives
  `None`; `declared_by["description"]` names the member used.
- **The warning** (Design 2.5): its exact text for a capability and for a
  term (`a name, a Status and a description`, `a name and a description`);
  ordered by id-path, then by `L`'s place in the load order; silenced when a
  member nearer than `W` that `L` passes the axis to has a complete own
  declaration (AC 43's `ee` with `name`, `Status` and a declared
  description, possibly empty); not silenced by an incomplete one (only
  `Status`), nor by a complete one that `L` does not pass the axis to (AC
  43's last sentence: `dd`'s complete object in AC 11's family).
- **An unreadable member** (Design 1.3): a declarer in `unreadable` that is
  a chain member makes the result unreadable, naming it; an unused declarer
  in `unreadable` only changes its place in the warning.
- **A property test**, as TCW-108's (its Step 2): 2,000 families of at most
  seven projects with random parent links and random declarations at one
  id-path, generated with `random.Random(112)`, the load order from
  `load_order_of` and the relation from `passing`. Rules checked for every
  family: the chain's members are declarers, in reverse load order; each
  member passes the axis to the one before it; no declarer that passes the
  axis to the chain's first member is left out of the chain unless a nearer
  member already covers it; every declarer is either in the chain or unused,
  never both; the active project, when it declares, is first and never
  unused; `combine` over a chain gives what folding its members' fields in
  load order gives. At least 10% of families must have an unused declarer,
  or the test fails rather than passing quietly.

**Mutation check**, recorded in the round: with "passes the axis to" taken
as "comes earlier in the load order" (folding every declarer, the rule the
user rejected for AC 11), AC 11's case and the property test go red, and
the failing family is read.

**Changes.** `tcw/store/base.py`, module level, beside `load_order_of`:
`Declaration`, `Combined`, `combine(id_path, declarers, passes, *,
unreadable=frozenset(), axis)` (choice 2), and `clash_warning(axis,
id_path, unused, winner, project)` giving Design 2.5's text. Nothing calls
them yet.

**Proves it:** the new test file and its mutation check; the full suite.

## Step 2 — exit 7's third message

Design 1.3's third message; AC 18's message at the level of the registry.
The message is built where TCW-108 and TCW-109 build the other two:
`ProjectRegistry.unavailable`, which TCW-109 makes the one place an
`InheritedUnavailable` message is built.

**Tests first**, beside TCW-109's tests of `unavailable` (Step 0 names the
file), with `core` present and readable: `registry.unavailable("app",
"core", "taxonomy", store_message="<msg>")` (the third argument is
`axis`) returns an `InheritedUnavailable` with code 7,
`project == "core"`, `axis == "taxonomy"`, `reason == "store"`, `detail ==
"<msg>"`, and the message `'app' inherits its taxonomy from project 'core',
whose taxonomy store cannot be read here: <msg>`; the two existing reasons
keep their messages, and their `detail` is None.

**Changes.** `tcw/store/base.py`, `ProjectRegistry.unavailable`: a
keyword-only `store_message: str | None = None`; when given, the reason is
`"store"`, set in place of the one `link_state(gap_id)` gives (the gap is
present and readable, so `link_state` would give none of its own), and the
message is Design 1.3's third, with `subject` standing for the axis as in
the other two. `tcw/errors.py`,
`InheritedUnavailable`: the reason `"store"` and a `detail` attribute
holding the store's own message, as data for `tcw validate` (Step 3), never
used to build the message. Nothing raises it yet.

**Proves it:** the tests; the full suite.

## Step 3 — inheritance comes from the parent links

Design 1.1, 1.2, 1.3 (a source's store that cannot be opened); AC 1, 2, 3,
4, 17, 18 (`tcw taxonomy list` exit 7, `tcw validate`), 19. `extends` is
still read and still held to the links (TCW-108 Step 11), but it no longer
decides which stores are inherited. The 3.x reading rules stay (choice 8).
Construction of the active project's stores stays eager in this step; Step
13 makes it lazy. A source's store opens no sources of its own (choice 4).

**Before the change**, a recording plugin is run over the full suite with a
hook `tcw.store.fs._on_inherit(axis, project_id, extends_ids, source_ids)`,
added to `_extended_component_stores` for this step: it records each test in
which a store's `extends` IDs differ from `sources(axis)` without the
project (a parent passing the axis with no `extends`, or a capabilities
store several levels down, which 3.x never flattened: `_inherited_stores`
exists only on the taxonomy store, `tcw/store/fs.py:1771-1783`). That list
is read test by test and becomes `allowed-step3.txt`, each ID with its
reason: Design 1.1 (more is inherited); `xfail:` for a middle project's 3.x
override pointer no longer applied in the active project's view (choice
8); or exit 7 now raised by a missing parent that passes the axis without
being in `extends` (TCW-108 Design 6.2).

**Tests first**, in new `tests/test_tree_inheritance.py` (CLI, projects
built with `write_config`, `connect_projects(..., inherit=...)` and
`write_manifest`, objects with `write_state_data`; none writes `extends`):

- AC 1 (lists both of `core`'s objects in `app`), AC 2 (each `inherit`
  form), AC 3 (two levels, and `lib`'s link with `inherit: [config]`), AC 4
  (`ws` with no store), AC 17 (`ws` with `inherit: none` not on the machine),
  AC 19 (`core` its own git repository with `capabilities.path: ledger`).
- AC 18's first sentence: a test that makes opening `core`'s taxonomy store
  raise `StoreNotProvisioned` (by declaring `taxonomy.repository` in
  `core`'s file with no checkout) gives exit 7 with `whose taxonomy store
  cannot be read here`; and AC 18's `tcw validate` sentence.

**Changes** (`tcw/store/fs.py`, `tcw/validate.py`):

- `_extended_component_stores` (`:991-1077`, as TCW-108 Step 11 left it) is
  replaced by `_source_stores(axis)`: for each project of
  `registry.sources(axis, self.project_id)` other than the store's own, in
  load order, the store opened as choice 4 says, keyed by project ID. A
  source whose store for the axis is neither present nor declared is left
  out (Design 1.2), replacing the `ValueError` at `:1070-1071`. A source
  whose store raises `StoreNotProvisioned` or `StoreDeclarationError`
  (`:1059-1069`) raises `registry.unavailable(self.project_id, <source>,
  axis, store_message=str(error))` (Step 2). `sources` raising
  `InheritedUnavailable` passes through.
- Both stores' `__init__` (`:1713-1727`, `:2237-2253`) set
  `self.extends = self._source_stores(axis)` when not opened with
  `as_other=True`, and `{}` when they are (until Step 7, which builds an
  `as_other` store's sources on first use): the dictionary keeps its name
  and shape for this step and the next, so every 3.x reader of it is
  unchanged. `extends_cycles` is always empty, since `sources` never loops
  (TCW-108 Design 4.7). The taxonomy store's `_inherited_stores`
  (`:1771-1783`) returns `self.extends` as it is: sources are already
  flattened.
- The `extends` key is still parsed by `_extends_ids` and held to the links
  by TCW-108 Step 11's check, which moves from `_extended_component_stores`
  into a small `_check_extends(axis)` called from `__init__`, so that its
  refusals keep their messages and exit codes until Step 5b.
- `tcw/validate.py`: `_run_check` already collects `InheritedUnavailable`
  (TCW-108 Step 11). `_cmd_validate`'s row (c) branches on `reason`: for
  `"missing"` and `"unreadable"` it is TCW-108's row (c), added to the
  finding for the missing project; for `"store"` it is a separate
  `unresolved` finding at the active project's `.tcw/tcw-config.yaml`,
  `could not check the <axis> inherited from '<M>': <detail>` (Design 6.5).
- The tests listed with `xfail:` get the `xfail(strict=True)` mark of
  choice 8, in this step's commit.

**Proves it:** the new tests; `compare_outcomes.py outcomes-step2.xml
outcomes-step3.xml allowed-step3.txt` exits 0 (the `xfail:` IDs
`xfailed`, every other ID `passed`), the list and the output in the round;
`tests/test_capabilities_federation.py`, `tests/test_taxonomy.py`,
`tests/test_capabilities.py`, `tests/test_parent_links_cli.py` green.

## Step 4 — the fixtures stop writing `extends` (conversion)

No production code changes. Every test on Step 0's "connects projects with
`extends`" list loses its `extends` lines and relies on the parent link it
already has (TCW-108 Step 8a gave each one `inherit` holding the axes it
extended).

**The work list.** The recording plugin is run with a hook
`tcw.store.fs._on_extends(path)`, called by `_extends_ids` whenever it reads
a non-empty `extends`; the tests it records are the ones still writing the
key. Tests skipped in the local run are caught by Step 20's static guard.

**Commit 1, mechanical.** A script walking each test file's syntax tree
removes, only inside the test functions and fixtures on Step 0's "connects
projects" list (by function, so a test whose subject is `extends` in the
same file is never touched), from every string constant passed to
`write_config`, `write_config_file`, `write_local_config` or TCW-108's
configuration writers, a block-style `extends:` key under `taxonomy:` or
`capabilities:` (and the section, when nothing else is left in it), leaving
every other byte as it was; and every call of `tests/nodeconfig.py`'s
`declare_extends` (`:37`) and of `set_component_key(..., "extends", ...)`
(`:23`) in those functions. Constants it cannot cut cleanly, built text,
dictionary-built configurations, and module-level constants shared by
functions of both classes are listed for commit 2.

**Commit 2, by hand:** the listed calls; `connect_sources`
(`tests/test_taxonomy.py:49-58`) and `connect_many`
(`tests/test_capabilities_federation.py:62-70`), as TCW-108 Step 8a left
them, writing only `parents:` with `inherit`; every `extends_add` call in a
fixture (not in a test of `extends_add` itself) replaced by a parent link
passing the axis; and `tests/nodeconfig.py`'s `declare_extends` deleted once
nothing calls it.

**Proves it:**

1. `compare_outcomes.py outcomes-step3.xml outcomes-step4.xml
   allowed-step4.txt` exits 0, with `allowed-step4.txt` empty: no outcome
   changes, since nothing reads `extends` for inheritance any more.
2. The plugin of the work list records nothing, apart from the tests whose
   subject is `extends` (Step 0's second class), listed by ID.
3. **Mutation check:** with `_source_stores` returning no stores, every
   converted test that asserts an inherited object goes red, each exception
   listed, read as the conversion safeguards say.
4. The inventory: no test ID disappeared, no count dropped, and the
   assertion dumps of commit 1 are unchanged.

## Step 5a — shipped text stops naming `extends`

Design 8.1; AC 37 (the three scans). Its own commit, before Step 5b removes
the commands, so that the documents stop naming them first (header, fact
2). Nothing in `tcw/` changes.

**Changes**, each passage changed to say that a project inherits taxonomy
and capabilities from the parents whose `inherit` includes the axis,
configured under `parents:` (pointing at the `configure` skill's projects
reference), and, where the passage speaks of overrides, that an override is
an object at the same path. Every passage Step 0's sweep found, at
`d2d02829`:

- `README.md:360`, `:371` (taxonomy table row and example), `:421`, `:432`
  (capabilities table row and example).
- `skills/taxonomy/SKILL.md:86`, `:111-115`, `:132`;
  `skills/capabilities/SKILL.md:26`, `:89`, `:94` ("not declared in
  capabilities.extends", a message that no longer exists), `:122-123`,
  `:130`, `:138`, `:175`; `skills/configure/SKILL.md:4` (the `when_to_use`
  line's "taxonomy and capabilities extends" becomes "inherited taxonomy
  and capabilities"); `skills/configure/references/stores.md:108-114`;
  `skills/configure/references/projects.md:6`, `:55`, `:117`, `:343-371`
  (the section on `extends` becomes a short section saying what replaced
  it, with no `` `taxonomy.extends` `` or `` `capabilities.extends` ``
  heading, keeping its anchors' targets reachable from `personal.md`);
  `skills/configure/references/personal.md:145-148` (the two table rows go);
  `skills/setup/references/taxonomy.md:18`.
- `docs/guide/taxonomy-and-capabilities.md:37-38`, `:57-64`, `:212-213`;
  `docs/guide/cli.md:14`; `docs/guide/multi-repo.md:257-269`;
  `docs/guide/linking-and-validation.md:17`, `:139`.
- The capability descriptions that name `extends`, in this repository's
  3.x layout (Design 8.2):
  `docs/capabilities/capabilities/federate/description.md`,
  `docs/capabilities/taxonomy/federate-shared-vocabulary/description.md`,
  `docs/capabilities/capabilities/configure-the-capabilities-store-location/description.md:9`,
  `docs/capabilities/capabilities/validate-capabilities/description.md:8-11`,
  `docs/capabilities/taxonomy/validate-the-taxonomy/description.md:1-5`,
  `docs/capabilities/cli/read-from-an-upstream-project/description.md:7`,
  `docs/capabilities/cli/reference-a-tcw-object/description.md:5`,
  `docs/capabilities/work/declare-capability-changes-in-a-child-projects-ledger/description.md:29`
  (Step 21 completes these records).
- Any passage TCW-108 to TCW-111 added or moved, from Step 0's sweep.
- **`tests/test_configuration_text_home.py`**: `KEY_PATHS` (`:40-41`) loses
  `taxonomy.extends` and `capabilities.extends`, in this same commit, since
  this commit removes their heading and their table row.

The sentences about overrides describe behaviour that arrives in Steps
7-11 on the same branch. Nothing is released between them (the spec's
Notes, 16).

`docs/use-cases.md` (`:92`, `:142-189`, `:369`, `:509`) is TCW-117's
(Non-goals) and names no removed command, so no scan reads a command
there; it is listed in Step 22's note.

**Proves it:** the three scans and `tests/test_configuration_text_home.py`
green, with the `extends` commands still present; Design 8.1's sweep with
`grep -n 'extends add\|extends rm\|\(taxonomy\|capabilities\) extends'`
finds nothing, `README.md` and the two `federate` descriptions included;
the full suite.

## Step 5b — the `extends` commands and store methods go

Design 1.5 (the commands, the store methods), 6.6 (the cycle check and the
alias collision); AC 15 (the commands and the store methods), 30 (its
first sentence).

**Tests first**, in new `tests/test_no_extends.py`:

- AC 15: `tcw taxonomy extends add core` and `tcw capabilities extends rm
  core` exit 2; `TaxonomyStore` and `CapabilitiesStore` have no
  `extends_add` or `extends_remove` (`hasattr` on the classes), and an
  opened `FsTaxonomyStore` and `FsCapabilitiesStore` have no `extends`
  attribute.
- AC 30: `app` inheriting from `core` with a top-level term folder `core`:
  `tcw validate` has no finding containing `collides with local top-level`.

**Changes**

- `tcw/store/fs.py`: delete `_FederationWalk` (`:935-962`),
  `_FederationCycles` (`:965-988`) and its use in both class bases
  (`:1704`, `:2225`), `_check_extends` (Step 3), `_persist_extends`
  (`:1444-1479`), both `extends_add` and `extends_remove` (`:1963-1990`,
  `:2718-2745`), the `_walk` parameter of `FsTreeStore.open`, `_open_at`
  and `resolve_store` (`:1298-1309`, `:1323-1326`, `:3182`), and in both
  `check`s the cycle findings and the project-ID collision findings
  (`:2047-2053`, `:2780-2786`). `_extends_ids` and `_extends_label` stay
  until Step 5c, which still reads the key to refuse it and rewrites
  `_legacy_config_problems`' message (`:1639`). `self.extends` is renamed
  `self._sources` (private), and **every reader is moved in this step**:
  `_override_problem`'s alias branch (`:2915-2922`) reads
  `self._sources.get(alias)` and its message becomes `overrides → unknown
  project '<alias>' (not a project this one inherits its capabilities
  from)`, since `_extends_label` names a key that is being removed; its
  test (`tests/test_capabilities_federation.py:172-179`) changes to that
  message in this step, listed in `allowed-step5b.txt` with Design 1.5;
  `_apply_override` (`:2364`), `get_capability_detail` (`:3021`) and the
  remaining 3.x readers (Step 0 lists them) read `self._sources`; and the
  two readers outside the store (`tcw/work/gates.py:354`, `:423`, as TCW-110
  Step 11 left them) read `own._sources` until Step 16 removes both uses.
- `tcw/store/base.py`: the abstract `extends_add` and `extends_remove`
  (`:396-402`, `:617-623`), and every docstring sentence naming `extends`
  (`:328`, `:347-358`, `:489`, `:513-526`, `:593`).
- `tcw/taxonomy/cli.py` (`:190-201`, `_extends_add`, `_extends_rm`) and
  `tcw/capabilities/cli.py` (`:147-158`, `:297-308`, and the module
  docstring's `extends add|rm`, `:6`): the `extends` groups.
- `tcw/refs.py:6` and `tcw/validate.py:110`: the docstrings naming
  `extends`.

**Changes the tests** whose subject is the commands or the store methods
(Step 0's second class): the tests of `extends add|rm`, of the legacy
`extends` map and duplicate IDs, of TCW-108 Design 3.6's refusals (TCW-108
Step 11, including `test_check_federation_cycle`), of `_persist_extends`
keeping comments, and of the cycle and alias-collision findings: each is
deleted, listed in `allowed-step5b.txt` with Design 1.5 or 6.6.
`tests/test_cli_help_standard.py`: the two `extends` commands leave
`SURFACE` (`:25`, `:28`); `:160`'s proof that the help walk sees a nested
group swaps `"taxonomy extends"` for another nested group of a command
module other than `work`, from Step 0's list, or, if `work tags` is the
only nested group left, keeps `"work tags"` and `"work tags add"`, which
already prove the walk descends, and the round says which. The `extends`
uses of `tests/test_config_edit.py` and `tests/test_config_edit_writers.py`
stay: they edit an arbitrary key of a file, not a store's configuration.

**Proves it:** the new tests; `compare_outcomes.py outcomes-step5a.xml
outcomes-step5b.xml allowed-step5b.txt` exits 0; the three scans green;
`grep -n "self\.extends\|\.extends\b" tcw/` finds nothing; the full suite.

## Step 5c — the `extends` key is refused

Design 1.5 (the key), 6.8; AC 15 (the key and the variables), 36.

**Tests first**, in `tests/test_no_extends.py`:

- AC 15: `taxonomy: {extends: [core]}` in `app`'s file makes `tcw taxonomy
  list` exit 1 with Design 1.5's message (`'taxonomy.extends' was removed
  in TCW 4.0` and `parents:`), and `tcw validate` report it as an error at
  `.tcw/tcw-config.yaml`; the same for `capabilities`; the same key in
  `core`'s file, `core` being `app`'s parent, leaves `tcw taxonomy list`
  in `app` exiting 0 (and lists `core`'s objects);
  `TCW_TAXONOMY_EXTENDS__APP=core` makes `tcw work list` exit 1 with `no
  configuration key is written` and not `is a shared key`, and the same
  for `TCW_CAPABILITIES_EXTENDS__APP`.
- AC 36: a `config.yaml` at `app`'s taxonomy root gives an error containing
  `parents:` and not `extends`.

**Changes**

- `FsTreeStore.__init__` (`:1272-1296`), for a store not opened with
  `as_other=True`: when `self.config` holds `extends`, raise `ValueError`
  with Design 1.5's message, naming the file (`_config_path()`), so every
  command on the axis exits 1, as today's `extends` errors do (Design 1.5).
  `tcw validate`'s store-opening path already reports such an error as an
  error at the file (Step 0 confirms the finding's `where`). A store opened
  with `as_other=True` never reads the key. If Step 0 found that TCW-109's
  loader reports keys missing from `known_keys()`, this refusal is raised
  first and the loader's report of `extends` is suppressed in the
  `ancestor` and `outside` roles (Step 0, point 3).
- Delete `_extends_ids` (`:904-933`) and `_extends_label` (`:1480-1487`).
- `_legacy_config_problems` (`:1619-1640`): Design 6.8's message.
- `tcw/config_keys.py`, `known_keys()`: the `extends` entries of the
  `taxonomy` and `capabilities` sections.
- **Not changed:** `taxonomy.extends` or `capabilities.extends` in the
  active project's *personal* file keeps the personal file's own refusal,
  `a shared key; a personal file cannot set it` (`tcw/config.py:402` at
  `d2d02829`, re-found in Step 0), not Design 1.5's message, because the
  personal file's allow-list is checked before any store is opened. The key
  is refused either way, and `tests/config/test_personal_allowlist.py:31-32`
  stays green as it is.

**Changes the tests**: `tests/test_legacy_store_config.py`'s `extends`
messages, rewritten to Design 6.8, and any test of the key still standing
from Step 0's second class, rewritten to AC 15's refusal; each listed in
`allowed-step5c.txt`.

**Proves it:** the new tests; `compare_outcomes.py outcomes-step5b.xml
outcomes-step5c.xml allowed-step5c.txt` exits 0; `grep -rn "extends" tcw/`
finds only `tcw/store/config_edit.py`'s generic examples (`:29`, `:638`)
and Design 1.5's message; the full suite.

## Step 6 — 3.x override fixtures move to their original's path (conversion)

No production code changes. Under the 3.x pointer rule an override is found
by its `overrides:` key wherever its folder is, so moving a fixture's
override folder to its original's id-path changes no outcome; after Step 7
only the path decides, so the fixtures must already be there. Most 3.x
override fixtures point by a bare id from an unrelated path (`ov/login`
overriding `base`'s `auth/login`, `tests/test_capabilities_federation.py:106`,
`:116`, `:126`, `:134`, `:142`), so the target folder is found from what
the pointer resolves to, not from the fixture's folder name.

**The work list.** The recording plugin is run with a hook
`tcw.store.fs._on_override(child_root, override_path, original_path,
own_paths)`, called by `_apply_override` (`:2344-2389`) whenever it applies
an override: the child store's root, the override's folder, the id-path of
the capability its pointer resolved to, and the child's own object paths at
that moment. Each record, keyed by test ID, says which fixture call must
move where.

The hook sees only overrides that 3.x still applies, and from Step 3 a
middle project's override is not applied in a lower project's view (choice
8). So the tests on Step 3's `xfail:` list are added to the work list by
hand: for each, its override fixtures are taken from Step 0's static list
of 3.x override fixtures, the original's id-path is found by resolving the
pointer by hand (a bare id against the state files of the middle project's
sources, `<alias>/<id>` against that alias's store), and the move goes to
commit 2. The 3.x capabilities store never flattened, so this list may be
empty; the round says whether it is.

**Commit 1, mechanical.** A script rewrites, in each recorded test, the
folder argument of the call that writes that override (`write_state_data`,
`write_state`, the `write_cap` helpers, matched by its literal folder and
the child root it writes under) from `override_path` to `original_path`. It
leaves a fixture whose folder already equals `original_path`. It lists for
commit 2, and does not rewrite: a call it cannot match to one literal; a
move onto a path that is already one of the child's own objects in that
test (a fixture with both a local object and an override at one path); two
overrides in one child resolving to the same original; and every assertion
or later call in the same test that names `override_path` (the assertion
dumps must stay identical, so those move by hand).

**Commit 2, by hand:** the listed calls and assertions; a fixture with two
objects at one path after the move is rewritten so the test still asserts
what it asserted, or listed with its design rule for Step 7; the
pointer-subject tests (Step 0's list) are not moved, since their pointers
resolve to nothing or to the wrong thing on purpose, and they are deleted in
Step 9; and the tests whose subject is the placement itself (`_write_target`
choosing `<alias>/<path>` when the mirror path is taken,
`tcw/store/fs.py:2676-2686`), which are not moved here but listed in
`allowed-step8.txt` for Step 8 to rewrite (Design 4.2: "The folder
`<alias>/<path>` is never used").

**Proves it:** `compare_outcomes.py outcomes-step5c.xml outcomes-step6.xml
allowed-step6.txt` exits 0 with an empty list (the `xfail:` tests stay
`xfailed`, since their overrides are still not applied until Step 7; one
that passes after its move has its mark removed in this step and is listed
in `allowed-step6.txt` with choice 8); the plugin, run again, records no
override whose `override_path` differs from its `original_path`, apart
from the pointer-subject tests, listed by ID; each `xfail:` test's override
fixture is at its original's path, checked against the hand list;
**mutation check**: with `_override_index` returning nothing, every moved
test that asserts an override's effect goes red, each exception listed; the
inventory, with commit 1's assertion dumps unchanged.

## Step 7 — reading by path: the view through `combine`

Design 2.1-2.5 (reading), 3.1, 3.2 (without the warnings, Step 12), 3.3,
3.6; the reading half of 4.5's records; AC 5, 6, 7, 8, 9, 10 (`show` and
`list` results only), 11 (`show` only), 26 (its first four sentences), 27.
**Every write keeps its 3.x outcome in this step** (Step 8 changes the write
rules): the writers that found an override through the 3.x pointer index
are re-keyed by path here, so that nothing still calls the index once it is
deleted.

**Tests first**, in new `tests/test_overrides_by_path.py` (CLI, as Step
3's file):

- AC 5, 6, 7, 8, 9 (the `show` part), 26's first four sentences (`show
  core.capabilities/cli/x` in `app` has `core`'s `Missing`; in `ee`, `show
  bb.capabilities/X` and `show cc.capabilities/X` agree with `show X`; `show
  app.capabilities/cli/z` for a path `app` only inherits exits 4), 27.
- AC 10's `show` and `list` results for a capability and for a term (`dd`'s
  object whole, exit 0, no `AmbiguousRef`), and AC 11's `show` result
  (`Status` from `bb`, `Priority` from `dd`).
- In `tests/test_combine.py`, a store-level test that `get_view`,
  `get_local` and `chain` give the `Combined` of Step 1 for AC 11's family
  and for a three-level family, so the store and the function cannot
  disagree.

**Changes** (`tcw/store/fs.py`, `tcw/store/base.py`, `tcw/locate.py`,
`tcw/taxonomy/cli.py`, `tcw/capabilities/cli.py`, `tcw/serve/records.py`):

- **Declarations.** `FsTreeStore._declarations() -> dict[str,
  Declaration]` over `own_paths()` (the walk's objects, TCW-111 Step 6),
  each read with `_state` and `description.md` (None when the file is
  absent, Design 2.3). A 3.x `overrides:` key is now just a key: it is
  dropped from `fields` with `id` and `tcw-version`, and reported by Step 9.
  `_local_paths` (`:2273-2277`) no longer separates override folders: every
  object folder is an own object. `_declarations()` takes over TCW-111's
  duty of filling `self.unreadable` for the project's own objects (each
  state file `_state` refuses), and each `check()` keeps clearing it before
  its full listing (TCW-111 plan.md:472-477). `has_own` and `declaration`
  are added (choice 1).
- **Another owner's sources** (choice 4; the plan re-check's M1). A store
  opened with `as_other=True` gets `_sources` as a property built on first
  use, from `_source_stores(axis)` over `registry.sources(axis, <its own
  project>)` (TCW-108 Step 7b's load order of any located project), and
  cached on the instance; from Step 3 to here it was `{}`. Its `_view()`
  combines with its own project's load order and choice 3's relation for
  that project. Nothing builds it while that store serves only as another
  store's source, since the active project's `_view()` reads each source's
  `_declarations()`, never its `_sources`; only `Locator.read`, `find_tree`
  and `_found` of another owner (below) do. So AC 26's owner-view sentences
  hold from this step, and an owner's missing ancestor already gives exit 7
  there (`show cc.capabilities/X` in `ee` with `bb` gone, tested in Step
  13). The active project's own store keeps opening its sources eagerly
  until Step 13.
- **The view.** `FsTreeStore._view()`: built once per store instance from
  `self._sources` (each source's `_declarations()`) and its own, in load
  order; for each id-path any of them declares, `combine` (Step 1), with
  choice 3's relation. Cached on the instance. It reads every object of
  every source, even for a command that needs one id-path (`show`): this is
  intended for this item, and reading per id-path is left for later, since
  it changes no outcome, only the time taken.
- **The objects.** `_term(id_path, combined)` (`:1731-1746`) and
  `_capability(id_path, combined)` (`:2328-2342`) build the record from a
  `Combined`: owner and full identifier from `chain[0]` (Design 2.4),
  `overrides` from the second member's full identifier, `name` falling back
  to the folder's (`:1736`, `:2336`), `_compose_body` (`:2311-2326`) reading
  `prependedDocs` and `appendedDocs` from the `resources/` of
  `declared_by[key]`'s folder and the description from
  `declared_by["description"]`'s, a term's attachments from the nearest
  member whose `resources/` holds a file, `modified` the latest of the
  members'. **Until Step 10**, `Capability.id` is the `id` of the nearest
  chain member whose own state file has one (3.x's `_apply_override` gives
  an override its original's id, `id=base.id`, `:2374`), read from the
  declarations since `combine` leaves `id` out, so `check`'s `missing id`
  and `duplicate id` keep their 3.x outcomes. **`_CAP_STRUCTURAL`**
  (`:2198`, as TCW-111 Step 13 left it) is unchanged: it keeps `parent`,
  `id`, `name`, `prependedDocs`, `appendedDocs` and `overrides`.
  `_CAP_STRUCTURAL` decides only which keys of the combined declaration
  become `Capability.fields` (`:2331`), and `check` reports every key of
  `fields` not in `CAP_FIELDS` as `unknown field` (`tcw/store/fs.py:2826-2830`,
  `tcw/store/base.py:458-461`), so taking `parent` out would report
  `unknown field 'parent'` for every capability that has one and put it
  into every JSON record's `fields`. `combine` folds the whole declaration
  (choice 2), so `parent` still combines like any key (Design 2.2) and
  reaches `Capability.parent`; `overrides` stays so that a 3.x pointer is
  never read as a field before Step 9 reports it with Design 6.4's message.
- **Deleted**: `_apply_override` (`:2344-2389`), `_override_index`
  (`:2301-2309`), `get_inherited` (both stores, and from the abstract
  classes, choice 1), the taxonomy's `_term_via` (`:1796-1797`) and
  `_inherited_stores`.
- **`get_by_id`** matches the `id` in each own object's **own state file** only (not the
  interim combined id above), so `_override_problem`'s `targets a local
  capability` check (`:2925`) does not fire on an override that carries its
  original's id; `get_by_id` goes in Step 10.
- **Each own object's references are checked once** (the plan re-check's
  I1). From this step `list_all(local_only=True)` returns the project's
  overrides too, since an override's chain starts with the project, so the
  second passes 3.x needed for override folders would check each override
  twice (the comment at `:2871-2875` names exactly that). So `check`'s
  per-object pass reads each own object's references from its own
  declaration (`declaration()`), which for an object that overrides nothing
  is its combined value and for an override is what `_set_fields` gave 3.x;
  the override loop's reference pass (`:2870-2882`, the `target and
  selected is None` branch) is deleted, while the loop's attachment checks
  and its `_override_problem` call stay until Step 9. The taxonomy's
  `_capability_referrers` (`:1899-1935`) reads the declared references of
  each own capability and drops its `overrides` list (`:1915-1920`), so an
  override is named `capability <path>`, not `capability override <path>`
  (Design 7.3: it is an own capability). With no caller left,
  `_override_fields` and `_set_fields` (`:2279-2299`) are deleted in this
  step. This brings the reference half of Design 6.2 and Design 7.3 (AC
  41's last sentence, AC 40) forward from Step 15, so that no step reports
  an override twice; Step 15 keeps the field checks on the combined object
  and tests AC 40 and 41.
- **The 3.x writers, re-keyed by path** (each keeping its 3.x outcome,
  through a private `_is_override(id_path)`: the active project has its own
  object there and its chain has more than one member):
  - `_write_target` (`:2655-2691`): the active project's own object at the
    id-path (`has_own`, then `declaration`) is written in place, with
    `is_override = _is_override(id_path)`; an inherited one gets a new state
    file at the mirror path with `is_override = True`, no pointer; the
    `<alias>/<path>` branch is unreachable (the mirror path is free exactly
    when the project has no object there) and is deleted with the pointer in
    Step 8.
  - `reset` (`:2576-2600`): the active project's own object at the id-path
    that `_is_override` is removed, with today's nested-folder refusal; an
    own object that is not an override keeps today's "is a local
    capability" refusal; no own object keeps the "inherits verbatim" one.
  - `remove` of an own object that `_is_override` keeps today's refusal of
    an inherited object until Step 8 (Design 4.4 lifts it there).
  - `_status_is_local` (`:2449-2459`): true when the active project's own
    object at the id-path sets `Status` in its own declaration (the rule
    Design 7.2 states; Step 16 deletes the function).
  - `get_capability_detail` (`:3016-3029`): the revision covers every chain
    member's state file and `description.md` (the rule Step 17a's tests
    check), replacing the `_override_index` lookup.
- **The lookups** (choice 1): `get_view(id_path)` is the view's entry;
  `get_local(id_path)` is the view's entry when its chain's first member is
  this project, else None; `chain(id_path)` is the entry's chain as full
  identifiers; `declaration(id_path)` is the own declaration alone (used
  by `check`'s reference checks from this step, and by the view-less
  routes from Step 13). `list_all(local_only=False)` lists the view, one entry per
  id-path, or with `local_only` the entries this project owns (Design 3.2).
  `search` matches the combined name and body.
- **Reading another owner** (Design 3.1, third row): `_found` (TCW-110 Step
  8) sends a `FullId` of another owner to `Locator.read`, and `Locator.read`
  and `find_tree` (`tcw/locate.py`) open that owner's store as choice 4
  says and call its `get_local`, which builds that owner's view; the branch
  through `get_inherited` goes. So `core.capabilities/cli/x` from `app` is
  `core`'s object as `core` sees it, never `app`'s override
  (design.md:459-462).
- **`AmbiguousRef` for a path** (Design 3.6): no store lookup raises it.
  Its catches for this reason (`:1928`, `:1955`, `:2003`, `:2954`, and
  `_check_subject`, `_check_feature`, as TCW-110 Step 9 moved them to
  `_stored_ref`) go; `tcw/serve/records.py:143` and `tcw/refs.py:122` (the
  latter catches every store error) are re-read in Step 0's citations and
  lose only the `AmbiguousRef` case. `AmbiguousRef` itself stays in
  `tcw/store/base.py:30` while `_resolve_vocab_ref`'s leaf-slug ambiguity
  (`:2022-2042`, which raises a `UsageError` of its own) or any other
  caller Step 0 finds still needs it; when none does, it is deleted with
  its docstring rows (`:349-358`, `:516-526`), and the round says which.
- **Records.** `tcw/taxonomy/cli.py` and `tcw/capabilities/cli.py`
  `_record` gain `overrides` (choice 7); `show` prints `overrides: <full
  id>` when set. `tcw/serve/records.py`'s `jsonable` serialises it as text.
  `tcw/taxonomy/cli.py`'s `_ordered` (`:49-56`, sorting on `origin`, as TCW-110
  Step 6 left it on `owner`) keeps its order.
- The `xfail` marks of choice 8 are removed.

**Changes the tests.** Every failure is read. Expected classes, each listed
in `allowed-step7.txt` with its rule: a test asserting `AmbiguousRef` for a
path (Design 3.6: now the load order decides, so it asserts the answer);
a term at an inherited path listed twice (Design 3.2: once, as an
override); an override that lists no `prependedDocs` now keeping its
original's (Design 2.3, Problem 5); `show <owner>.capabilities/<path>`
returning the owner's object rather than the active project's override
(Design 3.1; TCW-110's AC 23 cases in `tests/test_tree_full_identifiers.py`);
a test calling `get_inherited` (Step 0's list), moved to the owner's store's
`get_local` (Design 3.1); a test asserting `get_local` of an override
returns the raw own entry, now the combined object (choice 1); a test that
called `tcw taxonomy add` at an inherited path and now finds an override
(Design 3.2), until Step 8 changes what `add` writes; a `tcw validate`
scoped to one override that reported a problem in a reference only its
original sets (3.x checked a selected override's composed fields), now
silent (Design 6.2, AC 41); a `tcw taxonomy rm` refusal naming `capability
override <path>`, now `capability <path>` (Design 7.3). Step 3's `xfail:`
IDs must now pass, and each is listed in `allowed-step7.txt`, its outcome
going from `xfailed` to `passed` (choice 8); `compare_outcomes.py
outcomes-step2.xml outcomes-step7.xml` restricted to those IDs shows each
back to its Step 2 outcome, or the ID is listed with its rule.

**Proves it:** the new tests; `compare_outcomes.py outcomes-step6.xml
outcomes-step7.xml allowed-step7.txt` exits 0; `grep -n
"_apply_override\|_override_index\|get_inherited\|_inherited_stores" tcw/`
finds nothing; `grep -n "_override_fields\|_set_fields" tcw/` finds
nothing; `grep -rn "TCW-112 Step 7" tests/` finds nothing; the full
suite.

## Step 8 — writing by path

Design 2.7, 4.1, 4.2, 4.3, 4.4 (the cases that need the view), 5.1 (for
`set`); AC 20, 21, 22, 23 (all but its last sentence), 24, 25, 42 (the
store and CLI half; the web half is Step 17a).

**Tests first**, in `tests/test_overrides_by_path.py`:

- AC 20 (both `set` forms, the exact keys of the file, no `core` folder, the
  organising-folder case keeping `cli/x/z` listed), AC 21, AC 22, AC 23's
  first four sentences, AC 24, AC 25.
- A three-level chain (`app` over `lib` over `core`, `lib` overriding
  `core`'s `cli/x`): `tcw capabilities set core.capabilities/cli/x --field
  Priority=P2` in `app` writes `app`'s `cli/x` (choice 9: any member of the
  chain, not only the second), and `reset core.capabilities/cli/x` then
  removes it.
- AC 42 at the CLI: `tcw capabilities set cli/y --field Priority=` (the
  clear value) in a project with no parents leaves `Priority: null` in the
  file and no `Priority` in `show`; the same on `app`'s override leaves
  `Priority: null` over `core`'s `Priority: P1`.
- Design 2.7 directly: `inherited_at("cli/x")` in `app` is
  `core.capabilities/cli/x` with and without `app`'s own `cli/x`, and None
  for a path nothing inherits.
- Choice 9 at the store: `override_target` and `removal_target` called
  directly with each input form give the active project's own full
  identifier or the refusal, and `find_tree_writable` returns what they
  return.
- Choice 9's `NotFound` and early refusal: `set app.capabilities/cli/z`,
  `reset app.capabilities/cli/z` and `rm app.capabilities/cli/z` in `app`,
  which only inherits `cli/z`, exit 4 and write nothing, as `show` of that
  identifier does (AC 26); `set zz.capabilities/cli/x`, `zz` not one of
  `app`'s sources, exits 3 with Design 4.2's message.

**Changes** (`tcw/store/fs.py`, `tcw/store/base.py`, `tcw/locate.py`, both
CLIs):

- `inherited_at(id_path)` (Design 2.7): `combine` over the view's
  declarations at the id-path without the store's own, first member of the
  chain.
- **`override_target`, `removal_target` and `find_tree_writable`** as
  choice 9 says; both declared abstract in `tcw/store/base.py` with
  docstrings stating the rule. TCW-110's foreign-owner refusal in
  `find_tree_writable` goes; its test (TCW-110 plan.md:703-704, `set
  core.capabilities/cli/x` in `app` not inheriting from `core` exits 3,
  naming `core`) still passes with Design 4.2's message, and if it asserts
  `change it there` it is listed with Design 4.2.
- **`add`** (Design 4.1). `FsCapabilitiesStore.add` (`:2472-2500`): when
  `inherited_at` answers, `Refused` with Design 4.1's message; otherwise as
  today, writing no `id` from Step 10 (it still mints one in this step, so
  Step 10's conversion has one place to change). `FsTaxonomyStore.add`
  (`:1830-1866`): when `inherited_at` answers, the state file holds only
  what differs from the inherited term as this project sees it (`name` when
  it differs; `kind` only when `--kind` was given and differs, so the CLI's
  default, `tcw/taxonomy/cli.py:158-159`, is passed as None unless given;
  `vocabulary` when `--vocab` was given), `description.md` only when the
  description is not empty, and never `relatesTo`; nothing differing is
  `Refused` with Design 4.1's message; the combined term's checks
  (`:1859-1860`) run before writing; a `--parent` naming a path that only
  the view has creates the organising folders between. The CLI prints
  `<new full id> overrides <inherited full id>` on standard error.
- **`set`** (Design 4.2). `_write_target(target)` takes the `FullId` that
  `override_target` returns: the active project's own object at the
  id-path, if it has one, in place; else a new state file at the same
  id-path holding `tcw-version` and only the fields given, written into an
  existing organising folder when there is one. The `is_override` flag,
  the pointer (`{"overrides": …}`, `:2691`) and the `<alias>/<path>`
  branch (`:2676-2686`) go, with Step 7's `_is_override` uses in it.
  `_merge_meta` (`:2693-2705`) loses `is_override` and writes `None` as
  `null` on every own object; `add` keeps popping the key (`:2494-2498`).
  TCW-111 Step 13's refusal of `--parent` on an inherited capability goes.
  The object handed to any later ownership check is the active project's
  own object at the id-path (Design 4.2, last paragraph).
- **`reset`** (Design 4.3): takes `override_target`'s answer, so it accepts
  the id-path, the active project's full identifier or any in the id-path's
  chain; removes the active project's own object when `inherited_at`
  answers; keeps the three refusals (`:2578-2580`, `:2588-2590`,
  `:2594-2599` with `removal_blockers`); adds the refusal for another own
  object referencing the override's full identifier, naming each object and
  field, by the same field reading as `_referrers` (`:2536-2574`) extended
  to `Subject`, `Feature`, `relatesTo`, `vocabulary` and `parent`.
- **`rm`** (Design 4.4, `:1867-1897`, `:2502-2526`): takes `removal_target`'s
  answer; removes any own object, an override included (Step 7's interim
  refusal of an override goes); the refusals of an inherited object
  (`:1876-1878`, `:2512-2515`) are `removal_target`'s Design 4.4 message.
  After removing an override, the CLI prints `<id-path> now shows <next
  chain member's full id>` on standard error.
- **`set`'s re-read** (`:2714`) reads `get_view`.
- `tcw/taxonomy/cli.py`'s `_rm` and `tcw/capabilities/cli.py`'s `_set`,
  `_reset`, `_rm` call `find_tree_writable`, each passing `removing`
  (`True` for `rm`, `False` for `set` and `reset`; it has no default,
  choice 9), and pass its `FullId` on.
- The CLI help of `reset` (`prst`, `tcw/capabilities/cli.py:280-281`) says
  it accepts the overridden object's full identifier.

**Changes the tests**: the tests of `set` creating `<alias>/<path>`, of the
pointer written by `set`, of `rm` refusing an override, of `reset`'s
"inherits verbatim" when the override sat at `<alias>/<path>`, and of
`_merge_meta` deleting a cleared key on an object that overrides nothing;
each listed in `allowed-step8.txt` with its rule.

**Proves it:** the new tests; `compare_outcomes.py outcomes-step7.xml
outcomes-step8.xml allowed-step8.txt` exits 0; `grep -n
"is_override\|_is_override" tcw/store/fs.py` finds nothing; the full suite.

## Step 9 — the `overrides:` key is reported (conversion)

Design 6.4, 6.6 (`_override_problem`); AC 29. The conversion first, the
check last, so every commit is green: from Step 7 the key is only a key
(`_CAP_STRUCTURAL` keeps it out of `fields`, and nothing combines by it),
so removing it from a fixture changes no outcome.

**Commit 1, mechanical.** A script removes the `overrides:` key from every
state-file mapping written by a test on Step 0's override list, apart from
the pointer-subject tests, and nothing else.

**Commit 2, by hand:** what the script listed.

**Commit 3, the check and its test.** Tests first in
`tests/test_overrides_by_path.py`: AC 29 (the error at the file, and `show
cli/x` still combining). Changes: both `check`s report an `overrides` key
in an own state file as an error at that file with Design 6.4's message;
`_override_problem` (`:2912-2932`) and its call (`:2868-2869`) go; TCW-111
Design 2.5's paragraph "3.x override folders" and its row exceptions k-n
(TCW-111 Step 6's separation and any exemption in `shape_problems`, found in
Step 0) go. The pointer-subject tests (`dangling id`, `unknown project`,
`targets a local capability`, `ambiguous id`) are deleted in this commit,
listed with Design 6.6.

**Proves it:** AC 29; `compare_outcomes.py outcomes-step8.xml
outcomes-step9.xml allowed-step9.txt` exits 0, and every commit of the step
run alone is green; **mutation check**: with the combination ignoring the
active project's own declaration, every converted override test goes red,
each exception listed; the inventory, with commit 1's assertion dumps
unchanged; `grep -rn "overrides:" tests/` finds only AC 29's fixture and
the registry's own overrides.

## Step 10 — the opaque `id` goes (conversion)

Design 5.1, 5.2, 5.3, 6.6 (the `id` checks); AC 28, AC 23's last sentence.
Four commits, each green: what reads and writes the id goes first, then the
ids leave the fixtures, then row k applies to capabilities.

**Commit 1, the code that reads and writes the id, and its tests.** Tests
first in `tests/test_overrides_by_path.py`: AC 28's first and last parts (no
`id` in `show --json` or the text `show`; no `id` gives no `missing id`
finding) and AC 23's last sentence (`tcw capabilities add cli/new` writes
no `id`). Changes: `_mint_cap_id` (`:2211-2213`) and its call (`:2488`);
`Capability.id` (`tcw/store/base.py:495`) and its docstring (`:486-489`),
with Step 7's interim combined id; `get_by_id` (`:2401-2407`); the `id`
checks of `check` (`:2791-2802`, `:2815-2820`, `seen_ids`); `_detail`'s `id`
and `show`'s `id:` line (`tcw/capabilities/cli.py:42-43`, `:76-77`).
`_CAP_STRUCTURAL` keeps `id`, so a state file's `id` is never a field; row
k's exemption for capabilities (TCW-111 Step 5) is kept until commit 4, so
a fixture still holding `id: cap-…` is not yet an error. The tests whose
subject is the opaque id (minting, `get_by_id`, duplicate ids, `missing
id`) are deleted or rewritten to AC 28 in this commit, listed with Design
5, and so are the tests that read a capability's `id` from a record (Step
0's id list).

**Commit 2, mechanical.** A script removes `id: cap-…` from every
capability state file a test writes (Step 0's id list), and the `id`
argument from every helper that takes one.

**Commit 3, by hand:** what the script listed.

**Commit 4, row k for capabilities.** Tests first: AC 28's middle part
(`id: cap-1a2b3c` in folder `cli/x` gives row k's error; `id: x` gives
none). Changes: TCW-111's row k is applied to capabilities (its exemption
goes). The failure list of this commit, found before commit 2 as "Finding
a failure list before the check exists" says, is what commits 2 and 3
converted.

**Proves it:** AC 28; `compare_outcomes.py outcomes-step9.xml
outcomes-step10.xml allowed-step10.txt` exits 0, and every commit run alone
is green; **mutation check**: with row k's exemption for capabilities put
back, AC 28's `cap-1a2b3c` case goes red, and with `_mint_cap_id` put back,
AC 23's last sentence goes red; `grep -rn
"cap-[0-9a-f]\{6\}\|_mint_cap_id\|get_by_id" tcw/ tests/` finds only AC
28's fixture; the inventory, with commit 2's assertion dumps unchanged.

## Step 11 — an object that overrides nothing must be complete (conversion)

Design 6.1; AC 13, 14. The fixtures first, the check last.

**The failure list.** Design 6.1's check (below) is written in the working
tree, the suite is run, and the tests it turns red are recorded with the
fixture call each traces to; the check is then set aside as a patch, as
"Finding a failure list before the check exists" says.

**Commit 1, mechanical.** The record writers on Step 0's list that write no
`name` or no `description.md` gain a keyword-only `complete: bool` with
**no default**, so that every call says which it is and a shared fixture
never defaults a property the code branches on
(`docs/lifecycle/implementation.md`). `complete=True` writes `name` (from
the folder, the fallback `_term` and `_capability` use) and an empty
`description.md` when the caller gives neither. A script passes
`complete=True` at exactly the calls the failure list traces to and
`complete=False` at every other call, so that no override fixture gains a
`name` (which would replace its original's, Design 2.2) or becomes
complete (which would silence Design 2.5's warning). Writers that already
always write both (`tests/test_capabilities_federation.py:28-39`'s
`write_cap`) are left as they are.

**Commit 2, by hand:** the fixtures on the failure list that write state
files directly with `write_state_data`, each given `name` and an empty
`description.md`.

**Commit 3, the check and its tests.** The patch is applied again. Tests
first in `tests/test_overrides_by_path.py`: AC 13 (both capability and
term, the message's parts; the two complete objects with an empty
`description.md` giving no error), AC 14. Changes: both `check`s, for each
own object whose chain has one member, report the missing parts of its own
declaration (`name`, `Status` for a capability, `description.md`) as one
error at its state file with Design 6.1's message; `missing Status`
(`:2828-2829`) is replaced by this message for such an object; an
override's missing parts are never reported. The tests whose subject is an
incomplete object (`missing Status` tests now get Design 6.1's message, and
assert its `Status` part) change in this commit, listed.

**Proves it:** AC 13, 14; `compare_outcomes.py outcomes-step10.xml
outcomes-step11.xml allowed-step11.txt` exits 0, and every commit run alone
is green; **mutation check**: with every `complete=True` the script wrote
turned to `complete=False`, each test on the failure list goes red with `is
incomplete`, which shows the fixtures are what keeps them green; the
inventory, with commit 1's assertion dumps unchanged.

## Step 12 — two unrelated projects at one path

Design 2.5 (the warnings), 3.2 (warnings on standard error), 6.3; AC 9's
and 12's "no warning", 10 (the warnings), 11 (the warning), 43.

**Tests first**, in `tests/test_overrides_by_path.py`: AC 9's last
sentence; AC 10's warnings in `tcw validate` (exactly one, `where`
`.tcw/tcw-config.yaml`, exit 0) and in `tcw capabilities list` (standard
error, after `warning: `, standard output one identifier per line), and
`parents: [dd, cc]` reversing it; AC 11's warning; AC 12; AC 43 (the
complete object silences both, the partial one does not, `dd`'s complete
object in AC 11's family does not).

**Changes.** `view_warnings` (choice 1) from each `Combined.unused` that is
warned about; `list` and `search` in both CLIs print the warnings for the
id-paths they list on standard error before the list (Design 3.2); both
`check`s, when not scoped to one object, add one `warning` finding per
warning at the active project's `.tcw/tcw-config.yaml` (Design 6.3).

**Proves it:** the tests; the full suite.

## Step 13 — inherited content is read only when it is needed

Design 1.3 (when the view cannot be built), 1.4, 3.1 (existence checks),
3.4, 3.5, 4.4 (not found when the view cannot be built), 6.5; AC 16, 17, 18
(`--local`), 26's last three sentences, 35.

**Tests first**, in new `tests/test_tree_parent_missing.py`:

- AC 16, every bullet (with `core`'s manifest entry naming a folder that
  does not exist); AC 18's `tcw taxonomy list --local` exit 0; AC 26's
  `show cc.capabilities/X` in `ee` exiting 7 (naming `'cc' inherits its
  capabilities from project 'bb'`) and 5, and `zz`'s `tcw validate`
  reporting no finding naming `cc.capabilities/X`.
- A `tcw://cc.capabilities/X` link in `zz`'s description, with `bb`'s
  folder removed: `tcw validate` in `zz` reports no finding for the link.
- **The refusal order of choice 9** (TCW-114 relies on it), in AC 5's
  family with `core`'s folder removed: `tcw capabilities rm
  core.capabilities/cli/x` and `tcw taxonomy rm core.taxonomy/<its term>`
  in `app` exit 3 with Design 4.4's message, not 7; `tcw capabilities set
  zz.capabilities/cli/x --status Supported`, `zz` not one of `app`'s
  sources, exits 3 with Design 4.2's message, not 7; and `tcw capabilities
  set core.capabilities/cli/x --status Supported` exits 7 (whether it is in
  the chain needs the view).
- AC 35: a test that wraps `FsTreeStore.__init__` and `project_folder`
  (TCW-107 Step 3) to record each store root opened and each project ID
  looked up, while each of `tcw taxonomy list`, `tcw capabilities list` and
  `tcw validate` runs in a project with no parents, run in process through
  `tcw.cli.main`: only the project's own `docs/taxonomy` and
  `docs/capabilities` (and no capabilities store for `tcw taxonomy list`),
  and no `project_folder` call with another ID.

**Changes**

- Both stores' `__init__` no longer open sources: `self._sources` becomes a
  property built on first use (Design 1.4), from `_source_stores` (Step 3),
  cached on the instance, for the active project's store as for an
  `as_other` store since Step 7 (one property for both from here).
  Every lookup that needs the view (Design 3.5's
  table) goes through `_view()`, which reads `_sources`; `own_paths`,
  `has_own`, `declaration`, `list_all(local_only=True)`'s fallback and `rm`
  of an own object do not.
- **Every route by which a command reaches an own object, and what it calls
  from this step** (the plan review's S1; from Step 7 `get_local` builds
  the view, choice 1):

  | Route | Used by | Calls from this step |
  | --- | --- | --- |
  | `find_tree` form a of the active project, and form d with an own object (`tcw/locate.py`) | `show` | `get_local`; on `InheritedUnavailable`, `declaration` marked partial (below) |
  | `find_tree_writable` → `override_target` | `set`, `reset` | `has_own` first; a project that is not a source is refused before anything is read; the view only when there is no own object or the input names a source (choice 9) |
  | `find_tree_writable` → `removal_target` | `rm` | another project's full identifier refused before anything is read; `has_own`; the view only for an id-path with no own object, and its `InheritedUnavailable` becomes not found (Design 4.4) |
  | `_found(FullId of the active project)` | `remove`, `reset`, `_write_target`, `get_term_detail`, `get_capability_detail`, `update_term`, `update_capability` | `has_own` and `declaration` for the writers; `get_local` for the two detail reads (the web app needs the view, and 503s without it, Step 17a) |
  | `set`'s re-read after the write (`:2714`) | `set` | `get_view`; on `InheritedUnavailable`, `declaration` marked partial, and `set` still exits 0 |
  | `Locator.read(full_id)` for the active project | `resolve_address` (validate's link check, the web app's `/api/resolve`), `_stored_ref` | not used for existence any more: see `Locator.exists` |
  | `Locator.read(full_id)` for another owner | `show <owner's full id>`, the records gate | the owner store's `get_local` (it combines, Design 3.1) |

- **Existence without the view** (Design 3.1, second consequence): new
  `Locator.exists(full_id, named_by) -> Outcome`, which asks the owner's
  store `has_own(id_path)` only (the owner opened as choice 4 says, so
  none of its sources is read). `resolve_address` (TCW-110 Step 10) uses it
  for a taxonomy or capability address, and `_stored_ref` (TCW-110 Step 9)
  and the referrer checks of `rm` and `reset` use it or `has_own` for the
  active project. So an ancestor of the owner being missing never makes
  them "could not check", and `tcw://cc.capabilities/X` in `zz` resolves
  with `bb` gone. `Locator.read` stays for the callers that need the object.
- **Reading own objects without the view** (Design 3.4): `list --local` and
  `show` of an own object (by id-path or the active project's full
  identifier) catch `InheritedUnavailable`, print `warning: <message>;
  showing only '<P>''s own declarations` once on standard error, and print
  each object's `declaration()` (`partial: True`, no `overrides`); the JSON
  record has `"partial": true` and no `overrides` key; the text `show`
  prints `partial: inherited content could not be read` instead of an
  `overrides:` line; exit 0. Every other command lets the exception through
  to exit 7 (TCW-108's handler).
- **`rm` of an id-path the active project has no object at**, when the view
  cannot be built, is not found (exit 4); the `now shows` line is left out
  when the view cannot be built (`removal_target`, choice 9).
- **`tcw validate`** (Design 6.5): when `_view()` raises for an axis the
  project has a store for, the finding of Step 3 (TCW-108's row (c), or the
  `"store"` finding); then for that axis the checks needing the combined
  object (6.1, the field checks of 6.2 from Step 15, and 6.3) are not run,
  and the checks of what the own objects declare (reference existence
  through `Locator.exists`, unknown and retired fields, invalid values
  present in the file, 6.4, TCW-111's rows) still run, over `declaration()`
  of each own path. Catching the exception is enough here, without
  TCW-109's `source_entries`: Design 6.5 skips every combined check for the
  axis as soon as any source is missing, so knowing which other sources
  are present would change no finding.

**Changes the tests**: TCW-108's tests of exit 7 on `tcw taxonomy list
--local` or `show` of an own object (if any assert exit 7 there), each
listed with Design 3.4.

**Proves it:** the new tests; `compare_outcomes.py outcomes-step12.xml
outcomes-step13.xml allowed-step13.txt` exits 0; the full suite.

## Step 14 — a source's object with a version problem

Design 1.3 (an unreadable id-path); AC 39.

**Tests first**, in `tests/test_tree_parent_missing.py`: AC 39, every
sentence.

**Changes**

- `_declarations()` (Step 7) records a source's object whose `_state` raises
  `StateFileProblem` as unreadable at its id-path (the object exists; its
  contents are not read), and `_view()` passes the set to `combine`'s
  `unreadable` (Step 1).
- `list` and `search` leave an unreadable id-path out, print its message on
  standard error and exit 1, as TCW-111 Step 5 does for the project's own
  (`st.unreadable`); `list --local` prints the own object at it as its own
  declaration, marked partial, and also exits 1.
- `show`, `reset` and `add` at it, `set` of it when the project has no own
  object there, `chain`, and `inherited_at` raise the version problem (exit
  1) and change nothing; `set` and `rm` of the own object at it work
  (`override_target` and `removal_target` answer from `has_own`).
- `tcw validate`: one `unresolved` finding at the active project's
  `.tcw/tcw-config.yaml`, `could not check <axis> <id-path>: <message>`, and
  for that id-path no 6.1, 6.2 field or 6.3 check.

**Proves it:** AC 39; the full suite.

## Step 15 — each own object is checked as the project sees it

Design 6.2, 6.7, 7.3; AC 34, 40, 41, 42 (`tcw validate` reports nothing
about `cli/y`).

**Tests first**, in `tests/test_overrides_by_path.py`: AC 34, AC 40, AC 41,
and AC 42's `tcw validate` sentence.

**Changes**

- Both `check`s (`:2044-2084`, `:2761-2882`): the field checks (unknown or
  retired field, invalid `Status`, `Priority`, `Lifecycle`, "Partial
  requires Gaps", "Blocked requires Blocked by", a Feature's vocabulary,
  `:2070-2084`, `:2821-2840`) read each own object's combined fields
  (`get_local`), where `null` leaves no field (AC 42); the reference checks
  read the references the own declaration sets (`declaration()`, from Step
  7), never an inherited value (AC 41's last sentence). One list of own
  objects: what is left of the override-folder loop (`:2846-2881`), its
  attachment checks, folds into it (its reference pass went in Step 7 and
  its pointer check in Step 9).
- **Design 6.7**: row m (TCW-111 Step 14) does not warn when the object's
  combined `parent` names an object at the same id-path as its folder
  parent, owned by a project that passes the axis to the active project.
- **Design 7.3**: done in Step 7 (`_capability_referrers` reads the active
  project's own capabilities' declared references only); AC 40 is tested
  here.

**Proves it:** the tests; `grep -n "_override_fields\|_set_fields"
tcw/` finds nothing; the full suite.

## Step 16 — the records gate and drift

Design 7.1, 7.2; AC 31, 32, and AC 15's "no `extends`" in the gate.

**Tests first**, in `tests/work/test_gates.py`: AC 31, all four sentences
(the last with `core`'s folder removed). In
`tests/test_overrides_by_path.py`: AC 32. In
`tests/test_tree_parent_missing.py`: AC 16's `tcw capabilities drift`
exiting 7 with nothing on standard output.

**Changes**

- `tcw/work/gates.py`, `route_capability_path` (`:331-380` as TCW-110 Step
  11 left it): rule 1 (`own._sources`, Step 5b's interim name) goes; every
  entry is routed by its full identifier's owner to that owner's own
  ledger, opened through the `Locator`.
- `_LedgerReader.capability` (`:401-410`): the owner's `get_local(id_path)`,
  `Present` with its combined `Status`, or `ABSENT`.
- `_LedgerReader.removal` (`:412-426`): `REMOVED` when the owner has no own
  object at the id-path (`has_own`), else `STILL_LOCAL`; the `INHERITED`
  branch (`:421-424`) and the `INHERITED` outcome go (with its rendering,
  found in Step 0).
- `_READ_ERRORS` (`:383`) gains `InheritedUnavailable`, so it becomes
  `Unchecked(<message>)`.
- `tcw/store/fs.py`: `_status_is_local` (Step 7's path-keyed form) goes;
  `unreviewed_inherited` (`:2461-2463`) is the view's entries whose owner is
  not the project, plus the project's own overrides whose own declaration
  sets no `Status`. `tcw/capabilities/cli.py`'s `_drift` builds the list
  before printing anything.

**Proves it:** the tests; `tests/work/test_gates.py`,
`tests/work/test_drift_work.py`, `tests/work/jira/test_jira_drift.py`,
`tests/test_routing_nodes.py` green; `grep -n "extends\|_sources\|INHERITED"
tcw/work/gates.py` finds nothing; the full suite.

## Step 17a — the web app: overrides, ownership and 503

Design 4.5 (all but its last paragraph); AC 33, 42 (the web half). Choices
5 and 6.

**Tests first**, in new `tests/serve/test_overrides.py` (with the existing
server fixture of `tests/serve/`): AC 33, every sentence; AC 42's two
`PATCH` cases; a `PATCH` with `"body": ""` of an own object that overrides
nothing leaves an empty `description.md` and `tcw validate` clean (choice
5); a `PATCH` of an own term override changes only its file (choice 6); two
`PATCH`es of one override with the same revision, the second refused as
stale (the revision covers every chain member, Step 7). In `web/client`,
the entry view's test: a record with `overrides` shows "overrides `<full
id>`".

**Changes**

- `tcw/serve/server.py`, `error_answer` (`:69-95`): `InheritedUnavailable`
  → `503`, `{"code": "inherited-unavailable"}`, beside `Unreachable`
  (`:88-89`).
- `tcw/serve/records.py`, `update_term` (`:106-123`) and
  `update_capability` (`:181-200`): the check of `found.origin != "local"`
  (`:117-119`, `:193-196`, as TCW-110 Step 8 left it on the owner) is
  "owner is the served project", else `read_only` (403) with "owner" in the
  message. The message keeps today's hint, `; or override it in this
  project with tcw capabilities set <id-path> --field <name>=<value>`
  (`:194-196`), which TCW-114 Design 1.4 also keeps.
- `tcw/store/fs.py`, `update_capability` (`:3031-3074`): `_write_target`
  (Step 8) through `override_target`, `_merge_meta` without `is_override`,
  and choice 5's body rule replacing `:3058-3068`. `update_term`
  (`:2124-2198`): choice 6.
- `web/client`: the entry view shows "overrides `<full id>`" when the record
  has one; the model type gains `overrides: string | null` and `partial?:
  boolean`. `pnpm build`.

**Proves it:** the tests; `tests/serve/` green; `pnpm test`; the full
suite.

## Step 17b — the web editor edits the declared description

Design 4.5's last paragraph; AC 44. Decided by the dispatching session on
the plan review's D1. This fixes a 3.x problem as well: today a capability
with its own `prependedDocs` or `appendedDocs` has its attached documents
written into `description.md` by any web save of its body, because the
editor is given the combined body (`web/client/src/ui/app.tsx:636-639`,
saved at `:737-738`; `_compose_body`, `tcw/store/fs.py:2311-2326`).

**Tests first**:

- In `tests/serve/test_overrides.py`: AC 44's two server families, every
  sentence; `declaredDescription` is `""` for an own capability whose
  `description.md` is empty, and is present in the answers of `POST
  /api/capabilities` and `PATCH /api/capabilities/<key>`; and a capability
  in `solo` with no attached documents whose `description.md` holds `Y
  body` followed by a newline has `declaredDescription` `Y body`, equal to
  its `capability.body`.
- In `web/client/src/ui/app.test.tsx`: AC 44's client sentence (the body
  field holds `declaredDescription`, the note is shown, a save that changes
  only a field sends no `body`); a detail with `declaredDescription` `null`
  opens an empty body field; a save after editing the body sends the
  field's text as `body`; a detail whose `body` equals its
  `declaredDescription` shows no note (the server test above shows the two
  are equal for a file ending in a newline).

**Changes**

- `tcw/store/base.py`, `CapabilityDetail` (`:445-449`): gains
  `declared_description: str | None = None`, with its docstring.
- `tcw/store/fs.py`, `get_capability_detail`: fills it from the
  description of the owner's own declaration (`declaration(id_path)` of the
  chain's first member's store; the active store's for an own object),
  `None` when the owner declares none, with leading and trailing white
  space removed, as `_compose_body` uses it (`raw_desc.strip()`,
  `:2320-2321`; `_load_entry` reads the file untrimmed, `:1657`). So a
  `description.md` ending in a newline does not make `body` and
  `declaredDescription` differ, and the editor shows no false note
  (Design 4.5; the plan re-check's I6).
- `tcw/serve/records.py`, `get_capability`, `create_capability` and
  `update_capability`: each answer gains `"declaredDescription":
  detail.declared_description` beside `capability` and `coreRevision`.
  Nothing changes in what `update_capability` writes: the body it is sent
  is written as `description.md` (choice 5).
- `web/client/src/model/types.ts`, `CapabilityDetail`: `declaredDescription?:
  string | null`. `web/client/src/ui/app.tsx`: the capability editor's draft
  takes `body: payload.declaredDescription ?? ""` (`:636-639`), so
  `original.body` is the declared text and the save's comparison
  (`:737-738`) sends `body` only when it changed; when
  `capability.body` differs from the declared text, the editor shows,
  beside the body field, that the body shown on the page also holds
  attached documents or an inherited description, which the edit leaves
  unchanged. The read view keeps showing `capability.body`. `pnpm build`.
- A term needs no change (Design 4.5: its description is never composed).

**Proves it:** the tests; `tests/serve/` green; `pnpm test`; `pnpm exec tsc
--noEmit`; the full suite.

## Step 18 — what `tcw project info` shows

Design 3.7. Decided by Step 0's point 7:

- **`tcw project info` does not exist** (TCW-115 not landed, the expected
  case): nothing is built; Step 22's note to TCW-115 carries Design 3.7's
  rule, and that `list --local --json`'s records (their `overrides`) and
  `view_warnings()` are its inputs.
- **It exists**: tests first in TCW-115's test file for `info`: per axis, the
  own objects whose `overrides` is set, each with it, and the count of
  warnings; the change adds both to `info`'s output from those two inputs.

**Proves it:** the round says which case held; in the second, the tests.

## Step 19 — shipped text that states the removed override rules

Design 8.1 (each passage says an override is an object at the same path);
AC 37 (its sweep, re-run). Lands after Step 11, once the rules it describes
exist. Step 5a changed every passage that names a removed command or key;
this step changes the passages that give agents and readers the 3.x
override rules without naming one, which the `Skill-Driven-Component`
documentation entry covers ("model/fields ... or guardrails"), so that an
agent following a skill on a 4.0 build does not write files `tcw validate`
refuses:

- `skills/capabilities/SKILL.md:29` ("carrying an opaque stable `id`"):
  a capability is addressed by its path and has no `id`.
- `skills/capabilities/SKILL.md:141-147`: `set` on an inherited capability
  writes the project's own capability at the same path, holding only the
  fields given, with no `overrides` pointer; an empty override body
  re-inherits (Design 2.3); `reset` takes the id-path or the overridden
  object's full identifier and is refused while the project's own
  references name the override; `rm` removes an override; `tcw validate`
  reports an object that overrides nothing and is incomplete, an
  `overrides` key, and two unrelated projects at one path, and no longer
  checks override targets or federation cycles.
- `docs/guide/taxonomy-and-capabilities.md:79` (opaque id) and `:222-227`
  (`overrides: <upstream-id>`): the same two rules, in a sentence each; the
  guide's fuller rewrite stays TCW-117's.
- Any further passage from Step 0's second sweep (point 5).

**Proves it:** the three scans green; `grep -n "opaque\|overrides:\|must-be-inherited"`
over the files above finds only sentences saying these are gone; Design
8.1's narrowed sweep still finds nothing; the full suite.

## Step 20 — a guard that keeps it removed

AC 30's second sentence, and a backstop for Steps 4, 9 and 10.

**Tests first**, new `tests/test_no_3x_inheritance.py`, a static test
reading files:

- no file under `tcw/` contains `cycle in taxonomy federation`, `cycle in
  capability federation` or `collides with local top-level` (AC 30);
- no file under `tcw/` defines or calls `_mint_cap_id`, `get_by_id`,
  `_apply_override`, `extends_add` or `extends_remove`;
- no test file writes `extends:` under `taxonomy:` or `capabilities:`, an
  `overrides:` key in a state file, or `id: cap-`, apart from the files that
  test the refusals (AC 15, 28, 29), named in the test.

**Mutation check:** each rule is broken once in a scratch copy and the test
goes red for that rule.

**Proves it:** the test and its mutation check; the full suite.

## Step 21 — this repository's records

Design 8.2. In **3.x form** (`meta.yaml`, `description.md`, `id: cap-…`
kept), as the header explains; edited by hand, never with `.venv/bin/tcw`.

- The capabilities of the spec's "Capability changes", each
  `description.md` given the sentence the spec gives it:
  `taxonomy/override-an-inherited-term` (new, `meta.yaml` with a fresh `id`
  in 3.x form, `name`, `Status: Supported`, `Subject` naming the new term);
  `taxonomy/federate-shared-vocabulary`, `capabilities/federate`,
  `capabilities/override-inherited`, `capabilities/set-a-capabilitys-status`,
  `capabilities/reset-an-override`, `capabilities/remove-a-capability`,
  `taxonomy/remove-a-local-term`, `capabilities/add-a-capability`,
  `taxonomy/add-a-term`, `capabilities/read-a-capability`,
  `taxonomy/read-a-term`, `capabilities/browse-capabilities-by-status`,
  `taxonomy/browse-the-term-forest`, `capabilities/search-capabilities`,
  `taxonomy/search-terms`, `capabilities/validate-capabilities`,
  `taxonomy/validate-the-taxonomy`, `cli/validate-a-project`,
  `capabilities/detect-capability-drift`,
  `capabilities/configure-the-capabilities-store-location`,
  `cli/reference-a-tcw-object`, `cli/read-from-an-upstream-project`,
  `work/declare-capability-changes-in-a-child-projects-ledger`,
  `web/editing` (which also says that a body edit changes only the
  capability's own description, Design 4.5). Step 5a already rewrote the
  passages naming removed commands; this step completes each description.
- New `docs/taxonomy/override/` (`meta.yaml` and `description.md`).
- The item's `capabilities.yaml` already lists these; D1 changes what
  `web/editing` says, not which capabilities change, so it is not edited.

**Proves it:** with the lifecycle `tcw`: `tcw validate`, and `tcw work
advance TCW-112 --dry-run` at the end of implement (the records gate passes
for every entry); `tests/test_ledger_3_0.py` and the three scans green.

## Step 22 — notes for the later children

Comments the dispatching session posts (the text in the implement round),
the spec's Handoffs plus what planning added (the handoff texts of this
revision are in the revision report; the implement round repeats any that
changed):

- **TCW-113:** the view is `get_view` and `list_all()`; `--scope own` is
  `list_all(local_only=True)`; `--project <id>` reads `get_local` of that
  project's store (choice 1); `InheritedUnavailable` is now 503 in the web
  app (Step 17a), not TCW-108's 500; the web app's read-only rule is "owner
  is the served project" (Step 17a); the capability detail answer carries
  `declaredDescription`, which the editor edits (Step 17b); existence
  without the view is `Locator.exists` (Step 13). TCW-113's handoff of
  2026-10-22 (`--scope`, `show` by id-path under `own`, its Design 4.8
  replacing two rows of Design 3.5's table, this item's tests gaining
  `--scope up`) changes nothing in this plan: each of those lands in
  TCW-113, after this item.
- **TCW-114:** Design 2.7 is `inherited_at(id_path)` on both tree stores;
  the chain is `chain(id_path)`; the two refusal sites its Design 1.3
  rewords are `override_target` (Design 4.2's message, for `set` and
  `reset`) and `removal_target` (Design 4.4's, for `rm`), and nowhere else
  (choice 9); `find_tree_writable` returns the active project's own full
  identifier for every input it accepts, so a `check_owned` placed after it
  always passes, and the refusals must be reworded inside those two
  methods; the object handed to its ownership check by `set`, `reset` and
  `tcw taxonomy add` is the active project's own object at the id-path.
  `find_tree_writable`'s `removing` keyword has no default. `removal_target`
  refuses every other project's full identifier before anything is read,
  and `override_target` refuses a project that is not one of the active
  project's sources before anything is read (both tested in Step 13), so
  the `check_owned` calls placed in those branches keep that order; a
  source's identifier not in the chain still needs the view (exit 7 with a
  source missing). The active project's own full identifier at a path
  where it has no object is `NotFound` (exit 4) in both.
- **TCW-115:** Step 18's outcome; Design 3.7's inputs are `list_all(local_only=True)`
  records with `overrides` set, and `view_warnings()`.
- **TCW-116:** the spec's handoff, plus: a 3.x override is moved to the
  id-path of the capability its pointer resolves to, which is usually not
  `<alias>/<path>` and often not its folder's name (Step 6 found most test
  fixtures at unrelated paths); a move onto a path the project already has
  an object at is reported, not made; a capability's `id: cap-…` must be
  removed or row k fails (Step 10); a hand-written object with no `name` or
  no `description.md` that overrides nothing fails 6.1, so `tcw migrate`
  writes both and reports each; a 3.x override that lists no
  `prependedDocs` or `appendedDocs` while its original does changes its
  body; this repository's records (Step 21) are in 3.x form.
- **TCW-117:** the spec's handoff; the passages Steps 5a and 19 changed
  only enough to name no removed command and state no removed rule;
  `docs/use-cases.md:92`, `:142-189`, `:369`, `:509`.

## Step 23 — Documentation Sync

Each entry of `tcw work docs`, evaluated with the `documentation-sync`
skill, and recorded in the round:

| Entry | Fires? | Answer |
| --- | --- | --- |
| `README.md` [Public-API] | yes: `extends add|rm` removed | The four `extends` lines changed in Step 5a (AC 37); the fuller rewrite is TCW-117's. |
| `docs/guide/jira.md` [Jira-Change] | no: no ticket, key or status changes | Nothing. |
| `docs/guide/<topic>.md` [Guide-Topic-Change] | yes: `taxonomy-and-capabilities.md`, `multi-repo.md`, `linking-and-validation.md`, `cli.md` | The passages naming removed commands or keys, Step 5a; the two stating removed override rules, Step 19; the fuller rewrite is TCW-117's (Step 22's note). |
| `docs/release-notes/upcoming/<folder>.md` [Public-API] | yes | Written (below). |
| `docs/changelogs/upcoming/<folder>.md` [Any-Code-Change] | yes | Written (below). |
| `skills/<component>/SKILL.md` [Skill-Driven-Component] | yes: `taxonomy` and `capabilities` (commands removed, override by path, no opaque id, `add` at an inherited path, `reset` by full identifier, `partial` records, exit 7, the checks that changed) | The passages of Steps 5a and 19, plus in each skill's command table: `tcw taxonomy add` at an inherited path writes an override; `tcw capabilities set` on an inherited capability writes the project's own object at the same path; `reset` takes the overridden object's full identifier; `rm` removes an override; a record with `"partial": true`. The fuller explanation is TCW-117's. |
| `skills/configure/references/<document>.md` [Configuration-Key-Change] | yes: `taxonomy.extends`, `capabilities.extends` removed | `stores.md`, `projects.md`, `personal.md`, Step 5a. |
| `docs/use-cases.md` [Project-Setup-Change] | yes: UC-2, UC-3, UC-6, S-4, S-6 | Deferred to TCW-117, with the spec's Notes list and Step 22's note, as for TCW-108. |

The two `upcoming/` files are named
`TCW-112-tcw-4-0-inheriting-taxonomy-and-capabilities-and-overrides-by-path.md`,
following each folder's `README.md`, and formatted with `prettier`:

- `docs/release-notes/upcoming/<folder>.md`, in plain language: a project
  takes its parents' taxonomy and capabilities through its parent links,
  every level up, from each parent whose `inherit` includes them; the
  `extends` settings and commands are gone, and a configuration still
  holding one says what to do; to change one inherited entry, put your own
  at the same path holding only what you change (`tcw capabilities set` does
  this, and `tcw taxonomy add` at an inherited path), and `show`, the JSON
  records and the web app say what it overrides; an entry that overrides
  nothing must have a name, a description file and (for a capability) a
  status, so a leftover change whose original moved is reported; two
  unrelated parents with an entry at one path: the later one is used, whole,
  with a warning, until the project decides with its own complete entry;
  with a parent missing, the project's own entries can still be listed and
  shown, and the commands that need the parent stop with exit code 7;
  capabilities no longer carry a `cap-` id; editing a capability's body in
  the web app changes only its own description, so attached documents are
  no longer copied into it.
- `docs/changelogs/upcoming/<folder>.md`, technical, under **Added**
  (`combine`, `Declaration`, `Combined`, `clash_warning`, `own_paths`,
  `has_own`, `declaration`, `chain`, `inherited_at`, `view_warnings`,
  `override_target`, `removal_target`, `Locator.exists`, `Term.overrides`,
  `Capability.overrides`, `partial`, the `overrides` and `partial` record
  keys, `CapabilityDetail.declared_description` and the
  `declaredDescription` answer key, `InheritedUnavailable`'s `"store"`
  reason and `unavailable(store_message=)`, the 503 answer, Design 6.1, 6.3
  and 6.4 findings), **Changed** (`get_local` and `get_view` over the
  combined view, `Locator.read` and `find_tree` reading an owner as it sees
  itself, `find_tree_writable` returning the active project's target,
  `set`, `reset`, `rm`, `add`, `_merge_meta` writing `null`,
  `update_capability`'s empty body, the web editor's body field, the
  records gate and drift, the validate checks on combined objects, row k
  for capabilities, row m for a nested override, the pre-2.5.0 file's
  message, the lazy view), **Fixed** (a web body edit of a capability with
  attached documents no longer writes them into its description),
  **Removed** (`taxonomy.extends`, `capabilities.extends`, `tcw
  taxonomy|capabilities extends add|rm`, `extends_add`, `extends_remove`,
  `_extends_ids`, `_FederationWalk`, `_FederationCycles`,
  `_extended_component_stores`, `_persist_extends`, `_extends_label`,
  `get_inherited`, `_apply_override`, `_override_index`, `_override_fields`,
  `_set_fields`, `_status_is_local`, `get_by_id`, `_mint_cap_id`,
  `Capability.id`, `AmbiguousRef` for a path, the federation cycle and alias
  collision checks, the `overrides:` pointer checks, the gate's `INHERITED`
  outcome) and **Internal** (the fixtures converted off `extends`, the
  override pointer and `cap-` ids, the record helpers' `complete` argument,
  the static guard, the property test of `combine`). The headings are the
  five `docs/changelogs/upcoming/README.md:12-13` names, **Fixed** among
  them.

**Proves it:** `tests/test_upcoming_entries.py` green;
`tcw work docs` (lifecycle `tcw`) lists no entry this table leaves out.

## Step 24 — the suite as CI runs it

AC 38, done locally as TCW-108 Step 17 does, since CI does not run on
`v4`: bare `.venv/bin/pytest` from the worktree's root, never `python -m
pytest`; `pnpm install --frozen-lockfile` and `pnpm check:build`; and
`pnpm test`, `pnpm exec tsc --noEmit`, `pnpm lint` and `pnpm exec prettier
--check` over every file this item changed or created that
`.prettierignore` does not exclude. The header's three facts re-checked.
A failure is fixed in the step it belongs to, not with a skip.

## Verification the tests cannot do

- **The QA plan's scenarios and its "also checked"** (the five of the spec
  stage and the amendment for Design 4.5's last paragraph), by hand with
  `.venv/bin/tcw` in throwaway projects under the scratchpad (made with
  `tcw init`), with the current folder set there, never in this
  repository.
- **This repository's lifecycle still runs on `v4`** with the lifecycle
  `tcw`: `which tcw`, then `tcw work show TCW-112` and `tcw validate` from
  the worktree after Step 5c and after Step 21.
- **The web app by eye**: `tcw serve` (from `.venv/bin`) in AC 33's `app`,
  in the Claude Chrome instance: the override's entry view says what it
  overrides and saves; an inherited capability it does not override is
  refused as read-only; editing the body of an override whose original has
  attached documents shows only the override's own text in the field,
  with the note, and after saving the page shows the attached text once;
  with `core` moved away, the page reports the 503.
- **`pnpm test:e2e`**, run as the single command `PATH=.venv/bin:$PATH pnpm
  test:e2e`, as TCW-111's plan does, so no lifecycle command inherits that
  `PATH`.

## Self-review against the spec

**Every criterion has a step.** 44 criteria.

| AC | Step | AC | Step | AC | Step |
| --- | --- | --- | --- | --- | --- |
| 1 | 3 | 16 | 13 (all), 16 (drift) | 31 | 16 |
| 2 | 3 | 17 | 3 | 32 | 16 |
| 3 | 3 | 18 | 3 (exit 7, validate), 13 (`--local`) | 33 | 17a |
| 4 | 3 | 19 | 3 | 34 | 15 |
| 5 | 7 | 20 | 8 | 35 | 13 |
| 6 | 7 | 21 | 8 | 36 | 5c |
| 7 | 7 | 22 | 8 | 37 | 5a (scans, sweep), 19 (re-run) |
| 8 | 7 | 23 | 8, 10 (last sentence) | 38 | 24 |
| 9 | 7, 12 (no warning) | 24 | 8 | 39 | 14 |
| 10 | 7 (results), 12 (warnings) | 25 | 8 | 40 | 15 |
| 11 | 7 (`show`), 12 (warning) | 26 | 7 (first four), 13 (last three) | 41 | 15 |
| 12 | 12 | 27 | 7 | 42 | 8 (CLI), 15 (validate), 17a (web) |
| 13 | 11 | 28 | 10 | 43 | 12 |
| 14 | 11 | 29 | 9 | 44 | 17b |
| 15 | 5b (commands, methods), 5c (key, variables), 16 (gate) | 30 | 5b (validate), 20 (grep) | | |

**Every design rule has a step:** 1.1-1.2 Step 3; 1.3 Steps 2, 3, 13, 14;
1.4 Step 13; 1.5 Steps 5b, 5c; 2.1-2.6 Steps 1, 7; 2.7 Step 8; 3.1-3.3, 3.6
Step 7 (3.1's existence checks Step 13); 3.2's warnings Step 12; 3.4-3.5
Step 13; 3.7 Step 18; 4.1-4.4 Step 8 (4.4's view-less cases Step 13); 4.5
Steps 17a, 17b; 5 Step 10 (5.1 for `set` in Step 8, which writes no pointer
and no `id`); 6.1 Step 11; 6.2 Steps 7 (references), 15; 6.3 Step 12; 6.4 Step 9; 6.5 Steps
3, 13; 6.6 Steps 5b, 9, 10; 6.7 Step 15; 6.8 Step 5c; 7.1-7.2 Step 16; 7.3
Step 7 (tested in Step 15); 8.1 Steps 5a, 19; 8.2 Step 21. Every step traces back to one of
these or to the lifecycle (Steps 0, 20, 22-24).

**The suite at each step boundary.** Green after every commit, not only
every step. The places the first draft left red, and how each is closed:
Steps 9, 10 and 11 commit the conversion before the check; Step 5a's
documents change before Step 5b removes the commands, and
`tests/test_configuration_text_home.py`'s keys change with the documents;
Step 5b moves every reader of `self.extends` and keeps `_extends_label`
until Step 5c rewrites its last caller; Step 7 checks each own object's
references once, from its declaration, deletes `_override_fields` and
`_set_fields` with their last callers, and re-keys every caller of
`_override_index` by path before deleting it; Step 7 builds an `as_other`
store's sources on first use, so the owner views its own tests read exist
in that step (the re-check's M1); Step 3's tests that Step 7 puts right are
`xfail(strict=True)` between them, Step 6 moves their fixtures by hand
(its hook cannot see them), and `allowed-step7.txt` lists them. Each outcome comparison
is against the previous step's record, so a change of outcome is always
attributable to one step.

**Names.** `get_local`, `get_view`, `own_paths`, `has_own`, `declaration`,
`chain`, `inherited_at`, `view_warnings`, `override_target`,
`removal_target`, `Locator.exists`, `combine`, `Declaration`, `Combined`,
`_sources`, `_source_stores`, `_view`, `_declarations`, `_is_override`
(Step 7 to Step 8 only), `as_other`, `declared_description` /
`declaredDescription` are used with one meaning throughout. `self.extends`
exists only in Steps 3-4 and is `_sources` from Step 5b.

**Citations.** Every `tcw/` line cited was read at `d2d02829` for this
plan; those inside code TCW-108, TCW-110 and TCW-111 rewrite are marked "as
it left it" and are re-found by Step 0.

## Spec defects found while planning

None that block the plan. Three points the implementer should know:

1. **Design 8.1's list of passages is shorter than its sweep's output.** The
   sweep at `d2d02829` also finds `skills/taxonomy/SKILL.md:86`, `:114-115`,
   `skills/capabilities/SKILL.md:94`, `:130`,
   `skills/configure/references/projects.md:6`, `:117`, `:343-371`,
   `docs/guide/multi-repo.md:257-266`,
   `docs/guide/linking-and-validation.md:17`, and five more capability
   descriptions (`validate-capabilities`, `validate-the-taxonomy`,
   `configure-the-capabilities-store-location`, `reference-a-tcw-object`,
   `declare-capability-changes-in-a-child-projects-ledger`). The spec says
   "the plan names every passage it finds", so Step 5a does; the spec's
   list is examples, not a cover, and its rule is right.
2. **`update_capability`'s empty body** (`tcw/store/fs.py:3058-3068`)
   depends on knowing whether the object is an override, which Design 4.2
   removes for `set` but does not mention for the body. Design 2.3 settles
   it (an empty declared description changes nothing in the combination),
   and choice 5 follows from that.
3. **`reset` of another project's full identifier outside the chain** has
   no worded refusal in Design 4.3; choice 9 uses Design 4.2's.

The first draft's third point, that `parent` must leave `_CAP_STRUCTURAL`
for Design 2.2 to hold, was wrong and is withdrawn: `_CAP_STRUCTURAL`
decides what is a `field`, not what combines (Step 7). The web body edit
the first review raised (its D1) was a real gap and is now Design 4.5's
last paragraph and AC 44.

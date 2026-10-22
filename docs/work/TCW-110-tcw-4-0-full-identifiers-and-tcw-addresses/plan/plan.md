# Plan — TCW 4.0: full identifiers and `tcw://` addresses

All work is on the `v4` branch, in the worktree `.claude/worktrees/v4`, with
its own virtual environment (`.venv/bin/pytest`, `.venv/bin/tcw`). File and
line references are to commit `05d42988` on `v4` (the spec's `39603cc4` plus
the spec commits), before TCW-106 finished landing and before TCW-107; Step 0
re-checks them.

Every step ends with the named tests passing, and with the whole Python
suite passing (`.venv/bin/pytest`); a step that touches the web client also
ends with `pnpm test`, `pnpm typecheck` and `pnpm lint` passing and the
bundle rebuilt (`pnpm build`, which writes `tcw/serve/dist`). Tests are
written first and seen to fail for the reason they name, then the change is
made.

**This repository's own lifecycle is driven with the released 3.x `tcw`**
(the one on `PATH`, 3.0.2), never with `.venv/bin/tcw`, from Step 4 on. This
repository's Jira tickets hold 3.x `TCW Item` values (`tcw/TCW-110-…`), which
the 4.0 code leaves out of `tcw work list` (Design 5.2), and a write made with
the 4.0 code would put a 4.0 value on a ticket that the released CLI cannot
read. The spec's Non-goals already keep this repository's records in the 3.x
form until TCW-116.

## Step 0 — start from what TCW-106 and TCW-107 left

TCW-106 (being implemented) and TCW-107 (being planned) land on `v4` before
this step. Both are recorded as blockers on the ticket already.

**Checks**, before any change:

- `FsProjectRegistry.project_folder(project_id, named_by) -> Path` exists in
  `tcw/store/project.py` with TCW-107 Design 2.12's four outcomes: it returns
  the root; raises `Unreachable` (`tcw/errors.py:76-77`); raises
  `UnknownProject`; raises `ProjectGraphError`. The last two are new
  `TcwError` classes in `tcw/errors.py` (TCW-107 Design 2.12), with
  `UnknownProject` a subclass of `ProjectGraphError`.
- `FsProjectRegistry.open(root)` returns one registry per active root for the
  command (TCW-107 Design 2.13), so calling it from several places costs
  nothing.
- `open_project` (`tcw/work/open.py:88-99`) has TCW-107 Design 6.2's messages.
- `tests/projectfiles.py` (TCW-106) and TCW-107's manifest test helper exist;
  this plan writes manifests through TCW-107's helper and names it where a
  step needs one (`write_manifest` below stands for whatever TCW-107 calls it).
- Every file and line this plan cites is re-read, and a citation that moved is
  corrected in this plan before Step 1 (the plan is a document of this item's
  folder, so the correction is part of the item's record).

**Proves it:** bare `.venv/bin/pytest` passes on the merged `v4`, and its
count is recorded in the implement round as the baseline.

## Step 1 — the identifier module

**Creates** `tcw/ids.py`, importing only `tcw.errors` and
`tcw.project_files.KEY_PATTERN` (the project-ID pattern TCW-106 put at
`tcw/project_files.py:42`, the same as `PROJECT_ID_PATTERN`,
`tcw/store/project.py:25`), so every layer can import it. It holds Design 1
and 2 and nothing that reads a disk:

- `NAMESPACES = ("taxonomy", "capabilities", "work")`, `ID_PART` (Design 1.1:
  `[A-Za-z0-9][A-Za-z0-9_-]*`, at most `ID_PART_LIMIT = 128`).
- `FullId`, a frozen, ordered dataclass `(project, namespace, id_path)`.
  Its constructor does not validate, so a folder whose name breaks 1.1 can
  still be printed (Design 1.6); only the parsers refuse. `str()` is
  `<project>.<namespace>/<id_path>`; `address()` is `tcw://` + that;
  `parts` is `id_path.split("/")`, the one place an id-path is split for a
  caller.
- `FolderAddress`, a frozen dataclass `(project, namespace | None,
  folder_path)`, `str()` its one spelling (Design 2.3, trailing `/` kept as
  written), and `same_target(a, b)` comparing with a trailing `/` ignored.
- `IdError(UsageError)` (exit 2) with subclasses `MalformedId` and
  `ThreeXReference`, each message naming the rule broken (AC 1, AC 2).
  `ThreeXReference`'s message for an address is Design 2.4's text exactly;
  for a stored value it is
  `'<value>' is a TCW 3.x reference; TCW 4 writes <project>.<namespace>/<id-path> (run 'tcw migrate' in this project)`.
- `looks_full(text) -> bool`: Design 1.2's test, a `.` before the first `/`.
- `parse_full_id(text, namespace=None) -> FullId`: the grammar of 1.1; with
  `namespace`, a different namespace is a `MalformedId` naming the namespace
  expected (Design 3.1).
- `parse_address(text) -> FullId | FolderAddress`: Design 2.1 and 2.2, each
  refusal with its own message; `tcw://p1/` gets "needs a namespace or
  `.path`" and never the 3.x message; `is_3x_address(text)` is Design 2.4's
  recogniser, the only one in the codebase.
- `parse_stored(value, namespace) -> FullId`: what every reader of a stored
  field calls (Design 5.2). A valid full identifier of that namespace is
  returned; a value with no `.` before its first `/` raises
  `ThreeXReference`; anything else `MalformedId`.
- `Input`, the sorted form of a command argument (Design 3.1), and
  `sort_input(text, namespace, key_pattern=None) -> Input`, pure: form `a`
  (full identifier or its object address), `b` (the whole text matches
  `key_pattern`, work only), `c` (a work full identifier whose one-part
  id-path matches `key_pattern`), `d` (an id-path, every part checked against
  `ID_PART`). The Jira `KEY` pattern (`tcw/work/jira/backend.py:54`) is passed
  in by the work layer, so `tcw/ids.py` imports nothing from `tcw.work`.
- `identity(full_id) -> {"full-id": str, "owner": project}`: the two keys
  every record carries (Design 4.3), so the CLI and the web build them one
  way.

**Creates** `tests/fixtures/tcw-addresses.json`: the accepted and refused
addresses of AC 2, each accepted one with the path text a URL parser must
return (`tcw://p1.path/docs/p2-work` → `/docs/p2-work`), read by both this
step's test and Step 2's.

**Proves it:** new `tests/test_ids.py`: AC 1 (every accepted and refused
identifier, the 129-character id-part, each message naming its rule); AC 2
(every address in the fixture file, `tcw://p1/`'s message not containing
`TCW 3.x reference`, the equal and unequal comparisons, and
`urllib.parse.urlsplit(address).path` equal to the fixture's path for each
accepted address); `sort_input` on every row of Design 3.1's table including
`TCW-120` with and without a key pattern; `parse_stored` on `demo/x`, `term`,
`roles/admin` (each `ThreeXReference`) and `demo.work/x`. Nothing else in the
suite is touched.

## Step 2 — the web client's identifier module

**Creates** `web/client/src/model/identifier.ts`, the client's one parser of
Design 1.1 (spec 4.5): `parseFullId(text)` returning `{project, namespace,
idPath}` or `null`, `fullIdText(project, namespace, idPath)`,
`objectAddress(fullId)` (`tcw://` + text), and `isFullId(text)`.

**Creates** `web/client/src/model/identifier.test.ts`: the accepted and
refused identifiers of AC 1; and, reading
`tests/fixtures/tcw-addresses.json` (imported as JSON from the repository
root), Node's `new URL(address).pathname` equal to each accepted address's
path (the Node half of AC 2, which `tests/test_ids.py` cannot run: the
`pytest` job has no Node, `.github/workflows/test.yml:122-126`).

Nothing uses the module yet. **Proves it:** `pnpm test`.

## Step 3 — one test helper for expected identifiers

**Creates** `tests/fullids.py` with `fid(project, namespace, id_path)` and
`wid(project, folder)` returning the text `tcw.ids.FullId` prints, and
`addr(...)` for its address. The later steps change existing expectations
through these, as TCW-106 did with `tests/projectfiles.py`, and then read
every remaining failure one by one: an assertion is changed only where the
text it checks has legitimately changed form, never to make different
behavior pass (spec Risks, "Test churn").

**Proves it:** imported by Step 4's tests.

## Step 4 — work items are named by their full identifier

This is the largest step: every printed and stored work name changes form
together, because the item record, the backends and the web client all read
one another's output.

**Tests first.** New `tests/work/test_full_identifiers.py`, in a
files-backend project `demo` built with `tests/work/projects.py`'s
`make_project`:

- `tcw work new` prints `demo.work/<folder>` and `tcw work list` prints it
  (AC 4, work).
- `tcw work show <folder>`: first line `full-id: demo.work/<folder>`, second
  `owner: demo`, no `slug:` line (AC 5, work).
- `tcw work list --json` and `show --json`: `"schema": 2`, each record with
  `full-id` and `owner` and no `slug`; `parent`, `blocked-by`, `blocks`,
  `children` full identifiers (AC 6, work).
- `tcw work edit <folder> --parent <other>` and `--blocked-by <other>` write
  `parent: demo.work/<other>` and `blocked-by: [demo.work/<other>]` into
  `item.yaml` (AC 8, work).
- `tcw work show demo.work/<folder>` and `<folder>` show the same item
  (AC 7, first two forms).
- An `item.yaml` holding `parent: demo/<folder>` makes `tcw work list` refuse
  naming the unreadable item, `parent` and `tcw migrate`, and `tcw validate`
  report it so (AC 11, first part).
- A `pre` command binding sees `TCW_SLUG=demo.work/<folder>`;
  `tcw work stage prompt spec <folder>` names `demo.work/<folder>`; a
  `generate:` binding gets `"schema": 2` and `item["full-id"]`, and
  `evals/assets/gen_requirement.py` run on that document prints the marker
  computed from `demo.work/<folder>` (AC 19).

**Changes, Python**

- `tcw/work/model.py`: `Slug` (`:31-75`) becomes `tcw.ids.FullId` with
  namespace `work`: a frozen subclass whose constructor keeps its two
  arguments `(project, folder)`, so the 21 construction sites the sweep lists
  stay as they are, with `folder` reading `id_path`. `__str__` is inherited,
  so every message, `TCW_SLUG` (`tcw/work/advance.py:168`,
  `tcw/work/resolve.py:334`), the stage prompt's `<slug>`
  (`tcw/work/cli.py:517`), the Jira `TCW Item` writes
  (`tcw/work/jira/backend.py:708`, `:893`, `:898`,
  `tcw/work/jira/tickets.py:181`, `:388`) and the `item.yaml` writes
  (`tcw/work/fs_backend.py:180-183`) print the full identifier with no edit of
  their own. `Slug.parse(text, current_project)` (`:42-72`) is split in two:
  `Slug.stored(value)` calls `tcw.ids.parse_stored(value, "work")`, and
  `Slug.typed(text, current_project)` accepts form `a` and a one-part form `d`
  only (keys and the 3.x hint are Step 8's). `_as_slug` (`:155-161`) uses
  `typed`; `FOLDER_PATTERN` (`:28`) stays the folder rule for names a backend
  makes.
- `tcw/work/fs_backend.py:128-132` (`slug()` inside `_load`): `Slug.stored`,
  so a 3.x value is an `Unreadable` naming the key and `tcw migrate`.
- `tcw/work/jira/backend.py:383-389` (`_slug_of`) and
  `tcw/work/jira/tickets.py:233-241` (`_own_slug`): `Slug.stored`, `None` on
  any `IdError` (they never refuse, Design 5.2). `ticket_key` (`:582`):
  `_as_slug`.
- `tcw/work/record.py:25-45` (`item_record`): `**identity(item.slug)` first,
  replacing `"slug"`, so `show`'s text lines (`tcw/work/cli.py:291-298`, which
  print the record's keys in order) start `full-id:`, `owner:`; `path` kept.
- `tcw/output.py:53-61` (`print_json`): `"schema": 2`, with its docstring;
  `tcw/work/resolve.py:308-313`: `"schema": 2`.
- `tcw/work/cli.py`: the `--json` help strings at `:735`, `:843`, `:850`,
  `:873` show `"schema": 2`; `SLUG_HELP` (`:182`) reads "the item: its full
  identifier (`<project>.work/<folder>`), its folder name, or its tracker
  key"; `prints=` at `:708`, `:721`, `:806`, `:876` say "full identifier";
  the `--parent`/`--blocked-by` helps (`:682`, `:684`, `:728`) say "(an item:
  its full identifier or folder name)". The same help strings in
  `tcw/taxonomy/cli.py:146`, `:170`, `:187` and `tcw/capabilities/cli.py:235`,
  `:244`, `:294` move to `"schema": 2` here, since `print_json` does.
- `tcw/serve/work.py`: the board's fallback rows (`:223`), the create answer
  (`:514`), adopt (`:537`) and `_other_items` (`:565-567`) answer
  `full-id` in place of `slug`; `create`'s test of whether delegation made an
  item or a ticket (`:492`, `"/" in made`) becomes `looks_full(made)`;
  `checked_reference` (`:369`) and `add_blocks` (`:450`) use `Slug.typed`
  (Step 8 widens them).
- `evals/assets/gen_requirement.py:38`: reads `item.get("full-id")`.

**Changes, web client** (each `slug` read of a work record becomes
`"full-id"`, and every split goes through `identifier.ts`):

- `web/client/src/model/types.ts:60` (`WorkItem.slug`) and `:82`
  (`TFallbackRow.slug`) become `"full-id"` and `owner`.
- `web/client/src/model/work.ts:7-16` (`folderOf`, `projectOf`) and
  `:113-118` (`isLocal`) parse with `parseFullId`; a bare folder still answers
  itself and `null`; `boardRows` (`:59-82`) builds its fallback record with
  `"full-id"`. `moveHint` (`:120-122`) unchanged (it prints what it is given).
- `web/client/src/ui/work-forms.tsx:227`, `:397` (`currentIdentifier`),
  `:554-569` and `:786-795` (the create answer and `slug.slice(slug.indexOf("/")
  + 1)`): read `"full-id"` and `folderOf`.
- `web/client/src/ui/work-views.tsx:53-74` (`SlugLink`) through the new
  `work.ts`; `:245` builds `fullIdText(project.id, "work", detail.folder)`.
- `web/client/src/model/tree.ts:38-60`, `:175-190` (`buildWorkTree`,
  `workAncestors`) key on `"full-id"`; `web/client/src/ui/app.tsx:456` reads it.
- `web/client/src/model/reference-search.ts:58-73` (`descendantsOf`), `:90`
  (work options) read `"full-id"`; `:267-278` (`SLUG`, `otherProjectWarning`)
  parse with `parseFullId`. The work half of `tcwLinkOptions` (`:247-251`)
  keeps `tcw://W/<folder>` until Step 10.
- `web/client/src/model/api.ts:125-135` (`suggestOtherItems`) reads
  `"full-id"`.
- `web/client/src/ui/shared-components.tsx:325-345`: copies `"full-id"`;
  label "Copy full identifier".
- The client tests that build work records (`web/client/src/test-fixtures.ts`,
  `model/work.test.ts`, `model/tree.test.ts`, `model/reference-search.test.ts`,
  `ui/work-forms.test.tsx`, `ui/work-views.test.tsx`, `ui/app.test.tsx`,
  `ui/shared-components.test.tsx`) move to the new keys. `model/work.test.ts`
  gains AC 20a's `isLocal("demo.work/x", demo)`, `isLocal("core.work/x",
  demo)`, `projectOf("demo.work/x") === "demo"` and `folderOf` of it `x`.
- `pnpm build` rewrites `tcw/serve/dist`.

**Changes, tests.** Every test that compares `<project>/<folder>` text or a
`slug` key, through `tests/fullids.py`; the Jira fake's seeded `TCW Item`
values (`tests/work/jira/`), the memory backend (`tests/work/memory_backend.py`)
and `tests/serve/` records likewise; `tests/test_cli_contract.py:284`, `:346-361`
(renamed `test_every_json_output_is_one_object_with_schema_2`). Expected:
roughly the files `grep -rlE '"slug"|/20[0-9]{2}-' tests` lists.

**Proves it:** `tests/work/test_full_identifiers.py` (AC 4, 5, 6, 7 first two
forms, 8, 11 first part, 19 for work); `web/client/src/model/work.test.ts`
(AC 20a's model half); the whole suite and `pnpm test`.

## Step 5 — a Jira project part way through `tcw migrate`

**Tests first.** New `tests/work/jira/test_jira_full_identifiers.py`, with
the suite's Jira fake (`tests/work/jira/fake.py`):

- AC 9: `tcw work new` sets `TCW Item` to `<project>.work/<KEY>-<words>`;
  `tcw work show <KEY>` shows it (the existing key path,
  `tcw/work/cli.py:56-61`); an item whose parent ticket has no folder here and
  a `TCW Item` of `<project>/<folder>` lists that key under `untracked`.
  (`tcw work show <project>.work/<KEY>` is added to this file in Step 8.)
- AC 9a: two tickets of this project holding the 3.x value, one with a folder
  here and one without: `tcw work list` lists neither, and its standard error
  holds exactly one warning with `2 Jira tickets`, `TCW 3.x TCW Item value`,
  both keys and `tcw migrate`, and no `another copy of this repository`;
  `tcw validate --remote` reports the first at its item and the second at its
  key, each an error with `TCW 3.x value` and `tcw migrate`, and neither as
  `its ticket's TCW Item is … not …`.

**Changes**

- `tcw/work/jira/backend.py:470-482` (`list`): a value for which
  `parse_stored` raises `ThreeXReference` is collected, not warned about one
  by one; after the loop, one warning (Design 5.2's text) when any were
  collected. The "another copy of this repository" warning stays for a 4.0
  value whose folder is not here.
- `tcw/work/jira/remote.py:480-482`: a 3.x `TCW Item` gets Design 5.2's
  message in place of the mismatch; `:490-499`: a ticket whose value is 3.x
  and whose key the first direction did not already report is an error at the
  key, instead of the `continue` at `:494-495`.

**Proves it:** that test file, and `tests/work/jira/test_jira_validate_remote.py`
and `test_jira_list.py` still passing.

## Step 6 — taxonomy entries and capabilities are printed by full identifier

Output only; what commands accept is Step 8's.

**Tests first.** New `tests/test_tree_full_identifiers.py`, project `demo`
with a term `term`, a capability `cli/x`, and a project `core` inherited
through `taxonomy.extends: [core]` and `capabilities.extends: [core]`:

- AC 4: `tcw taxonomy list` prints `demo.taxonomy/term`, `tcw capabilities
  list` prints `demo.capabilities/cli/x`, an inherited entry prints
  `core.taxonomy/<slug>`; `add` prints the new full identifier.
- AC 5: `tcw taxonomy show term` and `tcw capabilities show cli/x` start
  `full-id:`, `owner: demo`, and print no `path:` or `origin:`.
- AC 6: the four `list`/`show --json` documents: each record has `full-id`
  and `owner` and no `path` or `origin`; the `--help` of the six `list` and
  `show` commands shows `"schema": 2` and contains neither `qualified path`
  nor `full slug`.
- `tests/serve/test_full_identifiers.py` (new): `/api/capabilities/<path>`
  and `/api/taxonomy/<slug>` return records with `full-id` and `owner` and no
  `slug`, `qualified` or `path` key (AC 20, first part, taxonomy and
  capabilities; `/api/work/<folder>` is added here for work, already true
  after Step 4).

**Changes, Python**

- `tcw/store/base.py`: `Term` (`:324-343`) and `Capability` (`:483-508`)
  gain `owner: str` and a `full_id` property
  (`FullId(owner, "taxonomy", slug)`, `FullId(owner, "capabilities", path)`);
  `qualified` (`:340-343`, `:505-508`) is deleted. `origin` stays as the
  stores' internal field (the extends ID, or `"local"`), read by the override
  code until TCW-112, and is never printed (Design 1.4).
- `tcw/store/fs.py`: `FsTreeStore` gains `project_id`
  (`FsProjectRegistry.open(self.project_root).current.id`, read once);
  `_term` (`:1731-1746`) and `_capability` (`:2328-2343`) set `owner` to it
  for a local entry and to `origin` for an inherited one. The five messages
  that print `.qualified` (`:1877`, `:2133`, `:2513`, `:2590`, `:2684`) print
  `full_id`.
- `tcw/taxonomy/cli.py`: `_record` (`:31-33`) is `{**identity(term.full_id),
  "name", "kind"}`; `_print_terms` (`:59-65`), `_add` (`:109`) print
  `full_id`; `_show` (`:82-83`) starts `full-id:`, `owner:`; `_ordered`
  (`:49-56`) sorts by `(owner != project, owner, term.full_id.parts)`;
  `prints=` (`:142`, `:151`, `:183`) say "one full identifier per line" and
  "the new entry's full identifier"; the `show` path help (`:168`) reads
  "the entry: its full identifier, or its path in this project"; the module
  docstring (`:3-7`).
- `tcw/capabilities/cli.py`: the same at `:37-39`, `:50-56`, `:75`, `:95`,
  `:173`, `:226`, `:242`, `:251`, `:290`, and the docstring `:3-8`.
- `tcw/serve/records.py:27-37` (`jsonable`): a `Term` or `Capability` is
  serialized with `identity(full_id)` in place of `slug`/`path`/`origin`/
  `qualified`; every other field is unchanged. The two read-only messages
  (`:118`, `:194-196`) print `full_id`.

**Changes, web client**

- `web/client/src/model/types.ts:180-200` (`TaxonomyItem`, `CapabilityItem`):
  `"full-id"` and `owner` replace `slug`, `path`, `qualified`, `origin`.
- `web/client/src/ui/route-utils.ts:18-36` (`itemKey`, `itemTitle`): the
  route key is the id-path of `"full-id"` when its owner is the served
  project, and the whole full identifier for an inherited entry (see "A spec
  gap this plan settles", below). `itemKey` of a work record whose `full-id`
  is `demo.work/x` is `x`, of `demo.capabilities/cli/x` is `cli/x` (AC 20a).
- `web/client/src/model/reference-search.ts:91-96`, `:126-143`, `:146-160`
  (taxonomy, capability, role and condition options) take `"full-id"`;
  the role and condition filter tests the id-path, not `item.path`.
- `web/client/src/ui/content-views.tsx:210-224`, `:258`, `:530` and
  `web/client/src/ui/shared-components.tsx:414`, `:425`: show `"full-id"`,
  and `owner` where `origin` was; "inherited" is `owner !== project.id`.
- `web/client/src/ui/app.tsx:631`: the edit target is `itemKey`.
- `web/client/src/ui/route-utils.test.ts` gains AC 20a's two `itemKey`
  cases; the other client tests move to the new keys. `pnpm build`.

**Server route keys.** `/api/taxonomy/<key>` and `/api/capabilities/<key>`
(`tcw/serve/records.py:244-254`) receive either an id-path or an inherited
entry's full identifier. In this step `get_term_detail`/
`get_capability_detail` receive the full identifier through a small
translation in `records.py` (an inherited `FullId` read with
`get_inherited(owner, id_path)`); Step 8 replaces that with the shared input
sorter.

**Proves it:** both new test files; `tests/test_taxonomy_cli_contract.py`,
`tests/test_capabilities_cli_contract.py`, `tests/serve/test_records.py`
moved to the new forms; `pnpm test`.

## Step 7 — finding the owner of a full identifier

**Tests first.** New `tests/test_locate.py`, two git repositories side by
side under `tmp_path` (`app`, `core`), `app` naming `core` under
`projects.upstream` (the relation needing no reciprocity) and no `extends`:

- `Locator(app).owner_root("core", named_by=app)` returns `core`'s root;
  with `core`'s folder removed it raises `Unreachable`; for `cor` (named by
  nothing, nothing next to `app` declares it) `UnknownProject` with `no
  project with ID 'cor' is known or found near this one; check the
  spelling`; with two folders next to `app` declaring `id: lib` (named by
  nothing in `projects:`) `ProjectGraphError` naming both folders.
- `owner_root(<app's own id>, app)` returns `app` without a lookup.
- `read(FullId("core", "taxonomy", "term"), named_by=app)` returns `core`'s
  own `term`; `core.taxonomy/missing` returns not found; with `app` extending
  `core`, it returns `term` as `app` sees it, override applied (Design 6.2).
- Work: `read(FullId("core", "work", <folder>), app)` reads through `core`'s
  backend; a Jira-mode `core` is answered by `link_exists`, with no request.

**Creates** `tcw/locate.py` (the deployment layer: it is the one module
outside `tcw/store/` that turns a project ID into a folder, by calling
TCW-107's function):

- `Outcome`, `(kind, value, message)` with `kind` one of `found`, `missing`,
  `unresolved`, `error` (spec 6.3's four answers).
- `Locator(active_root)`: holds `FsProjectRegistry.open(active_root)` and a
  cache of opened stores by `(project, namespace)`.
  `owner_root(project_id, named_by)` calls
  `registry.project_folder(project_id, named_by)` and lets its four outcomes
  propagate; `outcome_of(error)` maps `Unreachable` to `unresolved` and
  `ProjectGraphError` (and its subclass) to `error`, carrying the message,
  for callers that report rather than stop.
- `read(full_id, named_by) -> Outcome`: Design 6.2. Owner is the active
  project → its own store's `get_local` (`tcw/store/fs.py:1748-1761`,
  `:2391-2399`). Owner in the active store's `_inherited_stores()`
  (`:1771-1783`; `self.extends` for capabilities, `:2409-2423`) →
  `get_inherited(owner, id_path)` (`:1819-1821`, `:2442-2447`), the
  active project's view. Otherwise → the owner's store for the namespace,
  opened from the owner's root, `get_local` only, so another project's
  inherited objects are never reached. Work → the owner's backend `read`, or
  `link_exists` for a Jira backend (as `tcw/refs.py:144-153` does today).

**Changes**

- `tcw/work/open.py:88-99` (`open_project`): locates the project with
  `project_folder(project_id, here)`, so any project TCW can locate opens,
  not only one `projects:` names (Design 6.1); `UnknownProject` and
  `ProjectGraphError` propagate (exit 1), `Unreachable` keeps exit 5.
- `tcw/work/open.py:210-241` (`reference_resolver`) and
  `tcw/work/references.py:13-67`: a new answer `ERROR` carrying the message,
  for `ProjectGraphError` and `UnknownProject`, reported as an `error`
  finding naming the reference; `unresolved` stays for `Unreachable`.
  (`reference_problems`'s `Problem.level` gains `"error"`.)

**Proves it:** `tests/test_locate.py`; `tests/work/test_open.py` and
`tests/work/test_references.py` gain the `UnknownProject` cases.

## Step 8 — what commands accept

**Tests first**, added to `tests/work/test_full_identifiers.py` and
`tests/test_tree_full_identifiers.py`, and to
`tests/work/jira/test_jira_full_identifiers.py`:

- AC 7: `tcw work show tcw://demo.work/<folder>` shows the item;
  `tcw capabilities show demo.capabilities/cli/x` and `cli/x` show the same
  capability; `tcw work show demo.taxonomy/term` exits 2 naming `work`;
  `tcw work show demo/<folder>` exits 4 and its message contains
  `write demo.work/<folder>`; `tcw work list --parent demo.work/<folder>` and
  `tcw work edit <other> --blocks demo.work/<folder>` accept it.
- AC 9 (rest): `tcw work show <project>.work/<KEY>` shows the item.
- AC 10: in a files project, `tcw work show TCW-120` exits 4 with the same
  message as `tcw work show 2026-01-01-nothing` with the folder name swapped;
  and the fall-through itself is checked through `resolve_work_input` with a
  backend whose `lookup` answers None (see "Spec defects", AC 10).
- AC 13a (command half): `tcw taxonomy show cor.taxonomy/term` exits 1 with
  `check the spelling`; with two sibling folders declaring `id: lib`,
  `tcw taxonomy show lib.taxonomy/term` exits 1.
- AC 18: `tcw capabilities add 'cli/has.dot'` exits 2 and writes nothing; a
  hand-made `cli/has.dot` folder is listed as `demo.capabilities/cli/has.dot`,
  reported by `tcw validate` as an error naming the folder and saying it must
  be renamed by hand; `tcw capabilities show cli/has.dot` exits 2 naming the
  rule.
- AC 23 (first three parts): `app` extending `core`, `core`'s `cli/x` at
  `Missing`, `app`'s 3.x override setting `Supported`: `capabilities list
  --json` and `show core.capabilities/cli/x --json` both give `Supported`;
  `set core.capabilities/cli/x --status Partial` changes `app`'s override and
  leaves `core`'s `meta.yaml` byte for byte.
- AC 25: `tcw capabilities show Cli/x` and `show demo.capabilities/Cli/x`
  exit 4 on any disk, and on a disk that ignores case (skipped elsewhere,
  detected by writing a file and statting its upper-case name) the message
  names `cli/x`; `tcw work edit <folder> --parent <OTHER>`, where only
  `<other>` exists, exits 4 and leaves `item.yaml` unchanged.
- A foreign owner refuses writes: `tcw capabilities set core.capabilities/cli/x`
  in `app` when `app` does not extend `core` exits 3, naming `core`.

**Changes**

- `tcw/store/fs.py`: a new `exact_child(parent, name) -> bool | str`
  answering `True` when `name` is in `os.listdir(parent)` as written, and the
  on-disk spelling when it differs only in case; `exact_path(root, id_path)`
  walks it part by part. Used by `FsTaxonomyStore.get_local` (`:1748-1761`),
  `FsCapabilitiesStore.get_local` (`:2391-2399`),
  `FsWorkBackend._folder` (`tcw/work/fs_backend.py:258-262`), and
  `JiraBackend._key` (`tcw/work/jira/backend.py:327-331`), whose not-found
  messages name the spelling on disk (Design 1.1).
- `tcw/store/fs.py`: `get` (`:1799-1817`, `:2425-2440`) is split: a new
  `get_view(id_path)` is the bare-wins-local-then-inherited lookup with no
  prefix branch (form `d`); the old `get`, prefix branch included, is renamed
  `_get_3x` and kept only for the stored-reference readers Step 9 replaces.
- `tcw/locate.py`: `find_tree(store, namespace, text) -> Term | Capability`:
  `sort_input`, then form `a` → own owner `get_local`, inherited owner
  `get_inherited`, other owner `Locator.read`; form `d` → `get_view`. A
  multi-part id-path not found whose first part is a project ID `owner_root`
  finds adds Design 3.4's hint. `find_tree_writable(...)` refuses a foreign
  owner (`Refused`, exit 3, "belongs to project '<id>'; change it there"),
  like `_own` for work (`tcw/work/cli.py:69-74`).
- `tcw/work/open.py`: `resolve_work_input(text, backend, root) -> (Slug,
  backend)`: `sort_input(text, "work", KEY)`; form `b` → `backend.lookup`,
  `None` falls through to the folder of that name (Design 3.2); form `c` →
  the named project's backend (`open_project`) `lookup`, then the same fall
  through; forms `a` and `d` as Step 4; the 3.4 hint for a two-part `d`.
- `tcw/work/cli.py`: `resolve_item` (`:50-66`) calls `resolve_work_input`;
  `_new` (`:186-232`) and `_edit` (`:328-361`) turn `--parent`,
  `--blocked-by`, `--unblocked-by` and `--blocks` (`:339`) into `Slug`s
  through it before building `Changes`, each one read from its owner's
  backend, so a misspelt or wrong-case one exits 4 before anything is
  written (AC 25); `_list --parent` (`:247`) likewise. What is stored is the
  `Slug`'s folder as the backend answered it (Design 3.3).
- `tcw/taxonomy/cli.py:42-46` (`_get`), `:113-120` (`_rm`), and
  `tcw/capabilities/cli.py:68-71`, `:119-144` (`show`, `set`, `reset`, `rm`):
  through `find_tree` / `find_tree_writable`; the stores' `remove`, `set`,
  `reset`, `update_term`, `update_capability` and `_write_target`
  (`tcw/store/fs.py:1867`, `:2502`, `:2576`, `:2707`, `:2124`, `:3031`,
  `:2655-2691`) take the object found rather than re-reading the text, so
  `set core.capabilities/cli/x` reaches `_write_target`'s override branch as
  `core/cli/x` does today.
- Names that break 1.1 (Design 1.6): `FsCapabilitiesStore.add`
  (`:2472-2500`) and `FsTaxonomyStore.add` (`:1830-1866`, slug and parent)
  check each part against `ID_PART` before writing (exit 2), which covers
  their web routes (`tcw/serve/records.py:82-103`, `:161-178`); both
  `check()`s (`:2044-2084`, `:2761-2882`) report every local folder whose
  name breaks it, as an error naming the folder, the allowed characters and
  "rename it by hand".
- `tcw/serve/work.py:365-377` (`checked_reference`), `:440-459`
  (`add_blocks`), and the edit and create paths that build `Changes` from text
  (`parse_changes`, `:332-362`): through `resolve_work_input`, so a web write
  stores a full identifier however it was typed (Design 3.1, 3.3).
- `tcw/serve/records.py`: the route key of `/api/taxonomy/<key>` and
  `/api/capabilities/<key>` goes through `find_tree`, replacing Step 6's
  translation.

**Proves it:** the tests above; `tests/test_override_letter_case.py`,
`tests/test_store_bounds.py`, `tests/test_capabilities_federation.py` (which
use the alias-prefixed `core/…` input today) moved to `core.<namespace>/…`.

## Step 9 — references stored in taxonomy and capability records

**Tests first.** New `tests/test_stored_references.py`:

- AC 8 (tree part): `tcw capabilities set cli/x --field Subject=term` writes
  `Subject: [demo.taxonomy/term]`; `tcw taxonomy add Pay --kind feature
  --vocab term` writes `vocabulary: [demo.taxonomy/term]`; a `PATCH
  /api/taxonomy/<slug>` with `relatesTo: ["term"]` writes
  `relatesTo: [demo.taxonomy/term]` (see "Spec defects", AC 8).
- AC 11 (second part): a capability whose `meta.yaml` says `Subject: [term]`
  is reported by `tcw validate` naming `Subject` and `tcw migrate`; the same
  for `relatesTo`, `Feature`, `Roles: roles/x` and `Blocked by`.
- A reference into a project `app` does not extend:
  `Subject: [core.taxonomy/term]` passes `tcw validate`;
  `core.taxonomy/missing` fails it; with `core` removed it is `unresolved`
  and the run exits 0 (Design 6.3, all namespaces).
- `Roles: [!demo.capabilities/roles/admin]` keeps its negation and is checked.

**Changes**, all in `tcw/store/fs.py`, every read of a stored reference
through one method per store, `_stored_ref(value, namespace) -> Outcome`:
`parse_stored`, then `Locator.read` with `named_by` the store's project root
(a `ThreeXReference` or `MalformedId` becomes an `error` outcome with its
message):

- Taxonomy: `_ref_problem` (`:1992-2009`), `_require_ref` (`:2011-2020`),
  `_resolve_vocab_ref` (`:2022-2042`, which keeps its leaf-slug convenience
  for input and stores the full identifier), `check`'s `relatesTo` and
  `vocabulary` loops (`:2066-2083`), `_referrers` (`:1937-1961`),
  `_capability_referrers` (`:1899-1935`), `update_term`'s validation and
  write (`:2124-2196`: values given in any input form of 3.1 are stored as
  full identifiers).
- Capabilities: `_validate_fields` (`:2602-2637`: `Subject`, `Feature`,
  `Superseded by`, `Blocked by`, `Roles`, `When` written as full
  identifiers), `_ref_problems` (`:2934-2948`), `_ref_error` (`:2950-2956`),
  `_check_globals` (`:2958-2969`: "must be a roles/ path" tests the
  id-path's first part, the `!` kept outside the identifier), `_term_refs`
  (`:2971-2983`), `_check_subject` (`:2985-2996`), `_check_feature`
  (`:2998-3014`), `_referrers` (`:2536-2574`, `tokens` reading full
  identifiers).
- An `unresolved` outcome is reported as an `unresolved` finding (both
  `check()`s today create only `error` findings, `:2068-2069`, `:2812-2813`);
  `tcw validate` already counts `unresolved` as not failing.
- `_get_3x` (Step 8) is deleted, with the prefix branches it held
  (`:1801-1803`, `:2426-2428`).
- `tcw/serve/records.py:130-146` (`_subjects_are_vocabulary`): through
  `_stored_ref` after the store has normalised the value.

The `project ID '<id>' collides with local top-level term/capability`
findings (`:2046-2052`, `:2779-2785`) stay: they protect the 3.x override
folders at `<alias>/<path>` (`:2676-2681`) until TCW-112. The `overrides:`
pointer and its check (`:2912-2932`) are untouched (spec Non-goals).

**Proves it:** `tests/test_stored_references.py`; `tests/test_taxonomy.py`,
`tests/test_capabilities.py`, `tests/test_override_references.py`,
`tests/test_capability_ref_wording.py`, `tests/test_taxonomy_rm_gaps.py`,
`tests/test_capabilities_rm.py` moved to stored full identifiers; their
fixtures' `meta.yaml` values written through `tests/fullids.py`.

## Step 10 — `tcw://` links

**Tests first.** New `tests/test_links_full_identifiers.py`:

- AC 3: a description linking `[x](tcw://C/cli/x)` makes `tcw validate`
  exit 1 with an error containing `TCW 3.x reference` and `tcw migrate`; the
  same for `tcw://W/<folder>` and `tcw://core/T/term`.
- AC 13: `app` and `core` in two repositories side by side, `core` named
  under `projects.upstream`, no `extends`: `[t](tcw://core.taxonomy/term)` in
  `app` passes; `tcw://core.taxonomy/missing` fails; with `core`'s folder
  removed the first is `unresolved` and the run exits 0.
- AC 13a (validate half): `[t](tcw://cor.taxonomy/term)` exits 1 with an error
  at the link containing `no project with ID 'cor'` and `check the
  spelling`; `[t](tcw://lib.taxonomy/term)` with two siblings declaring
  `id: lib` reports an error at the link naming both folders.
- A folder address in a link (`tcw://core.path/docs`) is checked for form and
  that `core` can be located, not for the folder (Design 6.4).
- AC 20 (rest), in `tests/serve/test_full_identifiers.py`: `/api/resolve` for
  `tcw://core.taxonomy/term` from `app` answers `other-project` with `core`;
  for an own object `ok` with the id-path as `key`; for an inherited one `ok`
  with its full identifier as `key` (the route key of Step 6).
- `web/client/src/model/reference-search.test.ts`: `tcwLinkOptions` offers
  `tcw://demo.work/<folder>`, `tcw://demo.taxonomy/term` and
  `tcw://demo.capabilities/cli/x` (AC 20).

**Changes**

- `tcw/refs.py` is rewritten: `parse_tcw_uri` (`:59-81`), `TcwRef`
  (`:29-33`) and `_resolve_work`'s two spellings (`:126-162`) are deleted;
  `resolve_tcw_ref(project_root, uri)` (`:84-123`) becomes
  `resolve_address(project_root, uri) -> ResolveResult`: `parse_address`
  (`is_3x_address` first, for Design 2.4's message), then `Locator.read` for
  an object address and `owner_root` for a folder address. `ResolveResult`
  (`:36-48`) keeps `ok`, `reason`, `archived`, `resolution`; `axis` becomes
  `namespace`, `key` the route key, `project` the owner when it is neither
  the served project nor inherited. The module docstring (`:1-15`) states the
  4.0 grammar.
- `tcw/validate.py:327-346` (link loop, `:335`): `resolve_address`; an `unresolved`
  outcome is an `unresolved` finding, an `error` one an `error`, as today's
  `partition("unresolved: ")` split (`:339-346`) did for work only.
  `_LINK_RE` (`:49`) unchanged (it finds `](tcw://…)`).
- `tcw/serve/records.py:210-241` (`resolve`): from `ResolveResult`'s owner and
  route key; `AXIS_WORD` (`:20-21`) is deleted, the namespace word coming
  from the address.
- `web/client/src/model/reference-search.ts:242-258` (`tcwLinkOptions`):
  `objectAddress(item["full-id"])` for all three namespaces; the docstring
  says so. `web/client/src/ui/link-context.ts` and
  `web/client/src/ui/shared-components.tsx:446-470` need no change (they read
  `tcw://` text as typed). `pnpm build`.
- `tcw/store/base.py:488`: the docstring's "a `tcw://` reference points at"
  the opaque `id` is corrected (a link names the full identifier).

**Proves it:** that file, `tests/test_refs.py` and
`tests/work/test_refs_work.py` rewritten for the 4.0 grammar (the 3.x cases
kept as "recognised and refused"), `tests/test_validate.py`'s link tests,
`pnpm test`.

## Step 11 — `capabilities.yaml` entries name their ledger

**Tests first**, in `tests/work/test_gates.py`:

- AC 11 (third part): an item's `capabilities.yaml` entry `cli/x` is refused
  by the records gate (`tcw work advance --dry-run` into review) naming
  `tcw migrate`.
- AC 12: `app` with a child `server` holding `x`:
  `changed: [server.capabilities/x]` passes the gate; with `server`'s folder
  removed it is "could not check"; `app.capabilities/x` with no such
  capability in `app` fails.
- AC 23 (last part): `app` extending `core`, `changed:
  [core.capabilities/cli/x]`: `route_capability_path`'s answer is `app`'s own
  ledger (a unit test of the function), and the gate reads `app`'s override.
- `taxonomy: changed: [core.taxonomy/term]` is checked against `core`'s own
  taxonomy when `app` does not extend it.

**Changes**

- `tcw/work/gates.py:331-380` (`route_capability_path`): routes by the
  entry's full identifier. `parse_stored(path, "capabilities")` (a 3.x or
  malformed entry is a problem line naming `tcw migrate`); owner is the item's
  project → its own ledger; owner in `own.extends` → its own ledger, path
  `<owner>/<id-path>` handed to `get_inherited` (rule 1 today,
  `:354-355`); any other owner → that project's ledger, located with
  `Locator.owner_root(owner, project_root)`, whose `Unreachable` becomes an
  `Unchecked` and whose `ProjectGraphError` a problem. The first-folder rule
  and its ambiguity refusal (`:356-375`) are deleted (UC-3). `Route`
  (`:321-328`) carries the `FullId`.
- `tcw/work/gates.py:390-447` (`_LedgerReader`): `capability`, `removal` (the
  `partition("/")` at `:423` becomes "owner is in `extends`") and `term`
  (through `parse_stored` and `Locator.read`, so a term in a project not
  extended is found).
- `tcw/work/gates.py:450-483` (`project_reader`): `open_child` becomes the
  `Locator`; `registry.declared_child_ids()` is no longer asked.
- `tcw/work/gates.py:101-148` (`parse_declarations`) unchanged: it reads
  strings; the routing judges them.
- `evals/seed_fixture.py:669-670` and `:700-701`: write
  `demo-app.capabilities/billing/download-invoice` and
  `demo-app.capabilities/reports/view` (`PROJECT_ID`, `:66`).

**Proves it:** `tests/work/test_gates.py`, `tests/work/test_drift_work.py`,
`tests/test_routing_nodes.py` moved to full-identifier entries;
`tests/test_eval_fixture.py`.

## Step 12 — a plain store location is relative

The riskiest part of Design 7 is the address resolution of Step 13; this step
first moves every fixture off absolute store paths, so Step 13 changes only
resolution.

**Tests first.** New `tests/test_store_addresses.py`:

- AC 24: in `app`'s `.tcw/tcw-config.yaml`, each of `work.path: /tmp/x` and
  `work.path: ~/x` makes `tcw work list` exit 1 and `tcw validate` report an
  error at `work.path` containing `relative to the project`, `tcw://` and
  `.tcw/tcw-manifest.local.yaml`; the same for `taxonomy.path` and
  `capabilities.path`. `tcw init --work-path /abs` exits 2 with the same text
  and writes nothing.

**Changes**

- `tcw/config.py`, in `load_config` after `_list_problems` (`:606`): a
  `_store_location_problems(raw, project, shown)` adds a `Problem` at
  `(<c>, "path")` for an absolute or `~` value in the shared file, with
  Design 7.1's message. `tcw/cli.py:657-661` then stops every command
  (exit 1) and `config_findings` (`tcw/validate.py:361-381`) reports it.
- `tcw/store/fs.py:616-662` (`init`): a `--work-path` (`tcw/cli.py`'s `init`
  parser) or `paths` value that is absolute or starts with `~` is refused
  before anything is written.
- Tests that place a store at an absolute temporary path (expected among
  `tests/test_store_provisioning.py`, `tests/test_validate_moved_stores.py`,
  `tests/test_init_configured_tree_path.py`, `tests/test_worktree_sibling_nodes.py`,
  `tests/test_project_graph_paths.py`, `tests/work/test_init_provision.py`;
  the list is `grep -rlnE "\.path['\"]?: *['\"]?(/|~|\{tmp|str\(tmp)" tests`)
  write a relative path instead (spec Risks).

**Proves it:** the AC 24 tests and the whole suite.

## Step 13 — folder addresses as store locations, and loops

**Tests first**, in `tests/test_store_addresses.py`, each fixture a set of
git repositories side by side under `tmp_path`:

- AC 14: `app` with `work.path: tcw://workspace.path/docs/app/work`,
  `workspace` and `app` not connected and without manifests: `tcw work new` in
  `app` creates the folder under `<workspace>/docs/app/work/`, prints
  `app.work/<folder>`, and `tcw work path <folder>` prints that folder, and
  `tcw validate` in `app` passes; `tcw://workspace.work.path/../app` is
  refused by `tcw validate` and `tcw work list` with the `..` rule.
- AC 15: `work.path: tcw://workspace.work.path/app` resolves to
  `<workspace's work store>/app`; `p2` → `tcw://p1.work.path/x` and `p1` →
  `tcw://p2.work.path/y` make `tcw work list` in `p2` exit 1 with
  `store locations loop: p2 work -> p1 work -> p2 work`; `work.path:
  tcw://p2.work.path/x` in `p2` fails the same way. (The nesting half is
  Step 14's.)
- AC 17: `work.path: tcw://gone.path/w` with `app`'s `.tcw/tcw-manifest.yaml`
  placing `gone` at `../gone` (absent) and no `work.repository`:
  `tcw work list` exits 5 naming `gone`; `tcw://gonne.path/w`: exit 1 with
  `check the spelling`; the same `gone` address with a `work.repository`
  declared falls through to the provisioned copy (rule 2) as today.
- An object address as a location (`work.path: tcw://app.work/x`) is refused
  naming the `.path` form.
- `tcw://app.path/docs/work` in `app`'s own file names the same folder as
  `docs/work`.

**Changes**

- `tcw/store/fs.py`: one function, `store_location(project_root, component,
  configured, *, chain=()) -> Path` (Design 7.5), holding what both
  `_local_root` hooks do today (`:86-92`, `:1311-1320`): `None` → the default
  `docs/<component>`; a plain path → `anchor_configured_path(...) / value`
  (`:1212-1247`, unchanged); an address → `parse_address`; an object address
  is a `StoreDeclarationError` naming `.path`; a folder address resolves by
  Design 7.2 with `FsProjectRegistry.open(project_root).project_folder(id,
  project_root)` (the project whose file holds the address is that
  registry's own project, so 2.12's `named_by` rule holds); step 3 reads the
  named project's own configuration (`load_config(root / SENTINEL)`, no
  personal layers) and recurses with `chain + ((W, component),)`; a pair
  already in `chain` is a `StoreDeclarationError` with Design 7.3's text.
  `Unreachable` from the lookup becomes a new
  `LocationProjectAbsent(StoreLocationUnusable)` carrying its message;
  `ProjectGraphError` propagates.
- Both `_local_root` hooks call `store_location`; `resolve_store`
  (`:3182-3318`): at rule 4 (`:3248-3261`), a `LocationProjectAbsent` with no
  declaration raises `Unreachable` with its message (exit 5); with a
  declaration, rules 1.5 to 3 answer as today, since it is a
  `StoreLocationUnusable`.
- `init` (`:653-662`, `:704-712`): the configured text is turned into a
  folder by `store_location` for every component, the work one included,
  replacing `Path(configured_path).expanduser()` and the `is_absolute()`
  branch; `tree_store_present` (`:382-404`): its default folder is
  `store_location(project_root, component, None)`, so the default lives in
  one place (it answers presence from configuration, so it resolves no
  address).
- `tcw/validate.py:179-232` (`_configured_path_problem`), `:153`
  (`_claims_work`), `:156-160` (`_work_root`), `:241-266` (`_run_check`):
  catch `Unreachable` as an `unresolved` finding at the key and
  `ProjectGraphError` as an `error` at the key (Design 7.2), instead of
  letting either stop the run.
- `tcw/work/open.py:54-78` (`open_backend`): `Unreachable` and
  `ProjectGraphError` from `work_path` propagate (they are not `ValueError`),
  so exit 5 and exit 1 reach the command.

**Proves it:** the tests above; `tests/test_validate_moved_stores.py`,
`tests/test_store_provisioning.py`.

## Step 14 — stores never nest or coincide

**Tests first**, in `tests/test_store_addresses.py`:

- AC 15 (nesting half): `tcw validate` in `app` fails
  `tcw://workspace.work.path/app` as nested inside `workspace`'s work store.
- AC 16: fails when `app`'s `work.path` names `workspace`'s work store through
  `../workspace/docs/work` and through a relative path to a symlink of it, and
  when `app`'s `taxonomy.path` lies inside its own `capabilities.path`;
  passes when `app`'s store is a sibling of `workspace`'s work store inside
  `workspace`.
- A git worktree of `app` next to it is one project and not compared with
  itself (S-4).

**Changes**

- `tcw/validate.py:677-703` (`_shared_work_paths`) is replaced by
  `_store_overlaps(registry, project_root)`: the stores of the active project
  and of every project its registry connects (`registry.current`,
  `ancestors()`, `descendants()` and upstreams) and every project named by
  one of their store addresses, each project once by ID; for each, the
  folder `store_location` gives for each component, when it exists. Any two
  that are the same folder (`_same_folder`, `tcw/store/fs.py:595-602`) or one
  inside the other (`_in_folder`, `:605-613`, bounded by the folder's own
  filesystem root) are an error naming both stores, their projects and
  folders. The call at `tcw/validate.py:403-405` stays where it is (it
  returns early, as today).

**Proves it:** the tests above; `tests/test_validate.py`'s old
`_shared_work_paths` tests reworded to the new message.

## Step 15 — the sweep, and a guard that keeps it swept

**Creates** `tests/test_identifier_sweep.py` (AC 21): over the `.py`, `.ts`,
`.tsx` and `.mjs` files under `tcw/`, `web/client/src/`, `scripts/` and
`evals/`, test files and `tcw/serve/dist` excepted, no match of
`parse_tcw_uri`, `.qualified`, `tcw://W/`, `tcw://T/` or `tcw://C/` outside
`tcw/ids.py` (the 3.x recogniser, Design 2.4). Mutation-checked: put
`.qualified` back in one file, see it fail and name the file.

**The split sites.** A fresh search (`(r?partition|r?split)\("/"…`,
`"/" in `, `indexOf("/")`, `lastIndexOf("/")`, `split("/")`) over those
folders at `05d42988` finds these, each with what this plan does to it.
The reviewer repeats the search on the finished change and checks it against
this list.

| Hit | What it splits | Disposition |
| --- | --- | --- |
| `tcw/refs.py:71` | a 3.x link | deleted, Step 10 |
| `tcw/refs.py:135-136` | a 3.x work ref | deleted, Step 10 |
| `tcw/work/model.py:52` | a 3.x slug | replaced by `tcw/ids.py`, Step 4 |
| `tcw/work/gates.py:353` | a `capabilities.yaml` entry's first folder | deleted, Step 11 |
| `tcw/work/gates.py:423` | the same, for removals | replaced by an owner test, Step 11 |
| `tcw/store/fs.py:1801` | the 3.x alias prefix (taxonomy `get`) | deleted, Steps 8-9 |
| `tcw/store/fs.py:2426` | the 3.x alias prefix (capabilities `get`) | deleted, Steps 8-9 |
| `tcw/serve/work.py:492` | delegation's answer | `looks_full`, Step 4 |
| `tcw/store/fs.py:2914-2915` | the 3.x `overrides:` pointer `<alias>/<cap-id>` | kept: the pointer is out of scope until TCW-112 (spec Non-goals); it is neither an identifier nor a link |
| `tcw/store/fs.py:1136` | an id-path, in `_safe_store_id` | kept: an id-path already separated |
| `tcw/store/fs.py:1736`, `:2336`, `:2487` | an id-path's last part, for a display name | kept: id-path |
| `tcw/store/fs.py:2035` | an id-path's last part (`--vocab` leaf input) | kept: id-path |
| `tcw/store/fs.py:2046`, `:2779` | an id-path's first part (collision check) | kept: id-path |
| `tcw/store/fs.py:2420` | an id-path's first part (`--namespace` filter) | kept: id-path |
| `tcw/taxonomy/cli.py:56` | an id-path, for sorting | becomes `full_id.parts`, Step 6 |
| `tcw/validate.py:500` | a work folder name (one part until TCW-111) | kept: id-path |
| `tcw/work/fs_backend.py:260`, `tcw/work/jira/backend.py:329` | a folder name | kept: id-path |
| `tcw/serve/files.py:136` | a file path inside an item | kept: path on disk |
| `tcw/store/checkouts.py:53` | a repository URL | kept: URL |
| `web/client/src/model/work.ts:9`, `:14` | a slug | replaced by `identifier.ts`, Step 4 |
| `web/client/src/ui/work-forms.tsx:795` | a slug | replaced, Step 4 |
| `web/client/src/model/reference-search.ts:247` | a slug, for a 3.x link | deleted, Step 10 |
| `web/client/src/model/reference-search.ts:230`, `:234` | a typed capability id-path, one segment at a time | kept: id-path (its source becomes the id-path of `full-id`, Step 6) |
| `web/client/src/ui/route-utils.ts:41`, `:48` | a URL path of the page | kept: URL |
| `web/client/src/model/api.ts:91` | a file path inside an item | kept: path on disk |
| `web/client/src/ui/work-document-tabs.tsx:133` | a file path inside an item (`<stage>/<file>`) | kept: path on disk |
| `web/client/src/model/tree.ts:16`, `:30`, `:169` | a route key | kept: an id-path for the served project's objects. For an inherited entry the route key is its full identifier (Step 6), and the tree shows `<project>.<namespace>` as one top node; the identifier is never rebuilt from the pieces. This is the one hit that is not strictly one of AC 21's three kinds, and the reviewer is asked to accept or reject it (see "A spec gap this plan settles") |

Related hits that test a leading `/` rather than split (`tcw/cli.py:463`,
`tcw/serve/server.py:284`, `tcw/store/base.py:850`, `:981`) are paths on disk
or URLs, and are kept. `scripts/` and `evals/` hold no hit;
`scripts/require_artifact.py` passes `TCW_SLUG` to `tcw work path` and needs
no change (form `a`); `evals/grade.py` compares what `tcw work list` and
`new` print with each other and needs none.

**Proves it:** `tests/test_identifier_sweep.py`, and the table re-checked.

## Step 16 — this repository's records

In this repository's ledgers, in their 3.x form (TCW-116 converts them), so
the released CLI can still read them:

- New `docs/capabilities/cli/name-any-tcw-object-by-its-full-identifier/`
  (`meta.yaml`, `description.md`), status `Supported`, `Subject` naming the
  new terms.
- The 15 changed capabilities in `capabilities.yaml`: the sentences the
  spec's "Capability changes" gives each, in its `description.md`.
- New `docs/taxonomy/full-identifier/` and `docs/taxonomy/tcw-address/`;
  `docs/taxonomy/namespace/`, `reference/`,
  `configurable-component-store-location/` descriptions updated.

**Proves it:** with the released 3.x CLI from the worktree: `tcw validate`,
and `tcw work advance TCW-110 --dry-run` at the end of implement (the records
gate). `.venv/bin/tcw` cannot read these 3.x ledgers by design.

## Step 17 — notes for the later children

Comments the dispatching session posts (the text is in the implement round):

- **TCW-111:** `TCW Item` is a single-line field of at most 255 characters;
  a nested id-path can pass it (spec Risks). `exact_path` (Step 8) already
  walks an id-path part by part, for nested items.
- **TCW-112:** the inherited-view rule lives in `tcw/locate.py`
  (`find_tree`, `read`) and `route_capability_path`; the collision findings
  and the `overrides:` pointer were kept for the 3.x override folders.
- **TCW-113:** the web route key of an inherited entry is its full
  identifier, and `/api/resolve` answers `ok` for one (Step 6, Step 10).
- **TCW-116:** report absolute and `~` store paths, names that break 1.1,
  3.x `TCW Item` values, stores that nest or coincide; this repository's own
  links and `capabilities.yaml` files; `RESERVED_PROJECT_IDS`
  (`tcw/store/project.py:26`) still holds the 3.x axis letters `t`, `c`, `w`,
  which the 4.0 grammar no longer needs reserved.
- **TCW-117:** every JSON document is `"schema": 2`, which
  `docs/guide/cli.md`, `docs/guide/configuration.md` and
  `skills/configure/references/work.md` still show as 1; and
  `tcw/work/procedures/pause-work.md:22` teaches bare slugs.

## Step 18 — Documentation Sync

Each documentation entry, evaluated with the `documentation-sync` skill:

| Entry | Fires? | Answer |
| --- | --- | --- |
| `README.md` [Public-API] | yes: every printed name, `tcw://` links, store locations | Deferred to TCW-117, which rewrites the user-facing documents for 4.0 in one pass; recorded in the implement round. |
| `docs/guide/jira.md` [Jira-Change] | yes: `TCW Item` holds the full identifier; `tcw work list` leaves 3.x tickets out with a warning | Deferred to TCW-117, as above. |
| `docs/guide/<topic>.md` [Guide-Topic-Change] | yes: linking and validation, multi-repo store locations, the CLI output contract | Deferred to TCW-117. |
| `docs/release-notes/upcoming/<folder>.md` [Public-API] | yes | Written: one name for every record and how to type it; `tcw://` links; JSON `"schema": 2`; store locations as `.path` addresses, and absolute paths refused; stores may not nest; 3.x names reported as needing `tcw migrate`; tickets left out until migrated. |
| `docs/changelogs/upcoming/<folder>.md` [Any-Code-Change] | yes | Written, under Added (`tcw/ids.py`, `tcw/locate.py`, `store_location`, the client's `identifier.ts`), Changed (records, `print_json`, `refs.py`, routing, `open_project`), Removed (`parse_tcw_uri`, `.qualified`, first-folder routing, `_shared_work_paths`), Internal (the sweep guard). |
| `skills/<component>/SKILL.md` [Skill-Driven-Component] | yes: every component's names | Deferred to TCW-117. |
| `skills/configure/references/<document>.md` [Configuration-Key-Change] | yes: `<component>.path` takes a `.path` address and no longer an absolute path | Deferred to TCW-117. |
| `docs/use-cases.md` [Project-Setup-Change] | yes: UC-4's store location, UC-6's gap closed for taxonomy and capability links | Deferred to TCW-117, which owns `docs/use-cases.md` for 4.0. |

The two `upcoming/` files are named
`TCW-110-tcw-4-0-full-identifiers-and-tcw-addresses.md`.

## Step 19 — the suite as CI runs it

Bare `.venv/bin/pytest` from the worktree root, `pnpm check:build` (CI's
`web-build` job: rebuilds and fails if `tcw/serve/dist` differs), and
`pnpm test`, `pnpm typecheck`, `pnpm lint` (AC 22). A failure is fixed in the
step it belongs to, not with a skip.

## Verification the tests cannot do

- The QA plan's nine scenarios, by hand with `.venv/bin/tcw` in throwaway
  folders under the scratchpad, at qa (scenario 7 with the Jira fake only).
- `pnpm test:e2e` (`web/e2e/parity.spec.ts`, which runs the `tcw` first on
  `PATH`) with `.venv/bin` first on `PATH`: its slug and link expectations
  (`:240-250`, `:392`, `:421`, `:497-498`) are moved to full identifiers in
  Step 4 and Step 10, but the suite is not in CI and needs a browser, so it is
  run by hand and its result recorded. This also checks AC 20a's last part,
  the board's link opening `/api/work/<folder>`, in a served page; the
  client test in `ui/app.test.tsx` checks it with a mocked fetch.
- AC 25's case-insensitive half runs only on a disk that ignores case; it is
  run on macOS locally and recorded, since CI's Linux skips it.
- That this repository's lifecycle still runs on `v4` with the released 3.x
  CLI after Step 4: `tcw work show TCW-110` and `tcw validate` from the
  worktree.

## A spec gap this plan settles

**An inherited entry in the web app.** The spec keeps web route keys as
id-paths within the served project (Non-goals, TCW-113) and derives them from
`full-id`'s id-path (4.5). An inherited entry whose id-path a local entry
also has (or that two inherited stores share) then has no route key of its
own: today its key is the alias-prefixed `core/term`. This plan uses the full
identifier as the route key of an inherited entry only (Step 6), and the
server's routes accept it through the shared input sorter (Step 8). AC 20a's
cases, both of the served project's own records, are unchanged.

## Spec defects found while planning

Not edited here; each needs the spec's owner.

1. **`tcw taxonomy set` does not exist.** Design 3.1 lists
   `tcw taxonomy show|rm|set`, Design 5.1 "the reference fields set through
   `tcw taxonomy set`", and AC 8 says "`tcw taxonomy set` with a `relatesTo`
   given as a bare slug writes the full identifier". The taxonomy CLI has
   `list`, `add`, `show`, `path`, `rm`, `search` and `extends`
   (`tcw/taxonomy/cli.py:137-201`); `relatesTo` is written only by the web
   app's `PATCH /api/taxonomy/<slug>` (`tcw/serve/records.py:106-127`). Step
   9 tests that route and `tcw taxonomy add --vocab` instead.
2. **AC 10's second half cannot pass in a files-backend project.** A folder
   named `ABC-1` is not an item there: the files backend reads only
   `<date>-<words>` folders (`ITEM_FOLDER`, `is_item_folder`,
   `tcw/work/fs_backend.py:46`, `:57-67`), and an item's `created` date is
   read from the name (`:157`). So `tcw work show ABC-1` exits 4 whatever the
   input rule does. Step 8 tests the first half, and the fall-through with a
   backend whose `lookup` answers None.
3. **AC 13a's duplicate case, in AC 13's setup, is found by the graph walk,
   not at the link.** AC 13 names `core` under `projects:`, so TCW-107's walk
   looks `core` up, finds two folders, and records a graph problem;
   `tcw validate` then returns the graph problems before scanning links
   (`tcw/validate.py:394-397`), so the error is at the configuration, not at
   the link. Step 10 tests the duplicate with an ID nothing in `projects:`
   names (`lib`), which reaches the link as the AC intends.
4. **Problem 6 says no check compares stores' folders; one does.**
   `_shared_work_paths` (`tcw/validate.py:677-703`) already fails two
   filesystem-mode projects in the graph whose work paths are the same
   folder. It covers coinciding work stores only, not nesting or the tree
   stores; Step 14 replaces it.
5. **Design 7.5 counts `tree_store_present` as a reader that turns a location
   into a folder.** It answers presence from the configuration
   (`tcw/store/fs.py:382-404`) and resolves nothing; Step 13 has it take its
   default folder from `store_location`, which is the most the rule can mean
   for it.

## Self-review against the spec

| AC | Step |
| --- | --- |
| 1 | 1, 2 |
| 2 | 1 (Python), 2 (Node) |
| 3 | 10 |
| 4 | 4 (work), 6 (taxonomy, capabilities) |
| 5 | 4, 6 |
| 6 | 4, 6 |
| 7 | 4 (folder, full identifier), 8 (address, wrong namespace, 3.x hint, options) |
| 8 | 4 (work), 9 (records; see defect 1) |
| 9 | 5 (new, key, untracked), 8 (`<project>.work/<KEY>`) |
| 9a | 5 |
| 10 | 8 (see defect 2) |
| 11 | 4 (`item.yaml`), 9 (`Subject`), 11 (`capabilities.yaml`) |
| 12 | 11 |
| 13 | 10 |
| 13a | 8 (command), 10 (validate; see defect 3) |
| 14 | 13 |
| 15 | 13 (resolution, loops), 14 (nesting) |
| 16 | 14 |
| 17 | 13 |
| 18 | 8 |
| 19 | 4 |
| 20 | 6 (records), 8 (a parent written through the web), 10 (suggestions, `/api/resolve`) |
| 20a | 4 (model), 6 (`itemKey`), Verification (served page) |
| 21 | 15 |
| 22 | 19 |
| 23 | 8 (list, show, set), 11 (route) |
| 24 | 12 |
| 25 | 8 |

Every design rule of the spec's Coverage table maps to a step through these
criteria; 1.5 (one type, one parser) is Steps 1, 2 and 15; 6.1's four
outcomes are Step 7, used by Steps 8, 10, 11 and 13; 7.5 is Step 13. Every
step traces to a criterion except 0 (the starting point), 3 (the test helper
Steps 4 to 14 use), 16 (records, the spec's Capability changes), 17 (the
spec's Handoffs and what planning added) and 18 (documentation).

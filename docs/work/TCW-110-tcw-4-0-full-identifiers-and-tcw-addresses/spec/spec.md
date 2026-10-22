# Spec — TCW 4.0: full identifiers and `tcw://` addresses

Child 5 of 13 of TCW-99. It carries out these sections of the TCW-99 design
(`docs/work/TCW-99-…/design.md`): "Full identifiers", "Where stores live",
principle 3 ("Every object belongs to exactly one project"), and the parts of
"What any store must support" that sort these operations into the model and
the deployment layer. Built on the `v4` branch, on top of TCW-106 (the
`.tcw/` folder, `tcw-version`, and the naming rule for project IDs) and
TCW-107 (manifests, and the one function that finds a project's folder from
its ID, `FsProjectRegistry.project_folder`, TCW-107 Design 2.12). The
children land in the order TCW-106, TCW-107, TCW-110, TCW-108, TCW-111
(Notes, decided by the user on 2026-10-22): TCW-107 lands first, so this item
calls that function and provides no stand-in for it; TCW-108, which replaces
the 3.x `projects:` key with parent links, lands after it, so this item works
with `projects:` as TCW-107 leaves it (IDs only).

File and line references are to commit `39603cc4` on `v4`; the plan re-checks
them against whatever TCW-106 and TCW-107 finally land.

## Capability changes

- **New** `cli/name-any-tcw-object-by-its-full-identifier`: every taxonomy
  entry, capability and work item has one name,
  `<project>.<namespace>/<id-path>`, that says which project owns it and
  where it is. Every command prints it, every reference TCW stores is it, and
  every command that takes an object accepts it.
- **Changed** `cli/reference-a-tcw-object`: a link is
  `tcw://<project>.<namespace>/<id-path>`, never shortened; the 3.x forms
  (`tcw://C/…`, `tcw://<id>/W/…`) are reported as needing `tcw migrate`; a
  full identifier may name an object in any project TCW can locate, not only
  one named by `extends`.
- **Changed** `cli/rely-on-one-output-contract`: lists print full identifiers;
  JSON records carry `full-id` and `owner`, and the JSON envelope says
  `"schema": 2`.
- **Changed** `cli/validate-a-project`: checks the form of every stored
  reference and address, reports 3.x references as needing `tcw migrate`, and
  fails stores that nest in or coincide with another store, and store
  locations that loop.
- **Changed** `work/configure-the-work-store-location`,
  `taxonomy/configure-the-taxonomy-store-location` and
  `capabilities/configure-the-capabilities-store-location`: a location is a
  plain path or a `.path` address, resolved from the project that wrote it.
- **Changed** `work/read-a-work-item`, `work/manage-blocking-relations`,
  `work/decompose-a-work-item-into-children`, `taxonomy/read-a-term`,
  `capabilities/read-a-capability`: they accept and print full identifiers; a
  work item can be named by its tracker key, bare or as
  `<project>.work/<KEY>`.
- **Changed** `work/declare-capability-changes-in-a-child-projects-ledger`:
  each path in an item's `capabilities.yaml` is a full identifier, so the
  owning ledger is named rather than guessed from the first folder name.
- **Changed** `web/pick-references-and-known-values-from-suggestions`: the
  web app suggests and writes links and references as full identifiers.
- **Changed** `work/view-the-board`: `tcw work list` prints one full
  identifier per line, and in a Jira project says how many tickets it left
  out because their `TCW Item` is still a 3.x value, naming `tcw migrate`.
- **Changed** `work/keep-work-items-in-jira`: the `TCW Item` field holds the
  item's full identifier.
- **Taxonomy:** new `full-identifier` and `tcw-address`; changed
  `namespace`, `reference` and `configurable-component-store-location`.

## Problem

Today an object's name depends on where it is read from, so the same object
has different names, and a name does not always say which project owns it.

1. **Three name shapes, none of them complete.** A work item's slug is
   `<project>/<folder>` (`Slug.__str__`, `tcw/work/model.py:74-75`), and a
   bare folder is accepted for the current project (`Slug.parse`,
   `tcw/work/model.py:42-72`). A taxonomy entry or capability is named by its
   path, bare when it is the project's own, prefixed with an `extends` alias
   when inherited (`Term.qualified`, `tcw/store/base.py:340-343`;
   `Capability.qualified`, `tcw/store/base.py:505-508`). Nothing in either
   name says which namespace (taxonomy, capabilities or work) it belongs to.
2. **A bare name means different things in different places.** `get` in both
   tree stores reads a first folder name that matches an `extends` ID as a
   project, and otherwise looks locally, then in every inherited store
   (`tcw/store/fs.py:1799-1817`, `:2425-2440`). An item's
   `capabilities.yaml` path is routed by its first folder name to an
   extended ledger, a child project's ledger, or the item's own
   (`route_capability_path`, `tcw/work/gates.py:331-380`), and is refused as
   ambiguous when a folder name and a child project ID collide
   (`tcw/work/gates.py:360-371`). TCW-85 asked for a shorthand on top of
   this; the TCW-99 design answers it with full identifiers instead.
3. **`tcw://` links have their own grammar.** `tcw://[<namespace>/]<axis>/<ref>`
   with a one-letter axis `T`, `C` or `W` (`tcw/refs.py:1-14`), parsed by
   taking the first segment that reads as an axis (`parse_tcw_uri`,
   `tcw/refs.py:59-81`), so `tcw://T/C/x` is misread, a limitation the
   docstring records. A work link takes two spellings that must be
   reconciled (`_resolve_work`, `tcw/refs.py:126-162`). A taxonomy or
   capability link can name only a project listed in `extends`
   (`docs/capabilities/cli/reference-a-tcw-object/description.md`), so a
   project cannot point at an object in a project it does not inherit from.
4. **Output shortens.** `tcw work list` and `new` print `<project>/<folder>`
   (`tcw/work/cli.py:231`, `:257`); `tcw taxonomy list` and
   `tcw capabilities list` print the bare path for the project's own entries
   (`tcw/taxonomy/cli.py:64`, `tcw/capabilities/cli.py:55`). JSON records key
   the name differently per axis: `slug` for work (`tcw/work/record.py:30`),
   `path` plus `origin` for the other two (`tcw/taxonomy/cli.py:32-33`,
   `tcw/capabilities/cli.py:38-39`).
5. **A store kept in another repository needs a machine-specific path or a
   `repository` declaration.** `<component>.path` is a plain path, relative
   to the project root or absolute (`WorkLocation._local_root`,
   `tcw/store/fs.py:85-92`; the tree stores' copy reads the same way), read
   by `resolve_store` (`tcw/store/fs.py:3182-3318`). A planning workspace
   holding another project's work store (`docs/use-cases.md`, UC-4) writes
   `work.path: ../docs/app/work`, which is right only where the two
   checkouts sit in that relation on disk.
6. **Little stops two stores sharing a folder.** The one check that compares
   stores' folders, `_shared_work_paths` (`tcw/validate.py:677-703`, called at
   `:403-405`), fails two projects of the graph whose work stores are the same
   folder, and only that: it skips Jira-mode projects (`:690-692`), never
   looks at the taxonomy or capabilities stores, and does not notice one store
   inside another. So a work store configured inside another project's work
   store is listed by both, and a taxonomy store inside the capabilities
   store passes.

## Goals

1. Every taxonomy entry, capability and work item has one full identifier,
   `<project>.<namespace>/<id-path>`, computed the same way wherever it is
   read from.
2. Every command prints full identifiers; every reference TCW writes into a
   file or onto a ticket is a full identifier (a Markdown link is its
   `tcw://` address).
3. Every command that takes an object accepts its full identifier and its
   `tcw://` address, and a work item's tracker key; the active project's own
   objects may also be typed by id-path alone.
4. `tcw://` addresses follow one grammar that a general URL parser reads
   unchanged, including `.path` addresses naming folders.
5. A store's location is a plain path relative to the project or a `.path`
   address, resolved from the project that wrote it; stores never nest or
   coincide, and locations never loop.
6. A 3.x reference is recognised and reported as needing `tcw migrate`, never
   misread.

## Non-goals

- **State files, object folders and nested work items** (TCW-111): the
  `tcw-*.yaml` state files, reserved names, `resources/`, and work items whose
  id-path contains `/`. Until then the full identifier is computed from
  today's layout (Design 1.3), and a work id-path is one folder name.
- **Moving and renaming objects, and rewriting references** (TCW-114),
  including `tcw -C <folder or address>`, which uses this item's address
  parser.
- **Finding a project's folder by ID** (TCW-107, which lands first). This
  item calls TCW-107's function for it (Design 6.1) and handles each of its
  outcomes; the search rules, their cost and their duplicate-ID check are
  TCW-107's.
- **Converting 3.x references** in files and on Jira tickets (TCW-116). This
  item only recognises them and names `tcw migrate`.
- **Inheritance and overrides by path** (TCW-112): `extends`, the
  `overrides:` pointer and the capability's opaque `id` (`cap-…`) stay as
  they are. An inherited object is named by its owner's full identifier.
- **Views across projects** (TCW-113), including the web app showing other
  projects' objects beyond the inherited entries it shows today. The web
  API's route key of the served project's own object stays its id-path; an
  inherited entry's route key becomes its full identifier (Design 4.5), the
  one route-key change this item makes.
- **Environment overrides of store locations** (TCW-109).
- **`<component>.repository`** and the provisioning ladder in
  `resolve_store`: unchanged here; the design moves a store's repository into
  a manifest entry (TCW-107, TCW-115, TCW-116).
- **Store locations in personal files**: personal files cannot set store
  locations today (`PERSONAL_KEYS`, `tcw/config.py:45-52`), and what they and
  environment variables may set in 4.0 is TCW-109's.
- **Guides, skills, stage prompts and eval cases** that teach the 3.x link or
  slug forms (TCW-117). This repository's own records, links and `capabilities.yaml`
  files keep the 3.x forms until TCW-116 migrates it, because the 3.x CLI
  that drives this repository's lifecycle reads them; this item's own
  `capabilities.yaml` is written in that form for the same reason. That CLI
  is the `tcw` first on `PATH`: the primary checkout's editable install of
  `main`, which reports 3.0.2 and imports `main`'s code even when run from
  the `v4` worktree (Notes, decided by the user on 2026-10-22).

## Design

### 1. The full identifier

1.1. **Grammar.** In the notation below, `"x"` is literal text, `a / b` is
either, `[ a ]` is optional, and `*( a )` is zero or more.

```
full-id    = project-id "." namespace "/" id-path
project-id = word *( "-" word )                 ; word = 1*( a-z / 0-9 )
namespace  = "taxonomy" / "capabilities" / "work"
id-path    = id-part *( "/" id-part )
id-part    = ( A-Z / a-z / 0-9 ) *( A-Z / a-z / 0-9 / "-" / "_" )   ; at most 128 characters
```

`project-id` is TCW-106's naming rule (`PROJECT_ID_PATTERN`,
`tcw/store/project.py:25`), and, as for a project's own `id:`, it is not one
of the reserved IDs (`RESERVED_PROJECT_IDS`, `:26`: `t`, `c`, `w`, `local`),
so `local.work/x` is refused and `local` is never read or printed as an owner
(1.4). The grammar sets no limit on a whole identifier's length; TCW-111 adds
one. An id-part may not start with `-` or `_`, so a
part typed alone is never read as a command option, and is at most 128
characters, as a work folder is today (`FOLDER_LIMIT`,
`tcw/work/model.py:24`). Upper and lower case are different characters:
identifiers are compared exactly as written. On a disk that ignores letter
case (the macOS default), joining a typed id-path onto a store's root finds
`cli/x` when `Cli/x` is typed (`get_local`, `tcw/store/fs.py:2391-2399`), so
one object would have two identifiers and either could be stored. An id-path
is therefore found only when each of its folders exists with exactly the
spelling given, checked against the folder's listing; a spelling that
differs only in case is not found, and the not-found message names the
spelling on disk.

1.2. **A `.` before the first `/` marks a full identifier.** No id-part can
contain a `.`, and no project ID can, so any text whose part before the first
`/` contains a `.` is read as a full identifier (and is an error if it is
not a valid one), and any other text is read as an id-path.

1.3. **The id-path of today's objects** (until TCW-111 changes the layout) is
the object's existing identity, which is already its folder path under the
store's root:

| Namespace | id-path | Example |
| --- | --- | --- |
| `taxonomy` | the term's slug, every folder from the store root (`Term.slug`, `tcw/store/base.py:330`); flat in most projects, nested when a term was added with a parent | `tcw.taxonomy/reference` |
| `capabilities` | the capability's path, group folders included (`Capability.path`, `tcw/store/base.py:493`) | `tcw.capabilities/cli/reference-a-tcw-object` |
| `work` | the item's folder name (`Slug.folder`, `tcw/work/model.py:40`) | `tcw.work/TCW-110-tcw-4-0-full-identifiers-and-tcw-addresses` |

The id-path is relative to the store's root wherever `<component>.path`
puts it.

1.4. **The owner** is the project whose store holds the object's folder: the
active project for its own objects, and for an inherited one the project ID
it is inherited from (`origin`, which `_inherited_stores` already keys by
owning project ID, `tcw/store/fs.py:1771-1783`). The value `local` is never
printed as an owner.

1.5. **One value type and one parser.** A single module holds the full
identifier type (project, namespace, id-path), its parser, its text form and
the address forms of Design 2. The work model's `Slug` becomes that type
with namespace `work`; `Term` and `Capability` gain a `full_id` built from
their owner and path. Every place that parses or prints an identifier (the
sweep in Design 5.4) goes through it.

1.6. **Names that break the grammar.** Creating an object whose id-part
breaks 1.1 is refused as a usage error (exit 2) before anything is written:
`tcw taxonomy add`, `tcw capabilities add`, and their web routes. A work
item's folder is made from title words that already fit 1.1 (`FOLDER_PATTERN`,
`tcw/work/model.py:28`). An existing folder whose name breaks it (today's
stores allow any name without `/`, `\`, NUL or a `.`/`..` part,
`_safe_store_id`, `tcw/store/fs.py:1125-1139`) is reported by `tcw validate`
as an error naming the folder and the characters allowed, and saying it must
be renamed by hand. Commands still read it and list it, printing its full
identifier as the folder names it, but cannot be given it: the parser
refuses that text (`demo.capabilities/cli/has.dot` breaks 1.1, and a bare
`has.dot` reads as a full identifier by 1.2), so `show`, `set` and `rm` of it
are usage errors naming 1.1 and the rename. Only a rename by hand fixes such
a folder until TCW-114's move command exists, and `tcw migrate` (TCW-116)
reports them.

### 2. `tcw://` addresses

2.1. **Grammar.**

```
address      = object-address / folder-address
object-address = "tcw://" full-id
folder-address = "tcw://" project-id [ "." namespace ] ".path" "/" [ folder-path ]
folder-path  = folder-part *( "/" folder-part ) [ "/" ]
folder-part  = 1*( A-Z / a-z / 0-9 / "-" / "_" / "." / "~" ), and not "." or ".."
```

- `tcw://p1.work/TCW-120-add-login` names a work item.
- `tcw://p1.path/` names p1's root folder (the folder holding its `.tcw/`).
- `tcw://p1.work.path/` names the folder of p1's work store;
  `tcw://p1.capabilities.path/cli` a folder inside p1's capabilities store.
- `tcw://p1.path/docs/p2-work` names a folder inside p1's root.

2.2. **What is refused,** each with a message naming the rule it breaks:
a `.` or `..` folder (a URL parser drops them; the design's reason); an
empty folder (`//`); any character outside 2.1, so `%` (and with it
percent-encoding), `?`, `#`, spaces, `:` and `@` (no query, fragment, port or
user part); an upper-case letter before the first `/`; an address with
neither a namespace nor `.path` (`tcw://p1/`); a folder address with nothing
after `.path` (`tcw://p1.path`, written `tcw://p1.path/`); an object address
ending in `/`. Folder parts allow `.` and `~` within a name (`.github`,
`v1.2`) because they are folders on disk, which TCW does not name; they are
the characters RFC 3986 calls unreserved, which every URL parser leaves
unchanged.

2.3. **Every address has one spelling,** so two addresses name the same
target exactly when their text is equal, except that a trailing `/` on a
folder address is ignored when comparing.

2.4. **A 3.x reference is recognised:** an address whose part before the
first `/` holds no `.` and that has the 3.x shape `tcw://[<project>/]<axis>/<ref>`
with an axis of `T`, `C` or `W` and a non-empty `<ref>` (`tcw/refs.py:1-14`;
`tcw://C/cli/x`, `tcw://W/2026-01-01-x`, `tcw://core/T/term`). Any other
address with no `.` before its first `/` (`tcw://p1/`, `tcw://p1/x`) is not a
3.x reference, and gets 2.2's message for an address with neither a namespace
nor `.path`. A 3.x reference is reported as
`<address> is a TCW 3.x reference; TCW 4 writes tcw://<project>.<namespace>/<id-path> (run 'tcw migrate' in this project)`,
and is never resolved.

2.5. **An address is resolved from the project that wrote it**: the project
whose file holds it, wherever the command runs. A link in p2's records is
resolved by locating its project from p2 (Design 6.1).

2.6. **Object address versus full identifier.** A Markdown link and a store
location hold an address; a field in a state file, a `capabilities.yaml`
entry, a Jira field and every command's output hold the full identifier
without `tcw://`. Command input accepts either (Design 3.1).

### 3. What commands accept

3.1. **Every argument or option that names an object** (the item argument of
every `tcw work` command; `tcw work new|edit --parent`, `--blocked-by`,
`--unblocked-by` and `--blocks`, `tcw/work/cli.py:682-691`, `--blocks` being
on `v4` until TCW-114; `tcw work list --parent`, `:728`; the path argument of
`tcw taxonomy show|rm` and `tcw capabilities show|set|reset|rm`; the
reference values given to `tcw taxonomy add --vocab` and to
`tcw capabilities set --field` (Design 5.1; `tcw taxonomy add --parent` names
a folder of the active project's own store to create the entry in, and stays
an id-path); the route
key of `/api/taxonomy/<key>` and `/api/capabilities/<key>`; and the web
routes that write a parent, a blocker or a reference, among them
`PATCH /api/taxonomy/<key>`'s `relatesTo` and `vocabulary`) accepts these
forms. The taxonomy CLI has no `set` command (`tcw/taxonomy/cli.py:137-201`
registers `list`, `add`, `show`, `path`, `rm`, `search` and `extends`), so a
taxonomy entry's `relatesTo` is written only through that web route, and
this item adds no command for it. Each input is sorted into one form by its
text alone, by 1.2 and the key pattern:

| # | Input | Meaning |
| - | ----- | ------- |
| a | a full identifier, or its object address, except (c) | that object |
| b | a tracker key such as `TCW-120` (the whole text matches `KEY`, `tcw/work/jira/backend.py:54`), work only | the active project's item carrying that key |
| c | a work full identifier whose id-path is one part that wholly matches `KEY` (`<project>.work/TCW-120`), or its object address | that project's item carrying that key |
| d | an id-path | the active project's object at that path, read as the active project sees it (so an inherited object is found as it is today, `tcw/store/fs.py:1799-1817`) |

Anything else is a usage error (exit 2). A namespace in (a) or (c) that is not
the command's namespace is a usage error naming the namespace expected. (c)
takes the key-shaped id-path from (a) because in a Jira project an item
folder is always the key followed by title words (`KEY_FOLDER`,
`tcw/work/jira/backend.py:56`), so `planning.work/TCW-120` can only mean the
key. Neither backend can hold a folder whose whole name is a key (the files
backend's folders are `<date>-<words>`, `ITEM_FOLDER`,
`tcw/work/fs_backend.py:46`; the Jira backend's are `<KEY>-<words>`), so a
key-shaped text is never read as a folder name (3.2).

**An inherited object, until TCW-112.** When form (a) names an object owned by
a project that the active project's store for that namespace extends
(`taxonomy.extends`, `capabilities.extends`), it is read and written through
the active project's view, as form (d) is: `tcw capabilities show
core.capabilities/cli/x` in `app` shows what `tcw capabilities list` in `app`
shows for it, including `app`'s 3.x override of it (`_apply_override`,
`tcw/store/fs.py:2408-2441`), and `set`, `reset` and `rm` act on that override
as they do today for `core/cli/x` (`_write_target`, `:2655-2691`). Design 6.2's
reading from the owner's own store applies to every other project.
TCW-112 replaces overrides by path and this rule with them.

3.2. **A tracker key is looked up by the backend that holds the item,** with
the existing `lookup` operation (`tcw/work/backend.py:97`; the Jira backend
scans the work folder for the key, `tcw/work/jira/backend.py:314-325`). For
(c) the named project's backend is opened first (Design 6.1). When `lookup`
answers None, the item is not found (exit 4) with
`no work item in project '<id>' carries the key <KEY>`, the message a Jira
project gives today with the project named
(`no work item here carries the Jira key …`, `tcw/work/cli.py:58-61`).
A files-backend project has no tracker keys (`lookup` answers None,
`tcw/work/fs_backend.py:480-481`), so there `TCW-120` and
`demo.work/TCW-120` get the same message; they are never read as a folder
name, since no files-backend folder can be named only by a key (3.1). When
TCW-111 nests items, `lookup` finds the key wherever the folder is nested;
nothing here changes for that.

3.3. **What is stored is always the full identifier.** Whatever form of 3.1
names an object, the reference TCW writes is its full identifier with its
folder's id-path: `--parent planning.work/TCW-120` stores
`planning.work/TCW-120-add-export`.

3.4. **The 3.x forms are no longer input.** `<project>/<folder>` and an
`extends` prefix (`core/term`) contain no `.` before the first `/`, so they
are read as id-paths by 1.2 and are usually not found. When the first part
of such an id-path is the ID of a project TCW can locate, the not-found
message adds `; to name an object in project '<id>', write <id>.<namespace>/<rest>`.
Looking for the hint never changes the outcome: it is tried only when the
first part is a valid project ID, any answer of 6.1 other than "found" gives
no hint, and the command still exits 4 with the not-found message.

### 4. What commands print

4.1. **Lists** print one full identifier per line: `tcw work list`,
`tcw taxonomy list|search`, `tcw capabilities list|search`, and the
identifier printed by `tcw work new`, `tcw work tickets adopt`,
`tcw taxonomy add` and `tcw capabilities add`.

4.2. **`show`** in all three namespaces starts with `full-id: <full id>` and
`owner: <project id>`. In `tcw taxonomy show` and `tcw capabilities show`
these replace `path:` and `origin:` (`tcw/taxonomy/cli.py:82-83`,
`tcw/capabilities/cli.py:75`); in `tcw work show` they replace `slug:`, and
`parent`, `blocked-by`, `blocks` and `children` print full identifiers.

4.3. **JSON.** Each taxonomy, capability and work record carries `full-id`
and `owner`, replacing `path` and `origin` (taxonomy, capabilities) and
`slug` (work). The work record keeps `path` (its folder on disk), and its
`parent`, `blocked-by`, `blocks` and `children` hold full identifiers. Every
JSON document TCW prints says `"schema": 2` (`print_json`,
`tcw/output.py:53-56`), since every record's keys change. That includes the
document a `generate:` binding receives, which `tcw/work/resolve.py:308-313`
builds itself with `"schema": 1` around the same item record. One key name
across the three namespaces lets one script read any record.

4.4. **Everything else that names an object** names it by full identifier:
messages, warnings and `tcw validate` findings (they format through the
type of 1.5); the `TCW_SLUG` variable given to hooks and command bindings
(`tcw/work/advance.py:168`, `tcw/work/resolve.py:334`), which keeps its name,
since the design treats "slug" as a nickname for the full identifier; and
the item named in the stage prompt text (`<slug>`, `tcw/work/cli.py:517`).

4.5. **The web app** shows what the CLI prints (TCW-99 principle 4): the
records it receives carry `full-id` and `owner`, and its reference
suggestions insert `tcw://<full id>` links (today `tcw://W/<folder>`,
`tcw://T/…`, `tcw://C/…`, `web/client/src/model/reference-search.ts:242-257`),
and parent and blocker values as full identifiers. The `/api/resolve` answer
for a link to another project's object (any namespace, not only work as
today, `tcw/serve/records.py:234-236`) is `other-project` with that project;
for an object of the served project it is `ok` with the id-path as `key`,
and for an inherited entry `ok` with its full identifier as `key` (the route
key below).

The web records keep no `slug`, `qualified` or (taxonomy, capabilities)
`path` key beside `full-id`: they are the CLI's records (4.3). The client
reads them through one parser of its own, a new module in
`web/client/src/model/` holding 1.1's grammar, and the places that split a
slug at its first or last `/` today change to it:

- `folderOf`, `projectOf` and `isLocal` (`web/client/src/model/work.ts:7-16`,
  `:113-118`): `projectOf("demo.work/x")` returns `demo.work`, so every item
  of the served project would render as another project's;
- `web/client/src/ui/work-forms.tsx:795` and
  `web/client/src/ui/work-views.tsx:245`, which cut or build
  `<project>/<folder>`;
- `web/client/src/model/api.ts:129-132`, and the `slug` fields of
  `web/client/src/model/types.ts:60`, `:82`, `:181`;
- `itemKey` (`web/client/src/ui/route-utils.ts:19-27`), which derives a route
  key from `slug`, `qualified` or `path`. The route key of an object of the
  served project is the id-path of its `full-id`. The route key of **every**
  inherited entry is its whole full identifier (today the alias-prefixed
  `core/term`), not only of one whose id-path a local entry also has, so an
  inherited entry's key does not change when a local entry with the same
  id-path is added. A full identifier has a `/`, so the client encodes the
  key in the URL (`encodeURIComponent`, `web/client/src/model/api.ts:86`, as
  it does today) and `/api/taxonomy/<key>` and `/api/capabilities/<key>`
  (`tcw/serve/records.py:243-254`) read it with Design 3.1's forms;
- the server's own `slug` keys in `tcw/serve/work.py:223`, `:492`, `:514`,
  `:537`, `:566`, which become `full-id`.

### 5. References TCW stores

5.1. **Every stored reference is a full identifier** (a Markdown link, its
address). The places, found by the sweep in 5.4:

| Where | Field | Today |
| --- | --- | --- |
| a work item's `item.yaml` (files backend) | `parent`, `blocked-by` | `<project>/<folder>` (`tcw/work/fs_backend.py:128-164`, `:180-183`) |
| a Jira ticket | `TCW Item` | `<project>/<folder>` (`tcw/work/jira/backend.py:705-708`, `tcw/work/jira/tickets.py:181`, `:388`) |
| a work item's `capabilities.yaml` | every entry under `new`, `changed`, `removed`, and `taxonomy.*` | a path, routed by its first folder (`tcw/work/gates.py:102-148`, `:331-380`) |
| a taxonomy entry's `meta.yaml` | `relatesTo` (written by `PATCH /api/taxonomy/<key>`, `tcw/serve/records.py:106-127`), `vocabulary` (written by `tcw taxonomy add --vocab` and that route) | a bare or alias-prefixed slug (`tcw/store/fs.py:1739`, `:2178-2183`) |
| a capability's `meta.yaml` | `Subject`, `Feature` (taxonomy); `Superseded by`, `Blocked by`, `Roles`, `When` (capabilities, `Roles` and `When` keeping their `!` negation and `roles/`, `conditions/` id-paths) | bare or alias-prefixed paths (`tcw/store/fs.py:2936-2980`) |
| any `.md` file in a store | `](tcw://…)` links | 3.x grammar (`_LINK_RE`, `tcw/validate.py:49`) |

The 3.x `overrides:` pointer is not in this table: TCW-112 removes it.

5.2. **Reading a stored reference.** A value that is a valid full identifier
(or, for links, a valid address) is resolved by Design 6. A value in a 3.x
form (no `.` before its first `/`, or 2.4 for a link) is reported where it is
read, naming the file, the field and `tcw migrate`; a value that is neither
is reported as malformed. Each reader reports it the way it reports an
unreadable value today: the files backend as an unreadable item
(`Unreadable`, `tcw/work/fs_backend.py:128-132`), the tree stores' `check`
as a finding, and the readers that never refuse (Jira's `_slug_of`,
`tcw/work/jira/backend.py:383-389`, and `_own_slug`,
`tcw/work/jira/tickets.py:233-241`) as no item. So a ticket that has no
folder in this project (a key with a folder here is matched by the folder
first, `resolve_keys`, `tcw/work/jira/backend.py:391-402`) and whose
`TCW Item` is still 3.x is listed as untracked.

**A Jira project part way through `tcw migrate`.** Every ticket's `TCW Item`
holds `<project>/<folder>` until TCW-116's Jira step has run. Such a ticket
is not read as an item until it is migrated, as the design says of every 3.x
value ("Versions and migration"), but it is never blamed on the wrong cause.
Today `JiraBackend.list` drops every ticket whose value it cannot read with
the warning that its folder "may exist in another copy of this repository"
(`tcw/work/jira/backend.py:470-482`), which is false for a 3.x value. A value
is in the 3.x form when it has no `.` before its first `/` and reads as
`<project>/<folder>`.

- `tcw work list` leaves such tickets out, and says so once per command, on
  standard error: `warning: <n> Jira tickets of this project hold a TCW 3.x
  TCW Item value and are left out (<key>, <key>, …); run 'tcw migrate' in
  this project to convert them`, listing every key. The "another copy of this
  repository" warning stays only for a 4.0 value whose folder is not here.
- `tcw validate --remote` reports each one as an `error`, in both of its
  directions. From an item's folder to its ticket
  (`tcw/work/jira/remote.py:480-482`), a 3.x value gets `its ticket's TCW
  Item <value> is a TCW 3.x value; run 'tcw migrate' in this project to
  convert it` in place of the generic "TCW Item is …, not …" mismatch. From
  each ticket naming this project back to a folder (`:490-499`), which today
  skips a value it cannot parse (`:494-495`), a ticket whose value is 3.x and
  that the first direction did not already report gets the same message at
  the ticket's key, rather than being skipped silently.

5.3. **Writing.** Every write of a field in 5.1, from the CLI or the web
app, writes the full identifier (Design 3.3), including a value given in an
input form of 3.1.

5.4. **The sweep is repository-wide** over `tcw/`, `web/client/src/`,
`scripts/` and `evals/`: every call of `Slug.parse`, `Slug(...)`,
`str(<slug>)`, `.qualified`, `parse_tcw_uri` and `resolve_tcw_ref`; every
`partition("/")`, `split("/")`, `indexOf("/")` and `lastIndexOf("/")` applied
to a value that holds an identifier; every message or value built by hand by
joining a project ID, a `/` and a name (`f"{self.project}/{folder}"`, nine
such sites today, in `tcw/work/fs_backend.py`, `tcw/work/jira/backend.py`,
`tcw/serve/work.py`, `tcw/refs.py` and `web/client/src/ui/work-views.tsx`),
which no change to the type of 1.5 reaches; every read of the fields in 5.1 or of a
record's `slug`, `path`, `origin` or `qualified` key; and every text that
describes the old forms to a person: the command contracts' `prints=` strings
("one qualified path per line", `tcw/taxonomy/cli.py:142`, `:151`, `:183`;
`tcw/capabilities/cli.py:226`, `:251`, `:290`), `SLUG_HELP`
(`tcw/work/cli.py:182`), and the `--json` help strings that show
`"schema": 1` (`tcw/work/cli.py:735`, `tcw/taxonomy/cli.py:146`, `:170`,
`:187`, `tcw/capabilities/cli.py:235`, `:244`, `:294`). The plan lists each
site. Today's count is 28 `Slug.parse` and `Slug(` sites across `tcw/` (in
`tcw/validate.py`, `tcw/work/`, `tcw/serve/work.py` and `tcw/store/`);
`scripts/require_artifact.py`, which passes `TCW_SLUG` to `tcw work path`
and needs no change because the value is accepted input (3.1 a); and
`evals/assets/gen_requirement.py:38`, which reads the `generate:` payload's
`item.slug` and would silently lose its marker, so it reads `full-id`; and
`evals/seed_fixture.py:669-670` and `:700-701`, which write bare capability
paths into items' `capabilities.yaml` and so write full identifiers instead.
`evals/grade.py` compares what `tcw work list` and `tcw work new` print with
each other, so it needs no change.

### 6. Resolving a full identifier

6.1. **Finding the owner.** If the project is the active project, its own
store is used. Otherwise TCW calls TCW-107's function (TCW-107 Design 2.12)
on the command's one registry, the one `FsProjectRegistry.open(<active
project's root>)` returns:

```python
FsProjectRegistry.project_folder(project_id: str, named_by: Path) -> Path
```

`project_id` is the identifier's project, which need not be named under any
`projects:` key; `named_by` is the root of the project that wrote the
reference (2.5): the active project for its own files and for command input,
or the owner found for the file being read, which an earlier call returned.
`project_folder(<named_by's own ID>, named_by)` returns `named_by`. The
answer is kept for the rest of the command (TCW-107 Design 2.11), so a
reference met twice is located once. Every lookup this item makes in one
command, for a full identifier, a link, a `capabilities.yaml` entry or a
store address (7.2), in whichever project's file it is written, goes to that
one registry; none opens a registry of its own from another project's root,
which would walk that project's family again, keep its own answers, and so
escape TCW-107 Design 2.9's one-folder-per-ID check. Its outcomes, and what this item does
with each:

| Outcome (TCW-107 Design 2.12) | Raised | A command | `tcw validate` |
| --- | --- | --- | --- |
| found | returns the project's root folder | reads the object (6.2) | checks the object (6.4) |
| not on this machine: a manifest or `projects:` entry names the project, but its folder is not here | `Unreachable` | exit 5 when it needs the object, naming the project and, when the entry gives one, the repository and `tcw project provision <id>` | `unresolved`, "could not check" |
| unknown: nothing names the ID and the search does not find it | `UnknownProject` | exit 1, `no project with ID '<id>' is known or found near this one; check the spelling` | `error` with that message, at the reference |
| graph problem: two folders, a wrong entry, an unreadable candidate, a broken manifest, a bad `TCW_PROJECT_<ID>`, or a second folder for an ID already found | `ProjectGraphError` | exit 1 with its message | `error` with its message, at the reference |

The "unknown" row is TCW-107's narrowing of the design's "could not check":
a misspelt project ID in a `tcw://` address fails `tcw validate` instead of
passing it for ever as a project that is merely absent.

6.2. **Reading the object.** For an owner that the active project's store
for the namespace extends, the object is read through the active project's
view, as 3.1 says, until TCW-112. For every other owner, the owner's store
for the namespace is opened from the owner's own configuration, and the
object is read from that store's own objects at the id-path; another
project's inherited objects are never reached through it. So
`core.taxonomy/term` from `app`, when `app` does not inherit from `core`,
reads `core`'s own `term`; when `app` does, it reads `term` as `app` sees it,
which is `core`'s `term` with any override `app` keeps. A taxonomy entry or
capability may now name an object in any project TCW can locate, not only
in one listed in `extends` (TCW-99 principle 1: naming is not inheriting).
For work, the owner's backend `read`s the folder (Jira: the folder scan
`link_exists`, so `tcw validate` needs no network, as today,
`tcw/refs.py:145-149`). The records gate reads an item's
`capabilities.yaml` entry the same way, so `changed: [core.capabilities/cli/x]`
in `app` is checked against `app`'s view of it, as rule 1 of
`route_capability_path` does today (`tcw/work/gates.py:354-355`).

6.3. **Outcomes.** Found: the object. Not there: not found (exit 4 for a
command; an error in `tcw validate`). The project not on this machine:
exit 5 for a command that needs the object; "could not check" (`unresolved`)
in `tcw validate`, for every namespace (today only work references are,
`docs/use-cases.md` UC-6, "Known gaps"). A project ID that is unknown, or
whose lookup is a graph problem: exit 1 for a command; an error in
`tcw validate` (6.1's table).

6.4. **`tcw validate`** checks every stored reference of 5.1 in the active
project's files and every address in its Markdown: form (Design 1, 2), 3.x
form (5.2), and that an object address or full identifier names an existing
object (6.2). A folder address is checked for form and that its project can
be located, not for whether the folder exists (the design: a `.path` rest
"is not checked against TCW's objects").

### 7. Store locations

7.1. **A store location** (`taxonomy.path`, `capabilities.path`,
`work.path`) is either a plain path, read as today (relative to the
project's root, may use `..`, re-anchored in a linked worktree,
`anchor_configured_path`, `tcw/store/fs.py:1212-1247`), or a folder address
(Design 2.1). An object address is refused as a location, naming the
`.path` form.
In the shared `.tcw/tcw-config.yaml` a plain path must be relative: an
absolute path or one starting with `~`, which 3.x accepts
(`WorkLocation._local_root`, `tcw/store/fs.py:85-92`), names a folder on one
machine in a file every machine reads. It is a configuration problem (every
command exits 1; `tcw validate` reports an error at the key) whose message
says: `<key> must be a path relative to the project, or a tcw:// .path
address such as tcw://<project>.path/<folder>; a folder that sits elsewhere
on this machine is placed by an entry in .tcw/tcw-manifest.local.yaml`. This
follows the request's "a plain path relative to the project". Whether a
personal file may give a store location at all is TCW-109's (Non-goals).

7.2. **Resolving a folder address** written in project W's configuration:

1. Find the named project's root with `project_folder(id, W's root)`, on
   the command's one registry (6.1). W's root is the active project's root
   or a folder an earlier call returned, as TCW-107 Design 2.12 requires of
   `named_by`.
2. For `tcw://<id>.path/<rest>`: the folder is that root joined with
   `<rest>`.
3. For `tcw://<id>.<namespace>.path/<rest>`: resolve that project's own
   location for `<namespace>`, from its own configuration (recursively, by
   this rule and 7.1), then join `<rest>`.

`tcw://W.path/docs/work` in W's own file names the same folder as
`docs/work`. The resolved folder then enters `resolve_store`'s rule 1 as the
configured path does today (`tcw/store/fs.py:3220-3229`). Step 1's
outcomes (6.1's table) decide the rest. A named project that is not on this
machine (`Unreachable`) makes the location unusable
(`StoreLocationUnusable`), so a declared `repository` still answers by rules
1.5 to 3 as today; with none, the command stops with exit 5, naming the
project. An unknown project ID or a graph problem (`UnknownProject`,
`ProjectGraphError`) is not something a repository can answer: every command
that resolves the location stops with exit 1 and that message, and
`tcw validate` reports it as an error at the key.

7.3. **No loops.** While resolving 7.2 step 3, TCW keeps the chain of
(project, namespace) pairs it has followed. Reaching a pair already in the
chain is an error for every command that resolves that location, and for
`tcw validate`, naming the chain:
`work.path: store locations loop: p2 work -> p1 work -> p2 work`.
A self-reference (`work.path: tcw://p2.work.path/x` in p2) is the shortest
loop.

7.4. **Stores never nest or coincide.** `tcw validate` fails when any two of
these stores are the same folder or one lies inside the other: the active
project's three stores, and the three stores of every project it can locate
by name (on `v4`, every project its registry connects, and every project
named by one of its store addresses). Two stores of the same project count
too: today both tree stores mark entries with `meta.yaml`, so one would
list the other's entries as its own, the same harm the design names. A
Jira-mode project's work store counts like any other: its folder still holds
each item's documents, so a store inside it mixes the two projects' item
folders, and today's check skipping such projects (Problem 6) is not kept.
This check replaces `_shared_work_paths` (`tcw/validate.py:677-703`), whose
one case, two work stores that are the same folder, it includes. Folders
are compared by identity (`_same_folder` and `_in_folder`,
`tcw/store/fs.py:595-615`), so a symlink or letter case does not hide a
match. A project found twice (a git worktree and its main checkout) is one
project and is not compared with itself. A store elsewhere inside another
project's folder is allowed. The error names both stores, their projects
and folders.

7.5. **One function** turns a configured location into a folder, and every
reader calls it: `resolve_store` (`tcw/store/fs.py:3223-3227`), `tcw init`
(`tcw/store/fs.py:656-662`, `:708`) and `tcw validate`'s own reading
(`tcw/validate.py:153`, `:209-213`). `tree_store_present`
(`tcw/store/fs.py:382-404`) resolves no location: it answers whether a store
is declared from the keys of the configuration. It takes the default folder
it looks for (`docs/<component>`) from the same function, so the default is
written in one place.

## Abstraction litmus test

| Operation | Layer | Verdict |
| --- | --- | --- |
| Parsing and printing a full identifier (Design 1) | model | Any store can name an object by its owner, its namespace and its path among its organising groups; a database keeps the id-path as a column. Passes. |
| Resolving a full identifier to an object (Design 6) | model | "Find the owner, ask its store for the id-path." The store answers its own way; only `project_folder` is about folders, and it sits in the deployment layer. Passes. |
| Looking a work item up by tracker key (Design 3.2) | model | The existing backend `lookup` operation, unchanged. Passes. |
| Writing full identifiers into stored references (Design 5) | model | A reference is a value in the backend's or the repository's record; any store keeps a string. The Jira field is one such value. Passes. |
| `tcw://` addresses of objects (Design 2.1) | model | Text form of a full identifier. Passes. |
| `.path` addresses, store locations, loops, nesting (Design 2.1, 7) | deployment | About folders on disk, by TCW-99's split ("What any store must support"). A store that is not a folder of files does not implement them. |
| `project_folder` (Design 6.1) | deployment | TCW-107's operation (TCW-107 Design 2.12), on `FsProjectRegistry` alone; called here, not designed. A store that is not a folder of files finds the owner its own way. |

No backend operation is added or changed: the twelve operations in
`tcw/work/backend.py` keep their signatures, and `read`, `lookup` and the
others still take one folder name (TCW-111 changes that for nested items).

## Use cases

- **UC-1 (a single project).** Its objects print with a prefix
  (`demo.work/2026-10-22-x` instead of `demo/2026-10-22-x`;
  `demo.capabilities/cli/x` instead of `cli/x`), and typing stays as short as
  today (Design 3.1 d). No configuration is added. Its links get longer
  (`tcw://demo.capabilities/cli/x`); `tcw migrate` writes them (TCW-116).
- **UC-2 and UC-7 (a library others read; a public library).** A reader's
  link to `core.taxonomy/term` resolves in `core` itself when the reader does
  not inherit from it, and through the reader's own view when it does, so
  the reader's override of it still applies until TCW-112 (6.2). It is
  "could not check" where `core` is not on the machine (6.3, closing UC-6's
  gap for taxonomy and capability links). Nothing about a reader is written
  into the library: resolving reads only.
- **UC-3 (a monorepo).** `server.capabilities/x` in an item of `app` names the
  server's ledger outright, replacing the first-folder routing and its
  ambiguity refusal (`tcw/work/gates.py:360-371`). An epic in `app` with parts
  in children: each part's `parent` is `app.work/<folder>`, set from the part's
  own project (TCW-114 builds that flow on these identifiers).
- **UC-4 (a planning workspace).** `work.path: tcw://workspace.path/docs/app/work`
  in `app` replaces `../docs/app/work`, and resolves through
  `project_folder` wherever the two checkouts sit (7.2). The workspace's own
  work store is `docs/work`, a sibling folder, so 7.4 allows it; a location
  inside `tcw://workspace.work.path/` would be refused. The items stay owned by
  `app` (1.4): their identifiers are `app.work/…` although their folders sit in
  the workspace's repository.
- **UC-5 (a shared Jira project).** `TCW Item` holds `app.work/APP-257-…`; the
  `TCW Project` field and its filtering are unchanged
  (`tcw/work/jira/jql.py:1-8`). A key typed as `server.work/APP-257` opens the
  server's backend to look it up (3.2), since keys come from one sequence and
  say nothing about the project (UC-5's second requirement).
- **UC-6 (a project not on this machine).** A full identifier or store
  address naming it stops a command that needs it with exit 5 naming the
  project, and is "could not check" in `tcw validate`; commands on the
  project's own objects are not affected (6.3, 7.2). A project ID that
  nothing names and the search does not find is an error suggesting a
  misspelling, not "could not check" (6.1).
- **UC-8 (several families).** A full identifier names a project by ID only;
  which folder that is comes from `project_folder`, whose rules, search,
  cost and duplicate-ID error are TCW-107's. This item adds no search of its
  own; it calls the function for projects no `projects:` entry names, which
  TCW-107's rules answer the same way (AC 14).
- **S-3 (backends).** Both backends store and read full identifiers; the
  Jira backend's change is the `TCW Item` value (5.1, 5.2).
- **S-4 (worktrees, clones).** A plain path keeps today's worktree
  re-anchoring (7.1); a `.path` address resolves through `project_folder`,
  whose worktree rules are TCW-107's. 7.4 does not compare a project with its
  own worktree copy.
- **S-8 (partial failure).** A migration stopped before its Jira step leaves
  tickets whose `TCW Item` is 3.x. They are left out of `tcw work list` until
  migrated, with a warning that names their keys and `tcw migrate`, and
  `tcw validate --remote` reports each as needing `tcw migrate`, from the
  item's side and from the ticket's (5.2). None is misread or blamed on
  another copy of the repository.
- **S-9 (upgrades).** Every 3.x reference shape is recognised and refused
  with `tcw migrate` named (2.4, 3.4, 5.2). A 3.x TCW reading a 4.0 file is
  not designed for (the 4.0 file carries `tcw-version`, TCW-106).
- **S-10 (things TCW does not own).** Nothing here looks downwards; folder
  addresses name folders the configuration chose.
- **S-11 (version control).** Nothing here reads or changes git, beyond what
  `anchor_configured_path` already does for worktrees.

Checklist: 1 (where it looks) Design 6.1 and 7.2, through `project_folder`
only; 2 (whose things) resolving reads other projects, writes only the
active project's records; 3 (reading across projects) 6.2, never through
inheritance; 4 (backends) the litmus table; 5 (who is present) nothing asks
a person; 6 (harness) the CLI carries everything; 7 (stopping halfway) S-8
above; 8 (single project) UC-1 above; 9 (older and newer TCW) S-9 above;
10 (testing the setup claimed) criteria 13 to 17 use two projects in two
repositories, and criterion 9 a Jira fake.

## Acceptance criteria

Each criterion runs against fixtures built with the suite's 4.0 project
helper (TCW-106), with projects located by TCW-107's rules: a project named
under `projects:` by ID, and found next to the project naming it or through a
manifest entry. "Prints" means standard output.

1. **Parser.** The identifier module accepts `a.taxonomy/x`,
   `a-1.capabilities/cli/x_y`, `p.work/TCW-120-add-login`, and refuses each
   of: `a/x`, `A.work/x`, `a.Work/x`, `a.thing/x`, `a.work/`, `a.work//x`,
   `a.work/-x`, `a.work/x.y`, `a.work/x y`, `a.work/x%20`, `local.work/x`,
   and an id-part of 129 characters, each with a message naming the rule. A
   work identifier parsed from text compares equal to, and hashes the same
   as, the work model's identifier for the same project and folder.
2. **Addresses.** The module accepts `tcw://p1.work/x`, `tcw://p1.path/`,
   `tcw://p1.work.path/`, `tcw://p1.path/docs/p2-work`,
   `tcw://p1.capabilities.path/.github/v1.2/`, and refuses `tcw://p1/`,
   `tcw://p1.path`, `tcw://p1.path/../x`, `tcw://p1.path/./x`,
   `tcw://p1.path/a//b`, `tcw://p1.work/x/`, `tcw://p1.work/x#y`,
   `tcw://p1.work/x?y`, `tcw://P1.work/x`. The refusal of `tcw://p1/` says it
   needs a namespace or `.path`, and does not say `TCW 3.x reference`. The
   module compares `tcw://p1.path/docs` and `tcw://p1.path/docs/` as equal,
   and `tcw://p1.path/docs` and `tcw://p1.path/Docs` as different. For each
   accepted address, Python's `urllib.parse.urlsplit` and Node's `new URL()`
   return the same path text as the address holds after its authority.
3. **3.x links.** In a project whose capability description links
   `[x](tcw://C/cli/x)`, `tcw validate` exits 1 with an error whose message
   contains `TCW 3.x reference` and `tcw migrate`; the same for
   `tcw://W/<folder>` and `tcw://core/T/term`.
4. **Lists print full identifiers.** In project `demo` with a taxonomy entry
   `term`, a capability `cli/x` and a files-backend item, `tcw taxonomy list`
   prints `demo.taxonomy/term`, `tcw capabilities list` prints
   `demo.capabilities/cli/x`, and `tcw work list` and the `tcw work new`
   that made the item print `demo.work/<folder>`. An entry inherited through
   `taxonomy.extends: [core]` prints `core.taxonomy/<slug>`.
5. **`show`.** `tcw taxonomy show term`, `tcw capabilities show cli/x` and
   `tcw work show <folder>` each print `full-id: <full id>` as the first line
   and `owner: demo` as the second; none prints `path:` (taxonomy,
   capabilities), `origin:` or `slug:`.
6. **JSON.** The `--json` output of the three `list` and three `show`
   commands has `"schema": 2`; each record has `full-id` and `owner` and has
   no `slug`, `origin`, or (taxonomy, capabilities) `path` key; a work
   record's `parent`, `blocked-by`, `blocks` and `children` are full
   identifiers. The `--help` of those six commands shows `"schema": 2` and
   does not contain `qualified path` or `full slug`.
7. **Input forms.** `tcw work show` accepts `demo.work/<folder>`,
   `tcw://demo.work/<folder>` and `<folder>` and prints the same item;
   `tcw capabilities show` accepts `demo.capabilities/cli/x` and `cli/x`;
   `tcw work show demo.taxonomy/term` exits 2 naming the namespace `work`.
   `tcw work show demo/<folder>` exits 4 and its message contains
   `write demo.work/<folder>`. `tcw work list --parent demo.work/<folder>`
   and `tcw work edit <other> --blocks demo.work/<folder>` accept the full
   identifier as well.
8. **Stored as full identifier.** `tcw work edit <folder> --parent <other>`
   and `--blocked-by <other folder>` (bare input) in a files-backend project
   write `parent: demo.work/<other>` and `blocked-by: [demo.work/<other>]`
   into `item.yaml`. `tcw capabilities set cli/x --field Subject=term` writes
   `Subject: [demo.taxonomy/term]`; `tcw taxonomy add Pay --kind feature
   --vocab term` writes `vocabulary: [demo.taxonomy/term]`; and
   `PATCH /api/taxonomy/<key>` with `relatesTo: ["term"]` writes
   `relatesTo: [demo.taxonomy/term]`.
9. **Jira.** With the suite's Jira fake: `tcw work new` sets `TCW Item` to
   `<project>.work/<KEY>-<words>`; `tcw work show <KEY>` and
   `tcw work show <project>.work/<KEY>` show that item; and an item whose
   parent is a ticket with no folder in this project and a `TCW Item` of
   `<project>/<folder>` (3.x) lists that ticket's key under `untracked`.
9a. **Jira part way through a migration.** With the suite's Jira fake: two
   tickets of this project whose `TCW Item` is the 3.x value
   `<project>/<folder>`, one for a folder in this project and one for a
   folder that is not here. `tcw work list` does not list either; its
   standard error holds one warning containing `2 Jira tickets`,
   `TCW 3.x TCW Item value`, both keys and `tcw migrate`, and does not
   contain `another copy of this repository`. `tcw validate --remote`
   reports the first ticket, at its item, and the second, at its key, each
   as an error containing `TCW 3.x value` and `tcw migrate`, and reports
   neither with `its ticket's TCW Item is` followed by `not`.
10. **A key no item carries.** In a files-backend project `demo`,
    `tcw work show TCW-120` and `tcw work show demo.work/TCW-120` each exit 4
    with a message containing `no work item in project 'demo' carries the
    key TCW-120`. With the suite's Jira fake, `tcw work show <KEY>` for a key
    no folder of the project carries exits 4 with the same message for its
    project and key.
11. **3.x stored references.** An `item.yaml` with `parent: demo/<folder>`
    is reported by `tcw validate` as an unreadable item naming `parent` and
    `tcw migrate`; a capability with `Subject: [term]` (bare) is reported by
    `tcw validate` naming `Subject` and `tcw migrate`; a `capabilities.yaml`
    entry `cli/x` is refused by the records gate (`tcw work advance --dry-run`
    to the gated stage) naming `tcw migrate`.
12. **`capabilities.yaml` routing.** An item of `app` whose
    `capabilities.yaml` declares `changed: [server.capabilities/x]`, with
    `server` a connected child holding `x`, passes the records gate; the
    same with `server` absent from the machine reports it as could not
    check; `app.capabilities/x` with no such capability in `app` fails.
13. **Cross-project resolution.** Two projects side by side in two git
    repositories, `app` naming `core` under `projects:` (by ID only, as
    TCW-107 leaves the key) with no `extends`: a
    link `[t](tcw://core.taxonomy/term)` in `app` passes `tcw validate`;
    `tcw://core.taxonomy/missing` fails it; with `core`'s folder removed, the
    first link is reported as `unresolved` and `tcw validate` exits 0.
13a. **A misspelt project.** In AC 13's setup, a link
    `[t](tcw://cor.taxonomy/term)`, where nothing names `cor` and no folder
    next to `app` or enclosing it declares it, makes `tcw validate` exit 1
    with an error at the link containing `no project with ID 'cor'` and
    `check the spelling`; `tcw taxonomy show cor.taxonomy/term` exits 1 with
    the same message. With two folders next to `app` both declaring
    `id: lib`, an ID that no `projects:` entry names, a link
    `[t](tcw://lib.taxonomy/term)` makes `tcw validate` report an error at
    the link naming both folders, and `tcw taxonomy show lib.taxonomy/term`
    exits 1. (`core` cannot be the duplicate here: AC 13 names it under
    `projects:`, so TCW-107's graph walk finds the two folders first, and
    `tcw validate` reports the graph problem at the configuration and stops
    before it reads any link, `tcw/validate.py:394-397`.)
14. **Store address.** `app` with `work.path: tcw://workspace.path/docs/app/work`,
    `workspace` and `app` in two repositories side by side and not
    connected (neither names the other under `projects:`, and neither has a
    manifest), so `workspace` is found by TCW-107's search of the folders
    next to `app`: `tcw work new` in `app` creates the item folder under
    `<workspace>/docs/app/work/`, prints `app.work/<folder>`, and
    `tcw work path <folder>` prints that folder. The same location written as
    `tcw://workspace.work.path/../app` is refused by `tcw validate` and by
    `tcw work list` with the `..` rule.
15. **Namespace address and loop.** `app` with
    `work.path: tcw://workspace.work.path/app` resolves to
    `<workspace's work store>/app` and `tcw validate` in `app` fails it as
    nested inside `workspace`'s work store. `p2` with
    `work.path: tcw://p1.work.path/x` and `p1` with
    `work.path: tcw://p2.work.path/y` make `tcw work list` in `p2` exit 1 with
    `store locations loop: p2 work -> p1 work -> p2 work`; `work.path:
    tcw://p2.work.path/x` in `p2` itself fails the same way.
16. **Coinciding stores.** `tcw validate` fails when `app`'s `work.path`
    names the same folder as `workspace`'s work store (through `../`, and
    through a symlink), and when `app`'s `taxonomy.path` lies inside its own
    `capabilities.path`; it passes when `app`'s store is a sibling of
    `workspace`'s work store inside `workspace`'s folder. It also fails the
    first case when `workspace` is a Jira-mode project (its configuration
    names the Jira backend), with no request made to Jira.
17. **Missing project in a location.** `app` with
    `work.path: tcw://gone.path/w`, where `app`'s `.tcw/tcw-manifest.yaml`
    places `gone` at `../gone`, that folder does not exist, and no
    `work.repository` is declared, makes `tcw work list` exit 5 naming
    `gone`.
    With `work.path: tcw://gonne.path/w` instead, where nothing names `gonne`
    and nothing next to `app` or enclosing it declares it, `tcw work list`
    exits 1 with a message containing `check the spelling`.
18. **Names that break the grammar.** `tcw capabilities add 'cli/has.dot'`
    exits 2 and writes nothing; an existing capability folder `cli/has.dot`
    is listed by `tcw capabilities list`, is reported by `tcw validate` as an
    error naming the folder and saying it must be renamed by hand, and
    `tcw capabilities show cli/has.dot` exits 2 naming the same rule.
19. **Hooks and prompts.** A `pre` command binding sees `TCW_SLUG` equal to
    `demo.work/<folder>`; `tcw work stage prompt spec <folder>` prints
    `demo.work/<folder>` wherever it names the item. A `generate:` binding
    receives a document with `"schema": 2` whose `item` has `full-id` equal
    to `demo.work/<folder>` and no `slug`, and the eval harness's
    `evals/assets/gen_requirement.py` run on that document prints the
    marker computed from `demo.work/<folder>`.
20. **Web.** `/api/work/<folder>` and `/api/capabilities/<path>` return
    records with `full-id` and `owner` and no `slug` or `qualified` key; the
    reference suggestions offer `tcw://demo.work/<folder>`,
    `tcw://demo.taxonomy/term` and `tcw://demo.capabilities/cli/x` (a client
    unit test); `/api/resolve` for `tcw://core.taxonomy/term` from `app`
    answers `other-project` with `core`; a parent written through the web app
    is stored as a full identifier. In `app` with
    `capabilities.extends: [core]`, `/api/capabilities/<key>` with the key
    `core.capabilities/cli/y` URL-encoded returns that inherited entry's
    record, and `/api/resolve` for `tcw://core.capabilities/cli/y` answers
    `ok` with `core.capabilities/cli/y` as `key`; for
    `tcw://app.capabilities/cli/x` it answers `ok` with `cli/x`.
20a. **The web app's own items.** Client unit tests: for the project `demo`,
    `isLocal("demo.work/x", demo)` is true and `isLocal("core.work/x", demo)`
    is false; `projectOf("demo.work/x")` is `demo` and `folderOf` of it is
    `x`; `itemKey` of a work record whose `full-id` is `demo.work/x` is `x`,
    and of a capability record whose `full-id` is
    `demo.capabilities/cli/x` is `cli/x`, and of an inherited capability
    record whose `full-id` is `core.capabilities/cli/y` is
    `core.capabilities/cli/y`. Served by `tcw serve`, the board's link for an
    item of `demo` opens `/api/work/<folder>` for that item.
21. **The sweep.** After the change, no code under `tcw/`,
    `web/client/src/`, `scripts/` or `evals/` builds or splits a 3.x name: a
    search for `parse_tcw_uri`, `.qualified`, `tcw://W/`, `tcw://T/` and
    `tcw://C/` outside the migration's own recogniser (2.4) and the tests of
    it finds nothing, and neither does a search for a project ID joined to a
    name with `/` by hand (the regular expression
    `\{[^}]*project[^}]*\}/\$?\{`, which today matches the nine sites of 5.4
    and `Slug.__str__`, `tcw/work/model.py:75`). The plan lists every hit of `partition("/")`,
    `split("/")`, `indexOf("/")` and `lastIndexOf("/")` in those folders,
    and each hit left after the change is on a path on disk, a URL, or an
    id-path that the identifier module has already separated from its
    project and namespace; a reviewer checks the list against a fresh
    search.
22. **The suite, as CI runs it** (`.github/workflows/test.yml`): bare
    `pytest` after `pip install -e '.[dev]'`, which is the `pytest` job, and
    `pnpm install --frozen-lockfile` then `pnpm check:build`, which is the
    `web-build` job, both pass on `v4`. CI runs no other web check; the web
    client's unit tests (`pnpm test`), its type check (`tsc --noEmit`) and
    `pnpm lint` pass as well, and every file this item changes that
    `prettier` covers passes `prettier --check`. A repository-wide
    `prettier --check .` is not a condition: it fails on files this item
    does not touch.
23. **An inherited object with an override.** `app` with
    `capabilities.extends: [core]`, `core` holding `cli/x` at status
    `Missing`, and `app` holding a 3.x override of it setting status
    `Supported`: `tcw capabilities list --json` and
    `tcw capabilities show core.capabilities/cli/x --json` in `app` both give
    status `Supported` for `core.capabilities/cli/x`; `tcw capabilities set
    core.capabilities/cli/x --status Partial` in `app` changes `app`'s
    override and leaves `core`'s `meta.yaml` unchanged; for an item of `app`
    declaring `changed: [core.capabilities/cli/x]`, the records gate's route
    (`route_capability_path`'s answer, checked by a unit test) is `app`'s own
    ledger, not `core`'s store.
24. **Absolute store paths.** In `app`'s `.tcw/tcw-config.yaml`, each of
    `work.path: /tmp/x` and `work.path: ~/x` makes `tcw work list` exit 1 and
    `tcw validate` report an error at `work.path` whose message contains
    `relative to the project`, `tcw://` and `.tcw/tcw-manifest.local.yaml`.
    The same for `taxonomy.path` and `capabilities.path`.
25. **Letter case.** With a capability folder `cli/x`, `tcw capabilities
    show Cli/x` and `tcw capabilities show demo.capabilities/Cli/x` exit 4 on
    any disk; on a disk that ignores case (the test is skipped elsewhere)
    the message names `cli/x`. `tcw work edit <folder> --parent <OTHER>`,
    where only `<other>` exists in a different case, exits 4 and writes
    nothing.

### Coverage

| Design rule | Criteria |
| --- | --- |
| 1.1 grammar; exact case; reserved IDs | 1, 25 |
| 1.2 `.` marks a full identifier | 1, 7, 18 |
| 1.3 id-path of today's objects | 4 |
| 1.4 owner, never `local` | 4, 5, 6 |
| 1.5 one type, one parser; work identifiers equal however made | 1, 21 |
| 1.6 names that break the grammar, and naming one | 18 |
| 2.1 address grammar | 2 |
| 2.2 refused addresses | 2, 14 |
| 2.3 one spelling | 2 |
| 2.4 3.x links, and which message `tcw://p1/` gets | 2, 3 |
| 2.5 resolved from the writer | 13, 14 |
| 2.6 address versus identifier | 7, 8 |
| 3.1 a–d input forms; every option; the key-shaped full identifier; an inherited object through the view; route keys | 7 (a, d, the options), 8 (`--vocab`, `--field`, the `PATCH` route), 9 (b, c), 10 (b and c with no item), 20 (route keys), 23 (the view) |
| 3.2 key lookup through `lookup`; a key no item carries | 9, 10 |
| 3.3 stored as full identifier | 8, 9 |
| 3.4 3.x input and the hint, which never changes the exit | 7 |
| 4.1 lists | 4 |
| 4.2 `show` | 5 |
| 4.3 JSON, schema 2, the `generate:` payload | 6, 19 |
| 4.4 messages, `TCW_SLUG`, prompts | 19 |
| 4.5 web app: records, suggestions, the client's own parsing, an inherited entry's route key | 20, 20a |
| 5.1 every stored field | 8, 9, 11, 12 |
| 5.2 reading 3.x stored values; Jira part way through a migration | 9, 9a, 11 |
| 5.3 writing | 8, 20 |
| 5.4 sweep, including help texts, hand-built names and `evals/` | 6, 19, 21 |
| 6.1 `project_folder` and its four outcomes; one registry per command | 13 (found, not here), 13a (unknown, graph problem), 14 (a project no `projects:` names), 17; the one registry is checked by the plan's unit test |
| 6.2 the owner's own objects, any project; inherited ones through the view | 13, 23 |
| 6.3 outcomes | 13, 13a, 17 |
| 6.4 `tcw validate` | 3, 11, 13, 13a |
| 7.1 plain path or folder address; no absolute path in the shared file | 14, 24 |
| 7.2 resolving, and each outcome of step 1 | 14, 15, 17 |
| 7.3 loops | 15 |
| 7.4 nest or coincide, Jira-mode projects included | 15, 16 |
| 7.5 one function | 14 (`tcw work new`, `tcw work path` and `tcw validate` agree on one folder); the three call sites, and `tree_store_present`'s default, are listed in the plan |

## Risks

- **Size.** Every printed name, every stored reference and every `tcw://`
  link changes form, across both backends, three stores, the CLI and the web
  app. The sweep (5.4) is the defence; the plan may split the store
  locations (Design 7) into its own slice, since it shares only the parser.
- **Test churn.** Most tests compare `<project>/<folder>` text or bare paths.
  As in TCW-106, the plan changes expectations through one helper that
  builds the expected identifier, then reads every failure instead of
  editing assertions to pass.
- **Names that become invalid.** A capability or taxonomy folder whose name
  holds a `.`, a space or another character outside 1.1 is valid in 3.x and
  an error in 4.0 (1.6). `tcw migrate` (TCW-116) must report them, since it
  cannot rename without rewriting references (TCW-114).
- **Configurations that become invalid.** 7.4 fails some valid 3.x
  configurations, such as `capabilities.path: docs` with
  `taxonomy.path: docs/taxonomy`, and 7.1 fails an absolute or `~` store path
  in the shared file. `tcw migrate` (TCW-116) must report both. Test fixtures
  that place stores at absolute temporary paths move to relative ones or to
  `.path` addresses.
- **Override folders.** The 3.x override of an inherited capability lives at
  `<alias>/<path>` in the reader's ledger when its mirror path is taken
  (`tcw/store/fs.py:2676-2681`); that folder is not an object of its own and
  gets no full identifier of its own here. TCW-112 removes overrides by path,
  and TCW-116 moves those folders.
- **Jira field length.** `TCW Item` is a single-line text field (at most 255
  characters in Jira). A flat work identifier is at most the project ID
  plus 134 characters; nested id-paths (TCW-111) can exceed it, which this
  item records on TCW-111.
- **Two notions of "slug".** `TCW_SLUG` keeps its name while the JSON key
  becomes `full-id`. Accepted: the variable's readers only need its value,
  and the design names "slug" as a nickname; TCW-117's guides say both.

Handoffs, which the dispatching session records on each ticket when this
spec is accepted:

- **TCW-107:** this item calls its `FsProjectRegistry.project_folder`
  (TCW-107 Design 2.12) and handles all four of its outcomes (Design 6.1);
  TCW-107 lands first, and this item waits for it.
- **TCW-108:** lands after this item (Notes). This item's tests connect
  projects through the 3.x `projects:` key, by ID only, and TCW-108 converts
  them when it removes the key; this item already makes `open_project` look
  any ID up with `project_folder`, and no longer accepts the 3.x
  `<project>/<folder>` input that TCW-108's rule for a sibling's item keeps
  readable. The plan lists the tests (its Step 17).
- **TCW-109:** store locations cannot be overridden by personal files or
  environment variables (Questions for TCW-99, 1); the design's example
  `TCW_WORK_PATH__MY_PROJ` should not be built.
- **TCW-111:** the 255-character limit of the `TCW Item` field (Risks); the
  grammar of 1.1 sets no limit on a whole identifier, which is TCW-111's to
  add.
- **TCW-112:** the rule that an inherited object is read through the active
  project's view (Design 3.1) is replaced with overrides by path.
- **TCW-113:** the web route key of every inherited entry is its full
  identifier, and `/api/resolve` answers `ok` with it as `key` (Design 4.5);
  the cross-project views build on that key.
- **TCW-116:** report names that break 1.1, stores that nest or coincide,
  absolute or `~` store paths, 3.x `TCW Item` values, and the override
  folders at `<alias>/<path>` (Risks).
- **TCW-117:** the user-facing documents this item's documentation entries
  leave to it, each with what it must say (the plan names them).

## Notes

### Decisions the design left to this spec

1. **id-part grammar** (1.1): letters, digits, `-`, `_`, starting with a
   letter or digit, at most 128 characters, case-sensitive. The design gave
   the character set; the first-character rule keeps a typed part from
   reading as an option, and 128 is today's work folder limit.
2. **`.` decides** (1.2): because neither project IDs nor id-parts contain
   `.`, a parser needs no list of projects to tell a full identifier from an
   id-path.
3. **Input forms** (3.1): full identifier, its address, tracker key bare or
   as `<project>.work/<KEY>` (the design's own example writes
   `--parent planning.work/TCW-120`), and a bare id-path for the active
   project. The design's "references are never shortened" governs what TCW
   stores and prints, not what a person types: TCW-99 success criterion 3
   says a single project in its own repository needs no more than in 3.x,
   and requiring `demo.work/<folder>` for every command in such a project
   would break that, so rule 3.1 (d) stays.
4. **What commands print** (4.1-4.3): full identifiers one per line;
   `full-id:` and `owner:` first in `show`, after the design's sketch, which
   writes `full id:` with a space (`design.md:659`); the hyphen is this
   spec's choice, so the field reads like every other key TCW prints and
   matches the JSON key;
   one JSON key, `full-id`, across all three namespaces, and `"schema": 2`
   because every record's keys change.
5. **Tracker key lookup** (3.2): through the owning backend's existing
   `lookup`, so no backend operation changes.
6. **Address details** (2.1-2.3): folder parts take RFC 3986's unreserved
   characters, since a folder on disk may be named `.github`; one spelling
   per address; a folder address always has a `/` after `.path`.
7. **Two stores of one project** are covered by "never nest or coincide"
   (7.4), for the reason given there.
8. **A key-shaped full identifier is a key** (3.1 c): in a Jira project a
   folder is never only a key, so `<project>.work/<KEY>` can mean nothing
   else. A key no item carries is not found, in every backend, and is never
   read as a folder name (3.2): no backend can hold a folder named only by a
   key, so reading it as one could only give a less helpful message. An
   earlier draft fell through to a folder; the plan review showed that no
   test could observe the fall-through, and that it would lose the message a
   Jira project gives today.
9. **An inherited object through the active project's view** (3.1, 6.2),
   until TCW-112: otherwise `show` of an inherited capability would disagree
   with `list` in the same project, and `set` would have no defined target.
10. **Letter case is exact on every disk** (1.1): one object, one identifier,
    on macOS as on Linux.
11. **No absolute or `~` store path in the shared configuration** (7.1):
    the request asks for "a plain path relative to the project", and a
    `.path` address, with a personal manifest entry where the folder sits
    elsewhere, says the same thing on every machine.
12. **A Jira ticket still holding a 3.x `TCW Item` is left out until
    migrated** (5.2), as the design says of 3.x data; the warning names the
    keys and `tcw migrate` instead of another copy of the repository.
13. **An inherited entry's web route key is its full identifier** (4.5), for
    every inherited entry, so the key does not depend on whether a local
    entry shares its id-path. Settled while planning; it is the one change to
    route keys this item makes (Non-goals).
14. **Jira-mode work stores are compared** (7.4): their folders hold item
    documents, so nesting one inside another store does the same harm.
15. **One registry per command** (6.1, 7.2): every lookup, whichever
    project's file holds the reference, goes to the active project's
    registry, so TCW-107's one-folder-per-ID rule holds across all of them.

### Decided by the user on 2026-10-22

1. **The order of the children is TCW-106, TCW-107, TCW-110, TCW-108,
   TCW-111.** This item lands before TCW-108, so it works with the 3.x
   `projects:` key as TCW-107 leaves it (IDs only), and its tests connect
   projects that way. TCW-108 converts those tests when it removes the key
   (Handoffs).
2. **This repository's own lifecycle is driven with the `tcw` first on
   `PATH`,** the primary checkout's editable install of `main` (3.0.2), which
   imports `main`'s code even when run from the `v4` worktree. Never with the
   worktree's own `.venv/bin/tcw`, and never with `.venv/bin` first on
   `PATH`. The plan lists the ways 4.0 code could otherwise reach this
   repository's live Jira board, each with the rule that prevents it.
3. **CI runs bare `pytest` and `pnpm check:build`** (AC 22), and those are
   what the item's last step runs as CI does. A repository-wide `prettier`
   check is not a condition; only the files this item changes are formatted.

### Revised after the plan review

The plan review found five defects in this spec and a choice the plan had
made beyond it; each is corrected above: the taxonomy CLI has no `set`
command (3.1, 5.1, AC 8); a folder named only by a key cannot exist in a
files-backend project, so AC 10's second half could not pass (3.1, 3.2, AC
10, decision 8); AC 13a's duplicate project is found by TCW-107's graph walk
before any link is read when the duplicated ID is named under `projects:`
(AC 13a); Problem 6 missed `_shared_work_paths` (Problem 6, 7.4); and
`tree_store_present` resolves no location (7.5). The inherited route key is
decision 13.

### Questions for TCW-99

1. **The example in the design should be corrected.** "Personal overrides
   and environment variables" gives `TCW_WORK_PATH__MY_PROJ=/other/path` as
   its example of a variable, which overrides a store location, while the
   same section says neither personal files nor variables can change a
   project's store locations. This spec takes the rule as binding and the
   example as the error: store locations cannot be overridden, here or in
   TCW-109 (Handoffs).
2. **A misspelt project ID is an error, not "could not check"** (Design
   6.1, from TCW-107 Design 2.12). This narrows the design's rule that
   `tcw validate` reports references into a missing project as "could not
   check": that holds for a project a manifest or `projects:` entry names
   but this machine does not have. Accepted by the user on 2026-10-22.

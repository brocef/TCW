# Spec — TCW 4.0: object folders, `tcw-` state files and nested work items

Child 6 of 13 of TCW-99. It carries out these sections of the TCW-99 design
(`docs/work/TCW-99-…/design.md`): "Objects, folders and state files", the
parts of "What any store must support" that place state files in the
deployment layer, the state-file half of "Versions and migration" (every file
TCW writes carries a version), and the `id:` rule in "Full identifiers" ("An
object's ID is its folder's name … Its state file may repeat it as `id:`").
Built on the `v4` branch. The children land in the order TCW-106, TCW-107,
TCW-110, TCW-108, then this item (the user's decision of 2026-10-22, Notes),
so this item builds on all four: TCW-106 (`tcw-version` and its one check,
`version_problem`, `tcw/project_files.py`), TCW-107 (finding a project's
folder), TCW-110 (full identifiers `<project>.<namespace>/<id-path>`, its
id-part grammar, and its parser module, TCW-110 Design 1.5) and TCW-108
(parent links between projects, under `parents:`). By then the 3.x
`projects:` key is gone (TCW-108 Design 3.5), and nothing here uses it.

File and line references are to commit `05d42988` on `v4`; the plan re-checks
them against what TCW-106, TCW-107, TCW-110 and TCW-108 finally land.

Words used throughout: an **object** is a taxonomy entry, a capability or a
work item. Its **state file** is the one YAML file whose presence makes its
folder an object (Design 1). An **organising folder** is a folder in a store
that holds no state file and groups objects (Design 2.3). An object's
**parent** is always the object named by its `parent:` field (a work item's
existing `parent`, and the new one of terms and capabilities, Design 3.1).
It is never a project's parent: the projects a project names under
`parents:` (TCW-108) are called its **parent projects** here, and this item
neither reads nor changes them.

## Capability changes

- **New** `cli/keep-an-objects-other-files-in-its-resources-folder`: anything
  that belongs to an object but is not one of TCW's own files goes in the
  object's `resources/` folder; TCW reads nothing else from the object's
  folder and reports what does not belong there.
- **New** `cli/group-objects-in-organising-folders`: in any of the three
  stores, a folder with no state file may group objects. It is not an object
  and is never listed, but its name is part of the full identifier of every
  object inside it.
- **Changed** `cli/validate-a-project`: reports a file or folder that does not
  belong in an object's folder, a folder named with a reserved name, a 3.x
  `meta.yaml` or `item.yaml`, a state file's version problem, an `id:` that
  differs from its folder's name, a full identifier longer than 255
  characters, and (as a warning) an object nested in a folder that is not its
  parent's; it never checks the YAML files under an object's `resources/`,
  so a broken sample file there stops no other check.
- **Changed** `cli/read-a-file-by-the-format-version-it-records`: objects'
  state files carry `tcw-version` and are read by the same rule as the
  configuration files.
- **Changed** `cli/rely-on-one-output-contract`: taxonomy and capability
  records carry `parent`.
- **Changed** `work/decompose-a-work-item-into-children`: a child item made
  with `--parent` stays at the top of the work store, as today, unless
  `--nest` is also given (or the web app's matching option is ticked); then,
  when the parent is this project's item, the child is created inside its
  parent's folder. Nesting does not set the parent; `--parent` does.
- **Changed** `work/read-a-work-item`, `work/view-the-board`: items are found
  at any depth of the work store, by id-path.
- **Changed** `work/rename-a-work-item`: an item is renamed by its id-path,
  nested or not; an item that has other items nested in it cannot be renamed
  until TCW-114.
- **Changed** `work/keep-work-items-in-jira`: the item folder holds
  `tcw-work-item.yaml`; a key is found at any depth; a full identifier never
  exceeds the 255 characters of the `TCW Item` field.
- **Changed** `work/adopt-a-jira-ticket`: the folder it writes holds
  `tcw-work-item.yaml`; finishing a nested `new` puts the folder inside the
  parent's folder, where the ticket's `TCW Item` says, while a fresh
  adoption stays at the top; a fresh adoption's full identifier fits in 255
  characters, and it is still refused while a folder named for the key with
  no state file sits anywhere in the work store.
- **Changed** `work/delegate-a-work-item-to-another-project`: the `TCW Item`
  it sets in the other project is at most 255 characters.
- **Changed** `taxonomy/remove-a-local-term`,
  `capabilities/remove-a-capability`: the removal is refused while anything
  it would delete holds a state file, or a TCW 3.x `meta.yaml` or
  `item.yaml` (which names `tcw migrate`).
- **Changed** `web/editing`: the create form offers to put a new child's
  folder inside its parent's folder, unticked by default.
- **Changed** `taxonomy/add-a-term`, `taxonomy/browse-the-term-forest`,
  `taxonomy/read-a-term`: a term is a folder holding `tcw-taxonomy.yaml`; a
  term may declare `parent:`; attachments live in `resources/`.
- **Changed** `capabilities/add-a-capability`,
  `capabilities/set-a-capabilitys-status`, `capabilities/read-a-capability`:
  a capability is a folder holding `tcw-capability.yaml`; `add` and `set`
  take `--parent` (`set --parent` is refused on an inherited capability
  until TCW-112); `prependedDocs` and `appendedDocs` name files in
  `resources/`. A new capability's state file still holds the 3.x opaque
  `id: cap-…` until TCW-112.
- **Taxonomy:** new `state-file`, `object-folder`, `organising-folder`;
  changed `work-item`, `term`, `capability`.

## Problem

Today the file that makes a folder an object does not say which kind of
object it is, carries no version, and in one store is not even needed; an
object's folder may hold anything; and a work item cannot sit inside its
parent's folder.

1. **One anonymous file name for two namespaces, another for the third.** A
   taxonomy entry and a capability are both folders holding `meta.yaml`
   (`_entry_readable`, `tcw/store/fs.py:1382-1391`; `_is_capability`,
   `:2255-2256`); a work item holds `item.yaml` (`ITEM_FILE`,
   `tcw/work/fs_backend.py:44`, imported by the Jira backend,
   `tcw/work/jira/backend.py:34`). Nothing in a folder says which store it
   belongs to, and neither file records a format version, which TCW-106
   Design 3.6 leaves to this item.
2. **In the taxonomy store every folder is a term.** `_local_slugs` lists
   every folder under the store root, with or without `meta.yaml`
   (`tcw/store/fs.py:1763-1769`), as the removal code records: "A sub-folder
   without a `meta.yaml` still lists as a term" (`:1884-1886`). So the
   taxonomy store cannot have an organising folder, and a stray folder is a
   term.
3. **Object folders are open sets.** A term's attachments are every
   non-reserved file in its folder (`_load_entry`, `tcw/store/fs.py:1642-1664`,
   the list at `:1659-1663`); a capability's body pulls in any file its
   `meta.yaml` names in `prependedDocs` or `appendedDocs`, read from the
   folder itself (`_compose_body`, `:2311-2326`). A work item's folder is
   bounded only by a rule in prose (`docs/lifecycle/abstraction.md:92-94`):
   nothing checks it, since `work_store_problems` reads only the top of the
   work path (`tcw/work/fs_backend.py:538-549`) and `jira_store_problems` only
   each folder's name and `item.yaml` (`tcw/work/jira/backend.py:121-143`).
   This repository's own work store already holds two files outside that rule:
   `design.md` in the TCW-99 folder and `notes-from-tcw-74.md` in the TCW-76
   folder.
4. **A work item cannot nest.** Both backends refuse an item name containing
   `/` (`FsWorkBackend._folder`, `tcw/work/fs_backend.py:258-262`, and
   `is_item_folder`, `:483-484`; `JiraBackend._key`,
   `tcw/work/jira/backend.py:327-331`, and `link_exists`, `:104-109`), and
   every place that finds items looks only at the top of the work path:
   `Layout.item_folders` (`tcw/work/layout.py:102-109`), `read_all`
   (`tcw/work/fs_backend.py:201`), `work_store_problems` (`:538`),
   `jira_store_problems` (`tcw/work/jira/backend.py:121`), the Jira `lookup`
   (`:320`), the remote check's `_folders` (`tcw/work/jira/remote.py:418`),
   `round_findings` (`tcw/validate.py:659`), the offline `capabilities.yaml`
   check (`tcw/validate.py:634`), the single-target check, which refuses a
   `/` (`tcw/validate.py:500`), and the web app's item list
   (`tcw/serve/work.py:78`). So children sit side by side with their parent,
   as TCW-99's thirteen children do in `docs/work/`.
5. **Only work items have a declared parent.** `Term` and `Capability` have
   no parent field (`tcw/store/base.py:323-343`, `:481-508`); a nested term's
   only link to the term above it is where its folder sits, which
   `tcw taxonomy add --parent` chooses (`tcw/store/fs.py:1830-1843`).
6. **Nested identifiers would overflow the `TCW Item` field.** TCW-110 stores
   an item's full identifier in that Jira field, which holds at most 255
   characters (TCW-110 Risks). A flat work identifier is at most the project ID
   plus 134 characters; a nested one adds 129 per level. The Jira backend sets
   the field after the ticket exists (`create`,
   `tcw/work/jira/backend.py:693-711`), so a value Jira refuses would leave a
   ticket with no item.

## Goals

1. A folder is an object exactly when it holds its namespace's state file:
   `tcw-taxonomy.yaml`, `tcw-capability.yaml` or `tcw-work-item.yaml`, each
   carrying `tcw-version` and read by TCW-106's one check.
2. An object's folder holds its fixed files, the folders of its child
   objects, and one `resources/` folder; `tcw validate` reports anything else,
   and no object or organising folder may take a reserved name.
3. Folders without a state file may organise objects in all three stores.
4. A parent is declared by `parent:` in all three namespaces, never by where
   a folder sits; `tcw validate` warns where an object sits inside another
   object's folder that is not its parent. TCW nests a new work item in its
   parent's folder when asked (`--nest`), and the plan stage prompt always
   asks; the plugin's skills will too (TCW-117).
5. Both work backends find items by id-path at any depth; the backend
   operations are restated for id-paths.
6. No full identifier is longer than 255 characters.
7. `docs/lifecycle/abstraction.md` is amended to allow child folders and
   `resources/`.

## Non-goals

- **Inheritance of taxonomy and capabilities, and overrides by path**
  (TCW-112). The 3.x `overrides:` pointer, `extends`, override folders at
  `<alias>/<path>`, and the capability's opaque `id` (`cap-…`) keep their
  meaning; only the file they sit in is renamed. The opaque `id` is dropped
  in 4.0, but not here: TCW-112 stops writing it once overrides match by
  path, and `tcw migrate` (TCW-116) removes it (Design 1.3; the user's
  decision, Notes). TCW-112 may rework `prependedDocs` and `appendedDocs`,
  which this item only moves into `resources/` (Design 2.2).
- **Moving and renaming objects in general** (TCW-114): moving any object into
  another folder, renaming taxonomy entries and capabilities, renaming a work
  item that has items nested in it, rewriting references in every file
  (Markdown links, `capabilities.yaml`, other namespaces), `tcw -C`, and
  removing `tcw work new --project`. This item changes only `tcw work
  rename`'s backend operation, so that it takes an id-path and refuses an
  item with nested items (Design 5, row 7).
- **Migrating 3.x stores** (TCW-116): renaming `meta.yaml` and `item.yaml`,
  writing `parent:` for today's nested terms, moving stray files into
  `resources/`. This item only recognises the 3.x files and names
  `tcw migrate` (Design 2.6 f).
- **Views across projects** (TCW-113).
- **The naming rule for keys** (TCW-106 Design 5.1) applies to configuration
  files, not state files. State files keep their keys as spelt today
  (`Status`, `relatesTo`, `Superseded by`, `blocked-by`), since no
  environment variable is ever derived from them; the keys this item adds
  (`tcw-version`, `id`, `parent`) follow the rule anyway.
- **An item's `capabilities.yaml`** keeps its name and format and carries no
  `tcw-version`: it is written by people and agents, not by TCW, and is not a
  `tcw-*.yaml` file.
- **A shorter way to type a nested item.** In a files-backend project a
  nested item is named by its whole id-path or its full identifier
  (TCW-110 Design 3.1 d); finding an item by the last part of its id-path
  alone can be added later.
- **Adopting a Jira ticket under its parent.** A fresh adoption with
  `tcw work tickets adopt` still makes the folder at the top of the work
  store; Design 3.2 does not warn about a flat child. Only an adoption that
  finishes a nested create goes inside the parent's folder (Design 6.4).
- **The web app** shows nested items, opens them by id-path, and offers the
  nesting option on its create form (Design 3.3), but does not show
  `resources/` or edit a term's or capability's `parent`.
- **Guides, skills, use cases and eval cases** that name `meta.yaml` or
  `item.yaml` (`docs/guide/`, `skills/taxonomy/SKILL.md:64`, `:84`, `:129`,
  `skills/capabilities/SKILL.md:29`, `:136`, `:143`) are TCW-117's, and so is
  the skill text that has agents pass `--nest` (Design 9.3). This item changes
  only the plan stage prompt's text on where a child goes.
- **This repository's own records** keep `meta.yaml` and `item.yaml` until
  TCW-116 migrates it, because the 3.x CLI that drives its lifecycle reads
  them, as TCW-110's Non-goals say of its references (what this means for
  v4's own code run here is in Risks). This item's own `capabilities.yaml`
  uses the 3.x path form for the same reason.

## Design

### 1. State files

1.1. **Names.** A folder in a namespace's store is an object of that
namespace exactly when it holds that namespace's state file as a file:

| Namespace | State file | Replaces |
| --- | --- | --- |
| taxonomy | `tcw-taxonomy.yaml` | `meta.yaml` |
| capabilities | `tcw-capability.yaml` | `meta.yaml` |
| work | `tcw-work-item.yaml` | `item.yaml` (both backends) |

One module holds these names, the fixed names of 2.1, the reserved names of
2.4 and the walk of 2.5; every reader and writer takes them from it.

1.2. **Contents.** A state file holds what `meta.yaml` or `item.yaml` holds
today, plus `tcw-version` (TCW-106 Design 3.1) as its first line, plus the
optional `id` (1.3) and, for taxonomy and capabilities, the optional `parent`
(3.1). A Jira item's state file holds exactly `tcw-version` and `ticket`,
and may hold `id`; today's rule of exactly one key
(`_item_file_problems`, `tcw/work/jira/backend.py:146-167`) becomes that. The
files backend's list of allowed keys (`KEYS`, `tcw/work/fs_backend.py:53-54`,
enforced at `:105-108`) gains `tcw-version` and `id`.

1.3. **`id:`.** TCW never writes `id` into a taxonomy or work state file.
When one holds `id`, it must equal its folder's name exactly; otherwise
`tcw validate` reports an error at the file (2.6 k), and every command reads
the object by its folder's name regardless.

A capability's `id` is the exception until TCW-112: it keeps its 3.x
meaning, the opaque `cap-…` identifier that a 3.x override points at
(`overrides: <alias>/<cap-id>`, `tcw/store/fs.py:2691`). `tcw capabilities
add` still writes it (`_mint_cap_id`, `tcw/store/fs.py:2211`, called at
`:2488`), and 2.6 k does not apply to it. In 4.0 the opaque identifier is
dropped (the user's decision, Notes): once overrides match by path
(TCW-112), the path is the capability's identity, TCW-112 stops writing
`id: cap-…`, and `tcw migrate` (TCW-116) removes it from existing files.
From then on a capability's `id` follows the first paragraph's rule.

1.4. **Writing the version.** TCW writes `tcw-version: <running version>` as
the first line of every state file it creates (`tcw taxonomy add`,
`tcw capabilities add`, an override folder `tcw capabilities set` creates,
`tcw work new`, `tcw work tickets adopt`), and every later edit keeps the
line exactly as it was (TCW-106 Design 3.2), wherever the file is rewritten
whole (`FsWorkBackend._dump`, `tcw/work/fs_backend.py:169-184`;
`_write_entry` and `_write_meta`, `tcw/store/fs.py:1666-1684`, `:2639-2653`).

1.5. **Reading the version.** Every reader of a state file calls
`version_problem` (TCW-106 Design 3.4a) before it uses anything else in the
file. A state file with a problem (any of TCW-106 Design 3.4's rows a–d) is
never interpreted and never rewritten:

- `tcw validate` reports an error naming the file and `tcw-version`, with
  TCW-106's message for the row, and runs no other check of that file's
  contents.
- A files-backend item: the item is unreadable (`Unreadable`,
  `tcw/work/fs_backend.py:74-84`), so `show` exits 1 naming the file, and
  `list` exits 1 as it does for any unreadable item today (`:336-339`).
- A Jira item: the item is still read from Jira, for every row, because the
  ticket it reads is named by the folder's key and nothing is taken from the
  file. `tcw validate` reports the version problem in place of the checks of
  the file's keys and link (`_item_file_problems`,
  `tcw/work/jira/backend.py:146-167`), so a file from a newer TCW with a key
  this TCW does not know is reported as newer, never as "must hold exactly
  …". The one command that writes the file, `tcw work tickets adopt` when it
  finishes a folder (`tcw/work/jira/tickets.py:183-185`), refuses with the
  message and writes nothing.
- A term or capability: `list` leaves the object out, prints every other
  object as usual (its `--json` output holds no record for it, so no new
  record shape appears), prints the message naming the file on standard
  error, and exits 1, as a work `list` with an unreadable item does. `show`,
  `set`, `reset` and `rm` of it exit 1 with the message and change nothing,
  so a file from a newer TCW is never rewritten in an older format.

### 2. Object folders

2.1. **What an object's folder holds** (decided by the design; the work list
is "as today", `docs/lifecycle/abstraction.md:92-94`):

| Namespace | Fixed files and folders |
| --- | --- |
| taxonomy | `tcw-taxonomy.yaml`, `description.md` |
| capabilities | `tcw-capability.yaml`, `description.md` |
| work | `tcw-work-item.yaml`, `capabilities.yaml`, `comments/`, and one folder per stage named in the stage table (`STAGES`, `tcw/work/model.py:305-319`), holding what the layout names there (`tcw/work/layout.py:1-10`) |

and, in every namespace, one `resources/` folder and the folders of its
child objects. Hidden names (starting with `.`) are ignored, as today
(`tcw/work/layout.py:108-109`; `_load_entry`, `tcw/store/fs.py:1662`).

2.2. **`resources/`** holds anything else that belongs to the object, at any
depth, in any format. TCW never writes into it. An object's `resources/` is
found by its exact spelling (TCW-110 Design 1.1), so on a disk that ignores
letter case a folder spelt `Resources/` is never read as it, and is reported
as 2.6 c. Commands read `resources/` in two places only:

- A term's `attachments` (`Term.attachments`, `tcw/store/base.py:336`, shown
  by `tcw taxonomy show`, `tcw/taxonomy/cli.py:38`, `:84`) are the files under
  its `resources/`, as paths relative to the term's folder
  (`resources/diagram.png`), sorted; no longer the loose files of the folder.
- A capability's `prependedDocs` and `appendedDocs` entries are paths
  relative to the capability's folder that must lie inside its `resources/`
  (`resources/camera.md`). An entry outside it is an error in
  `tcw validate` and is not read into the body.

Containment is unchanged: a file that resolves outside the store is not read
(`_within_store`, `tcw/store/fs.py:1393-1410`).

`tcw validate` reads `resources/` in one more place, and the checks before a
removal search it (2.5):

- Its `tcw://` link check reads every Markdown file under `resources/`, as it
  reads every Markdown file in a store today (`_file_findings`,
  `tcw/validate.py:280-349`), since a design kept there (TCW-116 moves them
  there) is where broken links will be. A Markdown file under `resources/`
  that is not valid UTF-8 is a warning, `not checked for tcw:// links: not
  valid UTF-8`, not today's error (`_read_text`, `tcw/validate.py:82-91`),
  since `resources/` may hold anything.
- Its YAML well-formedness check skips every file under `resources/`. So a
  sample YAML file of any shape there is never reported, and in particular
  never switches off the taxonomy and capability checks, which today any YAML
  syntax error under a store root does (`yaml_syntax_error`,
  `tcw/validate.py:310`, `:317`, `:325`, read at `:418-421`). Nothing found under
  `resources/` stops another check (Notes, review decision 14).

2.3. **Organising folders.** In any store, a folder with no state file that
sits directly in the store's root or in another organising folder is an
organising folder: it is not an object, is never listed, and its name is a
part of the id-path of every object below it (TCW-110 Design 1.1). It is the
taxonomy store's new capability (Problem 2); the capabilities store's group
folders (`cli/`, `work/`) are organising folders already; and a work store
may now hold them too (`docs/work/2026/…`). Inside an object's folder there
are no organising folders: every folder there is a fixed folder,
`resources/`, or a child object (Notes, decision 2).

2.4. **Reserved names.** These names may not be the name of an object or of
an organising folder, compared ignoring letter case (so `Resources` on a disk
that ignores case is the same folder):

| Store | Reserved folder names |
| --- | --- |
| taxonomy, capabilities | `resources` |
| work | `resources`, `comments`, and every stage name in the stage table |

The state files and `description.md` cannot collide, since an id-part never
contains a `.` (TCW-110 Design 1.1). Reserving per store keeps `review` or
`plan` free as taxonomy terms. A reserved folder found anywhere but its own
place (directly inside an object folder of that store) is an error (2.6 c).
`tcw taxonomy add` and `tcw capabilities add` refuse a reserved name as a
usage error (exit 2) before writing anything; a work item's folder can never
take one, since it always starts with a date or a ticket key.

2.5. **The walk: finding a store's objects.** One function lists every
object folder in a store, and every lister calls it (Design 8). From the
store root:

1. The store root is never an object.
2. Visit a folder's entries in name order, skipping hidden names. A folder
   reached through a symbolic link is not visited, as the tree stores already
   behave (`tcw/store/fs.py:1764-1766`).
3. A folder holding the state file is an object. Inside it, the fixed files
   and folders of 2.1 and `resources/` are not visited; every other folder is.
4. A folder without the state file is visited whether it is an organising
   folder or, wrongly, a folder inside an object folder (2.6 b): the objects
   below it are still listed, so a misplaced folder hides nothing. The same
   holds for a folder with a reserved name outside its own place (2.6 c).
   Every command reads, lists and accepts such an object as any other, and
   `tcw validate` reports the misplaced folder above it.
5. The object's id-path is its folder's path from the store root, joined
   with `/`.

For a tree store, an object whose folder or state file resolves outside the
store is not read, as today (`_entry_readable`, `tcw/store/fs.py:1382-1391`).

Whether one given id-path is an object is answered by the same rule without
listing the store: its folder holds the state file, and no folder on the way
down from the store root is a symbolic link, or a fixed folder of 2.1 or
`resources/` of an object above it. For work, `is item folder` adds the
backend's naming rule for the last part (Design 5, row 12). So an id-path is
accepted by a command exactly when the walk would return it.

**The checks before a removal are not listings.** `tcw taxonomy rm` and
`tcw capabilities rm` delete an object's whole folder, hidden folders, fixed
folders and `resources/` included, so the check that refuses a removal with
something nested below it (`tcw/store/fs.py:1888-1889`; `_nested_entries`,
`:2528-2534`) never uses the walk, which skips hidden folders and never
enters `resources/` (step 2, 3). It searches everything the removal would
delete, below the object's own folder, and refuses (`Refused`, exit 3,
changing nothing) when it finds:

- a state file of any namespace: `cannot remove '<id-path>': nested under
  it: <path>, … (remove those first)`, today's message; or
- a TCW 3.x `meta.yaml` or `item.yaml`: `cannot remove '<id-path>': <path>
  holds a TCW 3.x <file>; run 'tcw migrate' in this project first`, so a
  folder not yet migrated is never deleted without a word (Notes, review
  decision 16).

This keeps today's protection, which `tests/test_capabilities_rm.py:192-200`
(`test_remove_refuses_capability_nested_in_a_dot_directory`) locks in. A
state file or 3.x file kept under `resources/`, a sample for instance, also
blocks the removal; the message names its path, so the person can move or
delete it, and that is intended.

**3.x override folders.** A capability folder whose state file holds
`overrides:` (at the mirror path or at `<alias>/<path>`,
`tcw/store/fs.py:2676-2681`) is returned by the walk like any folder holding
the state file. The capability listers keep separating it by its
`overrides:` key, as today (`_local_paths`, `tcw/store/fs.py:2273-2277`), so
it is not listed as an object of its own and gets no full identifier of its
own (TCW-110 Risks). Rows k to n of 2.6 skip it; rows a, b and j apply to
its folder as to any capability's. An `<alias>/` folder with no state file
is an organising folder, and is not empty for row e when it holds an
override. TCW-112 replaces these folders with overrides by path.

2.6. **What `tcw validate` reports** in each store it checks:

| # | Finding | Severity and message (shape) |
| - | ------- | ---------------------------- |
| a | a file in an object's folder that is not one of its fixed files | error: `is not one of <full id>'s files; move it into resources/` |
| b | a folder in an object's folder that is not fixed, not `resources/`, and holds no state file | error: `is not a child object of <full id>: it has no <state file>; give it one, or move it into resources/` |
| c | a folder with a reserved name outside its own place | error: `'<name>' is reserved in the <namespace> store` |
| d | a non-hidden file directly in the store root or an organising folder, other than a file another check already reports (a tree store's leftover `config.yaml` at its root, `_legacy_config_problems`, `tcw/store/fs.py:1619-1640`) | warning, as today for the work store's root (`tcw/work/fs_backend.py:541-543`): `is not part of any object` |
| e | an organising folder with no object anywhere below it | warning: `holds no TCW object` |
| f | a folder holding a 3.x `meta.yaml` or `item.yaml` and no state file | error: `holds a TCW 3.x <file>; run 'tcw migrate' in this project` |
| g | a state file in the store root | error: `the store's root is not an object; move this file into an object's folder` |
| h | work: a folder whose name follows the backend's item rule but which has no state file | error (in Jira mode, today's `is missing; it holds the ticket's link`, `tcw/work/jira/backend.py:151`); the folder is not an item (Design 6.1) |
| i | work: a folder holding the state file whose name breaks the backend's rule | error, as today (`tcw/work/fs_backend.py:545-548`; `tcw/work/jira/backend.py:125-130`, which now applies only to a folder holding the state file) |
| j | a state file's version problem | error (1.5); no other check of that file's contents runs |
| k | an `id` that differs from the folder's name (taxonomy and work; capabilities only once TCW-112 drops the opaque `id`, 1.3) | error (1.3) |
| l | terms and capabilities: a `parent` that is not a full identifier of an object in the same namespace, names the object itself, or makes a loop | error; a parent in a project not on this machine is "could not check" (TCW-110 Design 6.3). For work, the existing rules, unchanged: a `parent` naming no item is a warning (`reference_problems`, `tcw/work/references.py:48-51`), and a self-parent or a loop is refused when it is written (`validate_changes`, `tcw/work/model.py:188-233`) |
| m | an object nested in the folder of an object that is not its `parent` | warning (3.2) |
| n | an object whose full identifier is longer than 255 characters, such as one placed by hand (3.x override folders excepted, as above) | error at its state file: `<full id> is <n> characters; a full identifier is at most 255` (4.2) |

Rows a and b replace the work store's "is not an item folder" error for any
folder directly in the work path (`tcw/work/fs_backend.py:545-548`), which
row h and the organising-folder rule now split. A folder found by row f is
not an object, so the objects below it are found by the walk as any others;
row f takes the place of row h for it. Rows b and c name the folder they
report; the objects below it stay readable (2.5 step 4), so the message
names nothing more.

Row l's two severities differ on purpose, and neither should be changed to
match the other. A work item's missing parent stays the warning it is in
3.x, because work items are finished, discarded and moved between projects
all the time, and changing it would turn existing passing projects into
failing ones. A term's or capability's `parent` is new in this item, so it
starts strict, as every other reference between terms and capabilities is
(AC 13).

Row n is checked on every object the walk lists, in both tree stores and both
work backends. The limit is applied where an identifier is parsed from text
and where TCW builds one (4.2), never when an object found on disk is given
its identifier, so an over-long object made by hand is still listed and read,
and row n is what reports it.

### 3. Parents and nesting

3.1. **`parent:` in all three namespaces.** A work item's `parent` is
unchanged (files: its state file; Jira: the ticket's parent link). A term's
and a capability's state file may hold `parent: <full identifier>` of an
object in the same namespace, in any project TCW can locate. Taxonomy and
capability records gain `parent` (the full identifier, or null) in JSON and
in `show`, after `owner` (TCW-110 Design 4.2, 4.3). Nothing else reads it in
this item.

3.2. **The folder's parent, and when the two disagree.** An object's *folder
parent* is the object whose folder directly holds its folder, or none when
its folder sits in the store root, in an organising folder, or in any other
folder that holds no state file, such as a misplaced folder of 2.6 b or c (an
item in `<epic>/drafts/` has no folder parent; `tcw validate` reports
`drafts/` instead, AC 6a). Where an object
has a folder parent and its `parent` does not name that object (it names
another, or none), `parent` decides and `tcw validate` warns:
`<full id> sits in the folder of <folder parent>, but its parent is <parent or "not set">; parent: decides (set it to <folder parent>, or move the folder)`.
An object with no folder parent is never warned about, whatever its `parent`
says: a flat child, a parent in another project, and an adopted ticket
(Non-goals) are all ordinary (Notes, decision 3). For a files-backend item
and for terms and capabilities the check is offline. For a Jira item the
parent is on the ticket, so the check runs only under `tcw validate
--remote`, beside the existing remote checks (`tcw/work/jira/remote.py`).

3.3. **Where a new child goes.** For work items nesting is asked for, never
assumed (the user's decision, Notes):

- `tcw work new --parent <P>`, and the web app's create with a parent: the
  new folder is made at the top of the work store, as today.
- `tcw work new --parent <P> --nest` (new option), and the web app's create
  with its new "inside the parent's folder" option ticked (off by default;
  the create request carries `nest: true`): when `<P>` is an item of the
  active project, the new folder is made inside `<P>`'s folder, wherever that
  folder sits. When `<P>` is in another project, the folder is made at the
  top, the command succeeds, and standard error says
  `not nested: <P> belongs to <project>`, so a caller that always passes
  `--nest` (the plan stage prompt, Design 9.3) never fails on it. `--nest`
  without `--parent` is a usage error (exit 2) before anything is created.
- `tcw taxonomy add <Name> --parent <P>`: when `<P>` is a term of the active
  project's own store, the folder is made inside `<P>`'s, as today
  (`tcw/store/fs.py:1839-1843`), and `parent: <P's full identifier>` is
  written; otherwise the folder is made at the store root with `parent:`
  written. This keeps today's behaviour, and needs no `--nest`.
- `tcw capabilities add <id-path> --parent <P>` (new option): the folder is
  made at `<id-path>` as given, and `parent:` is written. When that folder has
  a folder parent and it is not `<P>`, the 3.2 warning is printed on standard
  error and the command still succeeds. When it has no folder parent (it sits
  in the store root or an organising folder, such as `cli/`), nothing is
  printed, as 3.2 says.

3.4. **Changing a parent never moves a folder.** `tcw work edit --parent` and
`tcw capabilities set --parent <P>` (new option; an empty value clears it)
change only `parent`, and print the 3.2 warning on standard error when the
result disagrees with the folder. Moving the folder is TCW-114's. On an
inherited capability, `tcw capabilities set --parent` is refused (`Refused`,
exit 3, `the parent of <full id> is set in project '<owner>'`) until TCW-112:
the only place to write it here would be an override folder, which TCW-112
replaces, so writing one would leave TCW-112 data to migrate. The whole
command is refused before anything is written, even when other flags such
as `--status` are given with `--parent`. A term's
`parent` is changed by editing its state file, as `relatesTo` is today
(`skills/taxonomy/SKILL.md:129`).

### 4. Id-paths and length

4.1. **A nested object's id-path** is its folder's path from the store root
(2.5 step 5), and satisfies TCW-110's grammar (TCW-110 Design 1.1): each
folder is one id-part, joined by `/`. An item nested in an item reads
`tcw.work/TCW-99-overhaul/TCW-111-object-folders`. Every object whose folder
path is unchanged keeps exactly the identifier TCW-110 gives it (TCW-110
Design 1.3), including capabilities in group folders such as `cli/`, which
are organising folders (2.3). The one exception is a taxonomy folder with no
`meta.yaml`, which 3.x lists as a term (Problem 2): it is an organising
folder now and has no identifier.

4.2. **At most 255 characters.** A full identifier, in every namespace and
backend, is at most 255 characters, the length of the `TCW Item` field; one
rule for all three keeps an identifier storable in any backend a project
might move to. This item adds the check to TCW-110's parser module (TCW-110
Design 1.5), which then refuses longer text as a usage error naming the
limit; TCW-110 itself builds nothing for it. It is enforced:

- `tcw taxonomy add`, `tcw capabilities add`: a usage error (exit 2) before
  anything is written.
- `tcw work new` and the web app's create: the title words are shortened to
  fit (4.3).
- `tcw work tickets adopt`, a fresh adoption (`<KEY>-<title words>`,
  `tcw/work/jira/tickets.py:160`, whose `TCW Item` is set before any folder
  is written, `:178-180`): the title words are fitted with the real key,
  which is known before anything is written (4.3), and when fewer than 8
  characters are left it is a usage error (exit 2) before the edit, so
  nothing changes. A resumed adoption takes the `TCW Item` Jira already
  holds, which was within the limit when it was set.
- Delegation into another project (`tcw work new --project`, which sets that
  project's `TCW Item` to `<KEY>-<title words>` after the ticket exists,
  `tcw/work/jira/tickets.py:385-388`), until TCW-114 removes it: the words
  are fitted to the other project's room with the real key, by the rule for
  after the ticket exists (4.3).
- `tcw work rename`: a usage error (exit 2), changing nothing, when the
  item's new identifier would exceed the limit. (An item with nested items
  is refused before this check, Design 5 row 7.)
- `tcw validate`: an error for an existing object whose identifier exceeds
  it (2.6 n), such as one placed by hand.

The parser's check bounds the text a person types or a file stores, which
for a full identifier is the identifier itself. Text typed in a shorter form
(an id-path, TCW-110 Design 3.1 d) is bounded by the same 255 characters,
but its full identifier is checked only where TCW builds one: by the
commands above, and by `tcw validate`. That difference is intended: an
over-long object placed by hand can still be named by its id-path, to rename
it shorter.

4.3. **Title words that fit.** `title_words` already takes a limit
(`tcw/work/model.py:78`). When a backend makes an item's folder name, the
limit is the smaller of today's (`FOLDER_LIMIT - PREFIX_ALLOWANCE`,
`tcw/work/model.py:24-27`) and the room left under 4.2 once the project ID,
`.work/`, the parent's id-path and `/` (when nested) and the prefix are
counted, where the prefix includes the `-` that joins it to the words (as
`PREFIX_ALLOWANCE` already does). The files backend counts its real prefix,
a date and `-`, 11 characters. The Jira backend does not know the key before
the ticket exists, so it counts the prefix at `PREFIX_ALLOWANCE` (20)
characters for the check below, then recomputes the room with the real key
once Jira has answered, before it sets `TCW Item`
(`tcw/work/jira/backend.py:693`).

**After the ticket exists, nothing is refused for length.** A key is
normally shorter than the allowance, so the room only grows; but a Jira
administrator can allow longer project keys, and a key of more than 19
characters makes the room smaller than the check before allowed for. Then
the title words are cut to the room that is left, however short (one
character at least). Only when not even one character is left (a parent's
id-path within a few characters of the limit, and an unusually long key) is
`TCW Item` left unset, and the command stops with today's message for a
ticket with no item: finish with `tcw work tickets adopt <KEY>`
(`tcw/work/jira/backend.py:705-719`), which makes a fresh adoption at the
top (6.4). A usage error after the ticket exists would leave a ticket with no
item and no way named to finish it, which is Problem 6's failure.

Before anything is created, when the room leaves fewer than 8 characters for
title words, the command is a usage error (exit 2), and with Jira no ticket
is created. When the item is nested, the message names the parent and says
to nest the item higher or not at all (leave out `--nest`). When it is not
nested, only a project ID longer than 230 characters (221 with Jira, by
255 less `.work/`, the prefix and 8) can cause this
(project IDs have no length limit, `PROJECT_ID_PATTERN`,
`tcw/store/project.py:25`), and the message names the project ID and says it
leaves no room for any item.

### 5. The work backend interface for id-paths

Every operation that takes a folder name today takes an id-path instead (a
string that may contain `/`). No operation is added or removed; there are
still twelve. The parameter is renamed `id_path` in `tcw/work/backend.py`.

| # | Operation | Today | 4.0 |
| - | --------- | ----- | --- |
| 1 | create | makes `<prefix>-<words>` directly in the work path (`tcw/work/fs_backend.py:301-307`; `tcw/work/jira/backend.py:693`, `:641-650`) | gains a `nest` argument (false by default). With `nest` true and a parent that is one of this backend's items, makes the folder inside the parent's folder; otherwise at the top, as today (3.3). Title words fit (4.3); writes `tcw-version` (1.4) |
| 2 | read | one folder name; `/` refused (`tcw/work/fs_backend.py:258-262`; `tcw/work/jira/backend.py:327-331`) | an id-path, found only when `is_item_folder` (12) accepts it; each part is matched with its exact spelling (TCW-110 Design 1.1) |
| 3 | list | items at the top only (`tcw/work/fs_backend.py:201`; Jira keeps a ticket only when its folder is at the top, `tcw/work/jira/backend.py:474-476`) | every item the walk (2.5) finds; Jira keeps a ticket whose `TCW Item` names an id-path at which `is_item_folder` holds |
| 4–6, 9, 10 | update, set stage, comment, read request, read comments | a folder name | an id-path; otherwise unchanged |
| 7 | rename | changes the folder's words and rewrites this project's `parent` and `blocked-by` naming it (files, `tcw/work/fs_backend.py:424-477`) or its `TCW Item` (Jira, `tcw/work/jira/backend.py:870-909`) | takes an id-path, at any depth. When any item is nested in the item's folder (the walk finds an item below it), it is refused (`Refused`, exit 3) before anything changes: `<full id> has items nested in it (<first nested full id>, …); renaming it waits for TCW-114`. Otherwise it changes the words of the id-path's last part, keeping its date or key, and rewrites what it rewrites today with the new full identifier: files, `parent` and `blocked-by` naming it in every state file of the project's work store; Jira, the renamed ticket's `TCW Item`, in today's order (Design 6.3) |
| 8 | lookup | Jira: scans the top of the work path for the key (`tcw/work/jira/backend.py:314-325`); files: None (`tcw/work/fs_backend.py:480-481`) | Jira: scans every item folder the walk finds, and returns its id-path; a key on two folders anywhere is the existing error. Files: unchanged |
| 11 | current user | unchanged | unchanged |
| 12 | is item folder | a name directly under the work path (`tcw/work/fs_backend.py:483-484`; `tcw/work/jira/backend.py:311-312`) | an id-path at any depth, accepted exactly when the walk (2.5) would return it as an item: its folder holds `tcw-work-item.yaml`; its last part follows the backend's naming rule (files: a real date then words, `ITEM_FOLDER`, `tcw/work/fs_backend.py:46`; Jira: `KEY_FOLDER`, `tcw/work/jira/backend.py:56`); and no folder on the way down is a symbolic link, or a stage folder, `comments/` or `resources/` of an item above it. A misplaced folder above it (2.6 b or c) does not stop it being an item; `tcw validate` reports that folder. In Jira mode this now needs the state file, where today the key in the name is enough (Design 6.1). It reads the work path alone, never the network |

`Layout.item_folders` (`tcw/work/layout.py:102-109`) becomes the walk over
the work store, returning id-paths, which callers filter with
`is_item_folder` as the web app does today (`tcw/serve/work.py:78`). Since
row 12 is the walk's own rule, the filter drops only folders whose last part
breaks the backend's naming rule (2.6 i), never an item below a misplaced
folder.
`Layout.item_dir` joins the id-path onto the work root
(`tcw/work/layout.py:90-91`), which already works for a path with `/`.

### 6. The Jira backend

6.1. **Folders.** A Jira item folder is named `<KEY>-<words>` at any depth;
`folder_key` (`tcw/work/jira/backend.py:98-101`) reads the id-path's last part.
`link_exists` (`:104-109`) takes an id-path and answers by 5 (12). A folder
in a Jira work store that is not named for a key and holds no state file is
an organising folder (2.3), where today it is an error
(`jira_store_problems`, `:123-130`); that error now applies only to a folder
holding the state file (2.6 i).

A change in behaviour: today `JiraBackend.is_item_folder` is `link_exists`
(`:311-312`), which accepts any key-named folder with or without `item.yaml`
(`:104-109`), so `tcw work show <KEY>` and the offline reference checks find
an item whose `item.yaml` is missing, and only `tcw validate` complains. In
4.0 a key-named folder without `tcw-work-item.yaml` is not an item, as the
design says ("only if it holds the state file"): `show` of its key is "not
found", a reference to it is reported as naming no item, and `tcw validate`
reports the folder (2.6 h). A key-named folder whose state file has a
version problem is still an item (1.5).

6.2. **`TCW Item`** holds the full identifier with its whole id-path
(TCW-110 Design 5.1), at most 255 characters (4.2).

6.3. **Renaming.** Only an item with no items nested in it is renamed (row 7),
so a Jira rename changes one ticket's `TCW Item`, in today's order and with
today's setting back when the folder move fails (`:870-909`, `:897-904`).
The item itself may be nested; its new full identifier keeps its parent's
id-path.

6.4. **Finishing a nested create with `tcw work tickets adopt`.** When
`create` stops after the ticket exists, its message says to finish with
`tcw work tickets adopt <KEY>` (`:705-719`). Two cases:

- `TCW Item` could not be set: the ticket names no item, so adopt makes a
  fresh adoption, at the top of the work store (Non-goals). The item is a
  flat child; its parent link stays on the ticket, and 3.2 does not warn.
- `TCW Item` was set but the folder could not be written: adopt resumes and
  takes the folder from `TCW Item` (`tcw/work/jira/tickets.py:142-153`,
  `:183-185`), which for a nested create is the nested id-path, so it makes
  the folder inside the parent's folder. `lookup` returns an id-path, so
  adopt's comparison of the folder found with the one the ticket names
  (`here != named.folder`, `:147`) compares id-paths, and stays correct.

**Folders named for the key with no state file.** Once a key-named folder
without `tcw-work-item.yaml` is not an item (6.1), `lookup` never returns
one. Adopt depends on seeing such folders (`tcw/work/jira/tickets.py:138-159`):
a folder left without its file by an adoption that stopped is finished only at
a status nothing has moved the ticket on from (`:150-155`), a moved-on ticket
whose file is gone is refused as "already the item" rather than taken back,
and a fresh adoption is refused while any folder for the key exists
(`:158-159`). So adopt does not ask `lookup`. It asks for every folder named
for the key at any depth, with a state file or without one, and keeps
today's rules on that answer unchanged: a stateless folder is "unfinished"
exactly as today, two folders for one key are today's error naming both
id-paths, and `here != named.folder` (`:147`) compares id-paths. This is the
one place outside `tcw validate` that sees a key-named folder with no state
file; every other command treats it as no item.

6.5. **`tcw validate --remote`** compares each item folder the walk finds with
its ticket (today only the top, `tcw/work/jira/remote.py:415-421`), and adds
the 3.2 check.

### 7. The files backend

7.1. An item's `created` date comes from the last part of its id-path
(`tcw/work/fs_backend.py:157`), and `rename` keeps the date of that part
(`:426`).

7.2. Renaming moves the item's folder in one `os.rename` (`:452`), within
the folder that holds it; it then rewrites references as row 7 says,
reporting a reference it could not rewrite as today (`:455-472`), and lists
the lines of other files that still name the old identifier, as
`report_mentions` does (`:211-223`). It searches for the old id-path, which
for an item at the top is the old folder name it searches for today, so a
different item with the same last part under another parent is not
reported.

### 8. The sweep

Repository-wide over `tcw/`, `web/client/src/`, `scripts/` and `evals/`:

- every reference to `meta.yaml`, `item.yaml` or `ITEM_FILE`: today in
  `tcw/store/fs.py` (39 lines, including `OWNED_YAML_NAMES`, `:800`, which
  becomes the three state files), `tcw/validate.py` (`:300-304`, `:545`,
  `:592`), `tcw/work/fs_backend.py`, `tcw/work/jira/backend.py` and
  `tcw/work/jira/tickets.py` (`:153`, `:183`); none in `web/client/src/`,
  `scripts/` or `evals/`;
- every scan of the top of a store, listed in Problem 4, and the tree stores'
  own listings (`_local_slugs`, `tcw/store/fs.py:1763-1769`;
  `_all_meta_dirs`, `:2258-2271`), which all call the walk (2.5). The
  nested-object checks before a removal (`:1888-1889`, `:2528-2534`) are not
  listings and keep searching the folder itself (2.5, "The checks before a
  removal are not listings"), now for the state files and the 3.x names;
- every refusal of a `/` in a work item's name (Problem 4) and every
  `folder[:10]`-style read of a folder name that now takes the last part;
- the web app's item routes, which already take a path parameter
  percent-encoded as one segment (`ONE`, `tcw/serve/work.py:583`;
  `ITEM`, `tcw/serve/files.py:357`; decoded once by `Request.param`,
  `tcw/serve/server.py:172-175`; encoded by `encodeRef`,
  `web/client/src/model/api.ts:86`), so an id-path with `/` reaches them as
  one value; the check that a reference names an item of this project
  (`tcw/serve/work.py:374`) uses the walk.

The plan lists each site.

### 9. Documents and shipped text

9.1. **`docs/lifecycle/abstraction.md`** is amended deliberately, as the
request asks:

- The bullet at `:92-94` becomes: treating an object's folder as an open set
  of files — _it is bounded: its state file and fixed files (for a work item,
  `tcw-work-item.yaml`, `capabilities.yaml`, stage folders holding
  `<stage>.md`, `round-N.md` and handoffs, and `comments/`; for a taxonomy
  entry or a capability, its state file and `description.md`), the folders of
  its child objects, and one `resources/` folder for anything else._
- The interface list (`:46-66`): **read**, **update** and the others take an
  item's id-path, "its folder's path in the work store, which may pass through
  its parent's folder and organising folders"; **create** adds "inside its
  parent's folder when asked to nest it and the parent is one of this
  backend's items"; **rename**
  adds "it takes an id-path, and refuses an item that has items nested in
  it"; **lookup** returns an id-path; **is item
  folder** reads "a folder at any depth under the work path".
- A sentence under "Abstract spine": where a folder sits never declares a
  parent; `parent` does.

9.2. **`tcw/work/backend.py`**: its docstring says "Eleven operations"
(`:8`) for an interface of twelve; it says twelve.

9.3. **Encouraging nesting.** The design asks that the plugin's skills and
the stage prompts encourage nesting; the CLI only offers it (`--nest`, 3.3).
The two halves land in different items:

- **The plan stage prompt is this item's.** It is shipped with the CLI
  (`tcw/work/prompts/plan.md`, printed by `tcw work stage prompt plan`), it
  names the flag this item adds, and it would name a flag that does not exist
  if it landed before this item. Step 6 (`tcw/work/prompts/plan.md:38-46`)
  becomes: each part is made with `tcw work new "<title>" --parent <slug>
  --nest`, which puts its folder inside the parent's folder so the folders
  read the way the items relate; `--parent`, not the folder, is what makes
  it a part. The prompt passes `--nest` every time, including for a parent
  that cannot hold the part's folder (3.3 prints a note and goes on).
- **The skills are TCW-117's** (a handoff): the `work` skill's "Epics are
  parents" bullet (`skills/work/SKILL.md:90-92`) and its command reference
  (`skills/work/references/commands.md:10`) always pass `--nest`; the
  `taxonomy` skill's nesting bullet (`skills/taxonomy/SKILL.md:91`) adds that
  `--parent` also records the parent; the `capabilities` skill gains
  `--parent` on `add` and `set`. Until then the skills say what they say
  today, which stays true: a child made without `--nest` is flat, as in 3.x.

TCW-114 rewrites step 6's `--project` half; the two edits meet in that one
paragraph.

9.4. **The example commit hook** (`docs/guide/examples/commit-item-after-move.sh`),
which this repository binds after every move, stages and commits everything
under `$TCW_ITEM_PATH` (`git add -A -- .`, then `git commit … -- .`). Once
children nest, that would commit a child's unfinished files with the
parent's move. Leaving the child out of `git add` alone is not enough: a
`git commit` given paths commits the working-tree content of every tracked
file under them, staged or not. So the hook leaves out every folder below the
item that holds `tcw-work-item.yaml` from both the `git add` paths and the
`git commit` paths (git's `:(exclude)<path>` form), and checks for staged
changes with the same paths. Its search for those folders does not enter
hidden folders, `resources/`, `comments/` or stage folders, as the walk does
not (2.5), so a sample state file kept in `resources/` never leaves that
folder out of the commit. A folder the search cannot read fails the hook,
which the move reports as a failed `post` check, rather than letting it
commit files it could not sort.

## Abstraction litmus test

| Operation | Layer | Verdict |
| --- | --- | --- |
| An item's id-path may hold its parent's path (Design 4.1, 5) | model | Any store can keep an id-path as a string with `/` in it; a database keeps it as a column. Passes. |
| `create` placing a child under its parent when asked (`nest`, Design 3.3, row 1) | model | "The child's id-path is the parent's followed by its own ID" is a string operation any store can perform, and starting it at the top instead is what every store does today. Passes. |
| `rename` taking an id-path, and refusing an item with nested items (row 7) | model | "Does any record's id-path start with this one followed by `/`?" is a prefix query any store can answer; the rename itself changes one record, as today. Passes. |
| `lookup` and `is item folder` at any depth (rows 8, 12) | model, unchanged in shape | Same operations, taking and returning id-paths. Passes. |
| `parent` in taxonomy and capability records (Design 3.1) | model | A reference held as a value, like any other (TCW-110 Design 5). Passes. |
| The disagreement check (Design 3.2) | model | Compares an id-path's prefix with a `parent` value; both are values any store has. Passes. |
| Length of a full identifier (Design 4.2) | model | A bound on a string. Passes. |
| State files, `resources/`, organising folders, reserved names, the walk, the bounded folder (Design 1, 2) | deployment | How a folder of files marks and bounds an object, which the TCW-99 design places in the deployment layer ("state files marking which folders are objects"). A store that is not a folder of files keeps an object's fields as a record and needs none of them. |

No backend operation is added or removed; the twelve change their argument
from a folder name to an id-path, and `create` gains its `nest` argument.

## Use cases

- **UC-1 (a single project).** No configuration is added. Files are renamed
  and gain one line (`tcw-version`). A child made with `--parent` alone is
  flat and typed as in 3.x, which keeps TCW-110's promise that a single
  project types no more than before. A child made with `--nest` (as the plan
  stage prompt does) sits in its parent's folder, so in a files-backend
  project it is typed by its id-path (`2026-10-22-epic/2026-10-22-part`) or
  found with `tcw work list --parent` (Non-goals). The walk replaces one folder listing with one per object
  folder, skipping stage folders, `comments/` and `resources/`; no command
  reads anything more than the folders it lists.
- **UC-2 and UC-7 (a library others read; a public library).** A reader's
  `parent:` may name a library's term or capability; it is checked as any
  reference (TCW-110 Design 6), and "could not check" where the library is
  absent (2.6 l). Nothing is written into the library.
- **UC-3 (a monorepo).** Each project's stores are walked alone; TCW-110's
  "stores never nest" (TCW-110 Design 7.4) means one store's walk never
  reaches another's objects. An epic in `app` whose parts live in `server`
  keeps them flat in `server`'s store, with `parent: app.work/…`, which 3.2
  does not warn about.
- **UC-4 (a planning workspace).** A store held in another repository is
  walked where it is. A planning item's parts in other projects are flat
  there, as in UC-3.
- **UC-5 (a shared Jira project).** Each project walks its own work store;
  `lookup` finds a key only among this project's folders, as today. A child
  whose parent belongs to another TCW project in the same Jira project is
  flat (3.3). The 255-character limit (4.2) is what keeps every project's
  `TCW Item` values writable.
- **UC-6 (a project not on this machine).** A `parent` naming it is "could not
  check" (2.6 l); nothing else here reads another project.
- **UC-8 (several families).** Not affected: nothing here finds projects.
- **S-3 (backends).** Both backends take id-paths (Design 5); the files
  backend checks the 3.2 rule offline, Jira under `--remote`, because the
  parent is a fact Jira owns.
- **S-4 (worktrees, clones).** Not affected: everything here is inside one
  store's folder.
- **S-7 (several people).** Two people giving a child the same title on the
  same day under the same parent collide as they do today at the top; the
  second `create` is refused (`tcw/work/fs_backend.py:303-305`). A rename in
  one clone and a nested create in another meet on merge: person A renames an
  epic that has no nested items yet (row 7 allows it), while person B creates
  a part under it with `--nest`. After the merge, the epic's old folder name
  holds only B's part, with no state file of its own. `tcw validate` reports
  the old folder as an item folder with no state file (2.6 h) and, in a
  files-backend project, the part's `parent` as naming no item (2.6 l, since
  A's rename rewrote only the references A's clone held). In Jira mode the
  part's ticket keeps its parent link, which Jira holds by key, and its
  `TCW Item` names the old path, which is where its folder still is; once
  the folder is moved, `tcw validate --remote` reports that `TCW Item` as
  naming another id-path until it is set. The part itself stays readable
  (2.5 step 4).
  Until TCW-114's move, the repair is by hand: move the part's folder into
  the renamed epic's folder, remove the empty old folder, set the part's
  `parent` with `tcw work edit` (files backend), set its `TCW Item` in Jira to
  the new full identifier (Jira), and run `tcw validate --remote` to confirm.
- **S-8 (partial failure).** A rename changes one item's folder and, in
  Jira, one ticket, as today (6.3); an item with nested items is refused
  before anything changes (row 7). A nested create that stops in Jira is
  finished by `tcw work tickets adopt` (6.4).
- **S-9 (upgrades).** A 3.x `meta.yaml` or `item.yaml` in a 4.0 store is
  recognised and names `tcw migrate` (2.6 f), never read, and never deleted
  by removing an object above it (2.5); a state file from a
  newer TCW is never rewritten (1.5). A 3.x TCW reading a 4.0 store finds no
  objects, which is not designed for (TCW-106 Use cases, S-9).
- **S-10 (things TCW does not own).** This item makes S-10's "treat an item
  folder as a bounded set of files" true and checked, for all three
  namespaces (2.6 a–b), and gives anything else a place (`resources/`).
- **S-11 (version control).** Nothing here reads or changes git; the example
  hook (9.4) is the project's, and is changed so it commits only the item's
  own files.

Checklist: 1 (where it looks) only inside the active project's stores, by the
walk; 2 (whose things) only the active project's records are written,
including by `rename`; 3 (reading across projects) only a `parent` reference
is resolved, by TCW-110's rules; 4 (backends) Design 5 and the litmus table;
5 (who is present) nothing asks a person; 6 (harness) the CLI carries every
rule, and the text that encourages nesting only passes `--nest`: the plan
stage prompt here, identical under every harness since `tcw work stage
prompt` prints it, and the skills in TCW-117 (9.3); 7 (stopping
halfway) S-8 above; 8 (single project) UC-1 above; 9 (older and newer TCW)
S-9 above; 10 (testing the setup claimed) criteria 1, 3, 9, 9a, 10, 12, 14
and 16 use the suite's Jira fake, criterion 15 two projects linked by
`parents:` (TCW-108).

## Acceptance criteria

Each criterion runs against fixtures built with the suite's 4.0 project
helper (TCW-106), in a project `demo` unless it says otherwise. "Prints"
means standard output; "warns" means a `tcw validate` finding of severity
`warning`.

1. **State files written.** `tcw taxonomy add Invoice` creates
   `docs/taxonomy/invoice/tcw-taxonomy.yaml`, whose first line is
   `tcw-version: <the number tcw --version prints>`, and `description.md`, and
   no `meta.yaml`. `tcw capabilities add cli/x` does the same with
   `docs/capabilities/cli/x/tcw-capability.yaml`. In a files-backend project
   `tcw work new 'Add login'` creates `<work>/<date>-add-login/tcw-work-item.yaml`
   with that first line and no `item.yaml`; with the Jira fake, the folder's
   `tcw-work-item.yaml` holds exactly the keys `tcw-version` and `ticket`, and
   so does the one `tcw work tickets adopt <KEY>` writes for an adopted
   ticket. The taxonomy and work state files hold no `id`; the capability's
   holds `id: cap-` followed by six hexadecimal digits, as today (1.3).
2. **Edits keep the version.** With the running version patched to `4.1.0`,
   a `tcw-capability.yaml` and a files-backend `tcw-work-item.yaml` whose first
   line is `tcw-version: 4.0.0` still have that first line after
   `tcw capabilities set cli/x --status Supported` and
   `tcw work edit <item> --priority high`.
3. **Version problems.** For each of TCW-106 Design 3.4's rows a–d written
   into `cli/x`'s `tcw-capability.yaml`: `tcw validate` exits 1 with an error
   naming that file and `tcw-version`; `tcw capabilities show cli/x` and
   `tcw capabilities set cli/x --status Supported` exit 1 and the file is
   byte-for-byte unchanged; `tcw capabilities list`, with a second capability
   `cli/w` beside it, exits 1, prints `demo.capabilities/cli/w` and not
   `cli/x`, names `cli/x`'s file on standard error, and its `--json` output
   holds the one record for `cli/w`. The same rows in a files-backend item's
   state file make `tcw work show <item>` and `tcw work list` exit 1 naming
   the file. With the Jira fake, a nested item's state file of row d with an
   extra key `added-in-4-1: x`: `tcw work show <KEY>` shows the item, and
   `tcw validate` reports the file as written by a newer TCW and does not
   report "must hold exactly".
4. **Only state files make objects.** A folder `docs/taxonomy/group/` holding
   no state file and a term `group/refund` with one: `tcw taxonomy list`
   prints `demo.taxonomy/group/refund` and not `demo.taxonomy/group`, and
   `tcw taxonomy show group` exits 4. The same layout in the capabilities and
   files-backend work stores (`docs/work/2026/<date>-x/`) lists
   `demo.capabilities/group/x` and `demo.work/2026/<date>-x`.
5. **Bounded object folders.** `tcw validate` exits 1 with one error each,
   with 2.6's message, for: `notes.md` in an item's folder (a);
   a folder `drafts/` with no state file in a term's folder (b); a folder
   `resources/` directly in the capabilities store root (c); a capability
   folder holding a 3.x `meta.yaml` and no state file (f); a
   `tcw-taxonomy.yaml` in the taxonomy store root (g); in a files-backend
   project, a folder `<date>-x` directly in the work store with no state file
   (h) and a folder `notes` holding a `tcw-work-item.yaml` (i). It passes with
   `resources/notes.md` and `resources/a/b.png` in the same item's and term's
   folders. It warns for `README.md` in the capabilities store root (d) and an
   empty organising folder `docs/work/empty/` (e). A leftover `config.yaml`
   at the taxonomy store's root is reported once, by today's check, and not
   again under d. A `resources/sample.yaml` in a term's folder that does not
   parse as YAML is not reported, and a capability beside it whose
   `appendedDocs` names a missing file is still reported (today's `missing
   attachment`), so the tree checks still ran; a `resources/old.md` that is not valid UTF-8 is a warning.
6. **Reserved names refused.** `tcw taxonomy add Resources` and
   `tcw capabilities add cli/resources` exit 2 and write nothing; in a files-backend
   project a hand-made organising folder `docs/work/review/` holding an item is
   an error in `tcw validate` naming `review`, and `docs/taxonomy/review/` with a
   state file is not.
6a. **A misplaced folder hides nothing.** In a files-backend project, an item
   `<date>-x` under that `docs/work/review/` folder, and an item
   `<date>-part` under a folder `drafts/` with no state file inside an epic's
   folder: `tcw work list` lists `demo.work/review/<date>-x` and
   `demo.work/<epic>/drafts/<date>-part`, and `tcw work show` of each id-path
   shows the item; `tcw validate` exits 1 reporting `review` (2.6 c) and
   `drafts` (2.6 b), and neither item.
7. **Attachments and composed bodies.** A term with `resources/diagram.png`
   and a loose `old.txt` in its folder: `tcw taxonomy show <term> --json` has
   `attachments: ["resources/diagram.png"]`, and `tcw validate` reports
   `old.txt` (2.6 a). A capability whose state file has
   `appendedDocs: [resources/camera.md]` shows that file's text at the end of
   its body; `appendedDocs: [camera.md]` with `camera.md` beside the state
   file is an error in `tcw validate` and is not in the body.
8. **`id:`.** An item's state file with `id: <its folder name>` passes
   `tcw validate`; with `id: other` it is an error naming `id`, and
   `tcw work show <folder>` still shows the item.
9. **Nesting a work item, files and Jira.** In a files-backend project,
   `tcw work new 'Flat' --parent <epic>` creates `<work>/<date>-flat/` at the
   top, as today. `tcw work new 'Part' --parent <epic> --nest` creates
   `<work>/<epic>/<date>-part/`, prints `demo.work/<epic>/<date>-part`, and
   `tcw work show`, `edit`, `comment`, `advance --dry-run` and `path` all
   accept that id-path and its full identifier; `tcw work list` lists all
   three items, and `tcw work list --parent <epic>` lists the two children.
   With the Jira fake, the same `--nest` command makes
   `<work>/<EPIC-KEY>-…/<KEY>-part/`, sets `TCW Item` to
   `demo.work/<EPIC-KEY>-…/<KEY>-part`, and `tcw work show <KEY>` shows it.
   `--nest` with a `--parent` naming an item of another project (TCW-110
   form a) creates the folder at the top, exits 0, and prints
   `not nested:` on standard error; `--nest` without `--parent` exits 2 and
   creates nothing.
9a. **Finishing a nested Jira create.** With the Jira fake set to fail the
   folder write after `TCW Item` is set, `tcw work new 'Part' --parent
   <EPIC-KEY> --nest` exits 1 naming `tcw work tickets adopt <KEY>`;
   running that command then makes `<work>/<EPIC-KEY>-…/<KEY>-part/` holding
   `tcw-work-item.yaml`. With the fake set to fail setting `TCW Item`
   instead, the adoption makes `<work>/<KEY>-part/` at the top.
10. **Jira at any depth.** With the Jira fake and two folders holding the
    state file and carrying the key `TCW-5`, one at the top and one nested,
    `tcw work show TCW-5` exits 1 naming both. `tcw validate --remote`
    compares a nested item's folder with its ticket, reporting a `TCW Item`
    that names another id-path. In the same Jira-mode store, an organising
    folder `2026/` holding an item passes `tcw validate` and the item is
    listed; a key-named folder `TCW-7-x/` with no state file is an error
    (2.6 h), `tcw work show TCW-7` exits 4, and a fresh `tcw work tickets
    adopt TCW-7` (its ticket naming no item, its summary giving other words)
    exits 3 naming `TCW-7-x`, makes no edit on the fake and creates no
    folder; a folder `notes/` holding a `tcw-work-item.yaml` is an error
    (2.6 i).
11. **Parents of terms and capabilities.** `tcw taxonomy add Refund --parent
    invoice` writes `docs/taxonomy/invoice/refund/tcw-taxonomy.yaml` holding
    `parent: demo.taxonomy/invoice`; `tcw taxonomy show invoice/refund --json`
    has `"parent": "demo.taxonomy/invoice"`, and a term with no parent has
    `"parent": null`. With capabilities `cli/x` and `cli/y`:
    `tcw capabilities add cli/w --parent cli/x` writes
    `parent: demo.capabilities/cli/x`, exits 0 and prints nothing on standard
    error (`cli/w` sits in the organising folder `cli/`, so it has no folder
    parent); `tcw capabilities add cli/x/z --parent cli/y` writes
    `parent: demo.capabilities/cli/y`, exits 0 and prints on standard error a
    warning containing `sits in the folder of demo.capabilities/cli/x` and
    `parent: decides`; `tcw capabilities set cli/w --parent ''` removes
    `parent` from `cli/w`'s state file. In a project that inherits the
    capability `core.capabilities/cli/v` from its parent project `core`,
    `tcw capabilities set core.capabilities/cli/v --parent cli/x --status
    Supported` exits 3 naming `core`, and no file changes in either project
    (3.4).
12. **Folder and parent disagree.** `tcw validate` warns, with 3.2's text and
    exit 0, for: a nested term whose state file has no `parent`; a
    files-backend item nested in `<epic>` whose `parent` is another item; and,
    with the Jira fake under `--remote` only, a nested Jira item whose
    ticket's parent is another ticket. It does not warn for an item at the
    top whose `parent` is `<epic>`, nor for one whose parent is in another
    project. `tcw work edit <part> --parent <other>` prints the same warning
    on standard error.
13. **Bad parents.** `tcw validate` reports an error for a capability whose
    `parent` is `demo.taxonomy/x` (wrong namespace), names itself, names a
    capability that does not exist, or forms a loop with another capability's
    `parent`.
14. **Length.** `tcw capabilities add` of an id-path whose full identifier
    would be 256 characters exits 2 naming 255 and writes nothing; one of 255
    succeeds. `tcw work new --parent <P> --nest` with a long title under a
    parent whose full identifier is 200 characters prints a full identifier
    of at most 255 characters (files and Jira fake). In the files backend,
    under a parent whose full identifier is 235 characters (exactly 8
    characters left for title words once `/` and the 11-character date
    prefix are counted), the item is created. With the Jira fake, under a
    parent of 227 characters (7 left once `/` and the 20-character allowance
    are counted), it exits 2 naming the parent and no ticket is created.
    Under a parent of 240 characters both backends exit 2 naming the parent. A project whose ID is 231 characters
    long: `tcw work new 'x'` (no parent) exits 2 naming the project ID.
    `tcw work rename <item> <words>` that would make the item's identifier
    256 characters exits 2 and moves nothing. With the Jira fake: under a
    parent leaving exactly 8 characters at the 20-character allowance, a
    fake answering with a 24-character key makes the item with title words
    cut to 3 characters, exits 0, and its `TCW Item` is at most 255
    characters; a fresh `tcw work tickets adopt <KEY>` in a project whose ID
    leaves fewer than 8 characters exits 2 and makes no edit on the fake; and
    a delegation (`tcw work new --project <other>`) into a project whose ID
    leaves fewer than 8 characters sets a `TCW Item` of at most 255
    characters. **`tcw validate` (2.6 n):** a capability folder made by hand
    whose full identifier is 256 characters, and in a files-backend project
    an item nested by hand whose full identifier is 256 characters, each give
    one error at its state file naming 255, exit 1, and are still listed by
    `tcw capabilities list` and `tcw work list`; at 255 characters neither is
    reported.
15. **A parent in another project is checked as a reference.** Two projects
    side by side in two git repositories, `app` naming `core` under
    `parents:` with `inherit: none` (TCW-108 Design 1.1): a term of `app`
    with `parent: core.taxonomy/payment` passes `tcw validate` when `core`
    has that term, fails it when it does not, and is reported as
    `unresolved` with exit 0 when `core`'s folder is removed (beside the
    one `unresolved` finding TCW-108 Design 6.5 a reports for `core`
    itself, which the criterion allows for; this is TCW-108's handoff to
    this item).
16. **Renaming, nested and not.** Files backend: an epic holding a nested
    part, and a third item whose `blocked-by` names the part.
    `tcw work rename <epic> new-words` exits 3 naming the part and TCW-114,
    and changes nothing. `tcw work rename <epic>/<part> new-words` renames
    the part inside the epic's folder: its identifier becomes
    `demo.work/<epic>/<date>-new-words`, the third item's state file names
    the new identifier, and standard error names the old and new
    identifier; a Markdown file under `resources/` that mentions
    `<epic>/<part>` is listed as still naming the old identifier, and one
    that mentions only another item `<other-epic>/<part>`, with the same last
    part, is not (7.2). Jira fake: the same nested-part rename updates that ticket's
    `TCW Item` to the new id-path; with the fake set to fail the folder move,
    the command exits 1 and `TCW Item` is set back.
16a. **A rename and a nested create meet on merge.** Files backend, built by
    hand as S-7 describes: the epic renamed to `<date>-new-words`, and the
    old folder `<date>-old-words/`, with no state file, holding only a part
    whose `parent` is `demo.work/<date>-old-words`. `tcw validate`
    exits 1 reporting the old folder (2.6 h) and the part's `parent` (2.6 l);
    `tcw work show <date>-old-words/<part>` shows the part. After moving the
    part's folder into `<date>-new-words/`, removing the old folder and
    `tcw work edit <date>-new-words/<part> --parent <date>-new-words`,
    `tcw validate` passes.
17. **3.x data in a 4.0 store** is never read: an item folder holding only
    `item.yaml` is not listed by `tcw work list` and is reported by
    `tcw validate` with `tcw migrate` (2.6 f); likewise a taxonomy folder with
    only `meta.yaml`.
17a. **Removal never deletes what it cannot see.** `tcw taxonomy rm
    invoice`, with a folder `invoice/old/` holding only a 3.x `meta.yaml`,
    exits 3 naming `invoice/old` and `tcw migrate`, and every file is still
    there; the same for `tcw capabilities rm cli/x` with `cli/x/.drafts/y/`
    holding a `tcw-capability.yaml` (today's message, `nested under it`),
    and with `cli/x/resources/sample/tcw-capability.yaml` (the message names
    that path). With none of these, both removals succeed.
18. **The web app.** `/api/work/<id-path, percent-encoded>` for a nested item
    returns its record, and its board lists it. A create request with a
    parent and no `nest` makes the item at the top; with `nest: true` it
    makes it inside the parent's folder. The create form's "inside the
    parent's folder" option is unticked by default and sends `nest: true`
    when ticked (the web client's unit tests).
19. **Shipped text.** `tcw work stage prompt plan <item>` contains
    `--parent <slug> --nest` and the sentence that the part's folder goes
    inside the parent's folder; `docs/lifecycle/abstraction.md` holds the 9.1
    bullet with `resources/` and the words "id-path" in its interface list;
    and `tcw/work/backend.py`'s docstring says "Twelve operations". (The
    skills' text is TCW-117's.)
20. **The commit hook.** Run as a `post` hook after moving an epic, in a git
    repository where a nested part has an untracked new file and a tracked
    file with uncommitted changes,
    `docs/guide/examples/commit-item-after-move.sh` commits the epic's own
    changed files and leaves both of the part's files uncommitted (`git
    status` still shows them), while a file the epic keeps at
    `resources/sample/tcw-work-item.yaml` is committed with the epic.
21. **The sweep.** After the change, a search for `meta.yaml`, `item.yaml`
    and `ITEM_FILE` under `tcw/`, `web/client/src/`, `scripts/` and `evals/`
    finds only the one module's 3.x names (1.1), which the 2.6 f recogniser
    and the checks before a removal (2.5) use, and those two's messages; a
    search for
    `iterdir()` applied to a store root finds only the walk. A reviewer checks
    the plan's list of sites against a fresh search.
22. The full suite, run as CI runs it (bare `pytest`, and the web client's
    unit tests), passes on `v4`.

### Coverage

| Design rule | Criteria |
| --- | --- |
| 1.1 state file names | 1, 4, 17 |
| 1.2 contents, Jira's exact keys, `KEYS` | 1, 3 (Jira), 8 |
| 1.3 `id:`; capabilities keep `cap-` until TCW-112 | 1 (no `id` in taxonomy and work; `id: cap-…` in the capability's), 8 |
| 1.4 writing the version, edits keep it; `adopt` writes it | 1, 2 |
| 1.5 reading the version, per store, Jira's version-first check | 3 |
| 2.1 fixed files per namespace | 5 |
| 2.2 `resources/`, attachments, composed bodies, exact spelling; `tcw validate`'s link check reads it, its YAML check skips it | 5, 7; exact spelling: the plan's case-insensitive-disk check |
| 2.3 organising folders in all three stores | 4, 5 (e), 10 (Jira) |
| 2.4 reserved names, per store | 5 (c), 6, 6a |
| 2.5 the walk, steps 1–5; one id-path by the same rule; the checks before a removal; 3.x override folders | 4 (steps 3, 5), 6a (step 4, and `show` of an id-path below a misplaced folder), 9 (nesting), 21 (one function); step 2's symbolic links: existing `tests/test_store_bounds.py` cases (`test_taxonomy_list_does_not_advertise_a_symlinked_entry`, `:186`; `test_capabilities_list_does_not_advertise_a_symlinked_entry`, `:224`), re-pointed at the walk by the plan; the checks before a removal: 17a; override folders: the existing override tests of `tcw capabilities set` and `list`, which keep passing on the state file (22) |
| 2.6 a–n | a, b, c, d, e, f, g: 5; b, c below a misplaced folder: 6a; d's skip of a leftover `config.yaml`: 5; h, i: 5 (files), 10 (Jira); h after a merge: 16a; j: 3; k: 8; l: 13, 15, 16a (work's warning); m: 12; n: 14 (`tcw validate`) |
| 3.1 `parent` in records | 11, 13 |
| 3.2 disagreement, offline and `--remote` | 11, 12 |
| 3.3 where a new child goes; `--nest`; the web option | 9, 11, 18 |
| 3.4 changing a parent never moves; `set --parent` refused on an inherited capability | 11, 12 |
| 4.1 id-path of a nested object; flat ones unchanged | 4, 9 |
| 4.2 the 255 limit, the parser's check, where it is enforced (add, new, adopt, delegation, rename, validate) | 14 |
| 4.3 title words that fit; real prefix for files, allowance for Jira; the project-ID message; nothing refused after the ticket exists | 14 |
| 5 rows 1–12 | 1 create: 9, 9a, 18; 2 read: 9, 6a; 3 list: 9, 6a; 4–6, 9, 10: 9; 7 rename: 16; 8 lookup: 9, 10; 11 current user: n/a, unchanged (`tcw/work/fs_backend.py:520-521`); 12 is item folder: 4, 6a, 9, 10, 17 |
| 6.1 Jira folders, organising folders, the state file now needed | 9, 10 |
| 6.2 `TCW Item` | 9, 14 |
| 6.3 renaming one ticket, nested or not | 16 |
| 6.4 finishing a nested create with `adopt`; key-named folders with no state file | 9a, 10 |
| 6.5 `--remote` at any depth | 10, 12 |
| 7.1–7.2 files backend; `report_mentions` searches the old id-path | 9, 16 |
| 8 the sweep | 21 |
| 9.1 `abstraction.md` | 19 |
| 9.2 docstring | 19 |
| 9.3 the plan stage prompt (the skills are TCW-117's) | 19 |
| 9.4 commit hook, both path lists, the folders its search skips | 20 |

## Risks

- **Size and test churn.** Every test fixture that writes `meta.yaml` or
  `item.yaml` (54 test files today) changes. As in TCW-106 and TCW-110, the
  plan gives the tests one helper that writes an object's state file, changes
  fixtures mechanically, and reads every failure rather than editing
  assertions to pass.
- **Files that become errors.** Loose files in object folders, valid in 3.x,
  are errors in 4.0 (2.6 a), including this repository's
  `docs/work/TCW-99-…/design.md`, which many requests and specs cite by path,
  and the practice of keeping a long design at an item folder's root. The
  design decided the bounded set; designs now go in `resources/`. TCW-116
  must move such files into `resources/` and report every link to their old
  path.
- **Taxonomy folders that stop being terms.** A 3.x taxonomy folder with no
  `meta.yaml` lists as a term today and is an organising folder in 4.0 (4.1).
  TCW-116 must give each one a state file or report it.
- **Nested terms that start warning.** Every 3.x nested term and nested
  capability has no `parent` and so warns under 3.2 once migrated, unless
  TCW-116 writes `parent:` for it.
- **Renaming an epic with nested parts waits for TCW-114.** Row 7 refuses
  it. Nesting is opt-in, so only epics whose parts were made with `--nest`
  are affected; the message says to wait for TCW-114, and a rename by hand
  (move the folder, fix the references, and in Jira the `TCW Item` values)
  stays possible, checked by `tcw validate --remote`.
- **Two items edit the same plan prompt paragraph.** TCW-111 (nesting) and
  TCW-114 (`-C` replacing `--project`) both change
  `tcw/work/prompts/plan.md` step 6; the combined difference is reviewed when
  both have landed.
- **Walking costs more than listing one folder.** Bounded by the number of
  object folders, since stage folders, `comments/` and `resources/` are never
  entered (2.5 step 3).
- **This repository's own records, read by v4's code.** Checked on
  2026-10-22 in the `v4` worktree. The `tcw` command on the path is the
  primary checkout's editable install of `main` (3.0.2). Its launcher script
  imports `main`'s code from any folder, the worktree's root included
  (`tcw --version` there prints 3.0.2), and it reads the 3.x
  `tcw-config.yaml` at the root and the `item.yaml` files that the `v4`
  branch still carries. So driving this repository's lifecycle with it keeps
  working after this item lands, from the primary checkout and from the
  worktree alike. What stops working is v4's own code run against this
  repository's records: the worktree's private environment
  (`.venv/bin/tcw`, which prints 4.0.0, and is the way the project guide
  gives for exercising a worktree's source), and any `python` started with
  the worktree's root as its current folder, which imports the worktree's
  `tcw/` first. Once this item lands, these find no item in `docs/work/`
  (every folder there holds `item.yaml`, row f), `tcw validate` reports every
  object folder, and `tcw serve` shows an empty board. This affects a
  contributor or agent who uses the worktree's environment for lifecycle
  commands, not the suite: no test runs `tcw` against this repository's own
  stores. Until TCW-116 migrates the repository, lifecycle commands use the
  `tcw` on the path, and the worktree's environment is used only for tests
  and fixtures. The breaking point that matters comes later: when `v4` is
  merged into `main`, the editable install runs 4.0 code on every machine
  that has it, so this repository must be migrated (TCW-116) in the same
  change, before any lifecycle command runs on the merged `main`.

Handoffs, which the dispatching session records on each ticket when this
spec is accepted:

- **TCW-110 (a note, no work):** TCW-111 adds the 255-character check to
  TCW-110's parser module (Design 4.2); TCW-110 builds nothing for it, and
  its Risks' handoff to TCW-111 is answered there.
- **TCW-112:** the capability's opaque `id` (`cap-…`) is dropped in 4.0 (the
  user's decision of 2026-10-22). Once overrides match by path, TCW-112 stops
  writing `id: cap-…` in `tcw capabilities add` and in the override folders
  `tcw capabilities set` creates, stops reading `Capability.id` as an
  identity, and turns on 2.6 k (an `id` must equal the folder's name) for
  capabilities. Also: `prependedDocs` and `appendedDocs` now name files in
  `resources/`, and the walk returns 3.x override folders, which the
  capability listers separate by `overrides:` until TCW-112 replaces them.
  And `tcw capabilities set --parent` is refused on an inherited capability
  until TCW-112 decides where an override's `parent` lives (3.4).
- **TCW-114:** delegation's 255-character fitting (4.2) goes with
  `tcw work new --project`. Renaming a work item that has items nested in it is refused
  until TCW-114 (Design 5, row 7); its rename must handle the nested items'
  identifiers, their references, and in Jira each nested ticket's
  `TCW Item`, with a rule for stopping halfway. Its move command places items
  in organising folders and moves a folder to agree with its `parent`,
  clearing 3.2's warning; it extends rename to terms and capabilities on the
  walk; it shares `tcw/work/prompts/plan.md` step 6 with this item.
- **TCW-116:** rename `meta.yaml` and `item.yaml` to the state files with
  `tcw-version`; write `parent:` for nested terms and capabilities; give each
  3.x taxonomy folder with no `meta.yaml` a state file or report it; move
  loose files in object folders into `resources/`, `prependedDocs` and
  `appendedDocs` files with them (rewriting those entries), and report links
  to the old paths; report any folder with a reserved name and any identifier
  over 255 characters; remove `id: cap-…` from capability state files, after
  TCW-112's overrides by path have replaced the pointers that use it. And
  this repository: until TCW-116 runs here, v4's own code finds none of this
  repository's items (Risks), so migrating this repository has to land with
  the merge of `v4` into `main`. Until a store is migrated, `tcw taxonomy rm`
  and `tcw capabilities rm` refuse to remove an object with a 3.x folder
  below it, naming `tcw migrate` (2.5).
- **TCW-117:** the guides and skills that name `meta.yaml` and `item.yaml`
  (Non-goals), and `docs/use-cases.md` S-10's wording, which now says "object
  folder". The skill text on nesting (Design 9.3): the `work` skill's "Epics
  are parents" bullet (`skills/work/SKILL.md:90-92`) and its command
  reference (`skills/work/references/commands.md:10`) always pass `--nest`
  with `--parent`; the `taxonomy` skill's nesting bullet
  (`skills/taxonomy/SKILL.md:91`) says `--parent` also records the parent;
  the `capabilities` skill documents `--parent` on `add` and `set`.
- **TCW-99 (the epic):** the user's decisions of 2026-10-22 recorded below
  (nesting opt-in with `--nest`, the narrowed disagreement warning, the
  opaque capability `id` dropped in 4.0), and the note in Risks that v4's own
  code cannot drive this repository's lifecycle until TCW-116.

## Notes

### Decisions made by the user on 2026-10-22

1. **The order the children land:** TCW-106, TCW-107, TCW-110, TCW-108, then
   this item. So parent links between projects (TCW-108) exist when this
   item is built, and the 3.x `projects:` key is gone. Nothing in this spec
   uses `projects:`; criterion 15 links its two projects with `parents:`.
   "Parent" in this spec always means an object's `parent:` field, never a
   parent project (the opening definitions).
2. **Nesting is opt-in (U1).** `tcw work new --parent` and the web app's
   create form keep a new child flat unless asked; `--nest`, and the form's
   matching option, put the child's folder inside its parent's (3.3). The
   plugin's skills and the plan stage prompt always pass `--nest`, which is
   the design's "encourage" (9.3): the prompt is this item's, the skills are
   TCW-117's. Taken with it, from the review's smaller version: renaming an
   item that has nested items is refused until TCW-114 (row 7). The review's
   reasoning holds: TCW-114 must build rename with reference rewriting for
   every namespace anyway, so building the work half here would build it
   twice; with nesting opt-in, epics with nested parts are rarer, so the
   cost of waiting is small; and it removes this spec's riskiest part, the
   multi-ticket Jira rename with setting back.
3. **The narrowed warning (U2), accepted.** The design says "Where the
   folder and `parent:` disagree, `parent:` decides and `tcw validate`
   warns". This spec narrows it: `tcw validate` warns only when an object
   sits inside another object's folder that is not its parent's, and a flat
   child never warns (3.2). The user accepted the narrowing, with nesting
   opt-in, knowing that most children will then be flat and unwarned.
4. **The capability's opaque `id` (U3).** It keeps its 3.x meaning until
   TCW-112, and is dropped in 4.0: once overrides match by path (TCW-112),
   the path is the identity, and `tcw migrate` (TCW-116) removes it. Then
   `id:` means the folder's name in all three namespaces, as the design says
   (1.3). This answers the question this spec had put to TCW-99.

### Decisions made when the plan review was answered (2026-10-22)

The plan review (round one of the plan) found five defects in this spec and
three more it had not listed; each is fixed above rather than settled in the
plan. The decisions taken with those fixes:

- **The user: TCW-111 stays one item, not split.** The review offered a split
  along four lines. The plan keeps those four parts in separate steps, each
  ending with the suite green and a commit: state files and the version; the
  walk and organising folders; nesting, the length limit and rename; parents
  for terms and capabilities.
- **Review decision 14, by the dispatching session: `resources/` in
  `tcw validate`.** The YAML well-formedness check skips `resources/`, and the
  `tcw://` link check keeps reading it (2.2). The other choice, checking
  both, would let one broken sample file switch off every taxonomy and
  capability check (`tcw/validate.py:310-317`, `:418-421`).
- **Review decision 16, by the dispatching session: removing an object with a
  3.x folder below it** that is not yet migrated is refused, naming
  `tcw migrate`; such a folder is never deleted without a word (2.5).
- **The checks before a removal are not listings** (2.5; the review's defect
  1): routing them through the walk would let `rm` delete objects the walk
  cannot see, which an existing test forbids.
- **A fresh adoption and a delegation keep within 255 characters** (4.2; the
  review's defect 2, and the same gap in delegation).
- **`tcw capabilities set --parent` is refused on an inherited capability**
  until TCW-112 (3.4; the review's defect 3): writing it into an override
  folder would make data TCW-112 has to migrate, and refusing can be undone
  later.
- **A work item's missing parent stays a warning** (2.6 l; the review's
  defect 5), and the difference from terms and capabilities is intended.
- **An object in a folder that holds no state file has no folder parent**
  (3.2; the review's gap b).
- **Row d skips a leftover store `config.yaml`** that another check already
  reports (the review's gap c).
- **Row n has a criterion** (AC 14's `tcw validate` part; the review's gap a).
- **Nothing is refused for length after a Jira ticket exists** (4.3): a
  refusal then would leave a ticket with no item.
- **Adopt still sees key-named folders with no state file** (6.4), so the
  change of 6.1 removes none of its refusals (the review's item 8; of its two
  options, deleting the "unfinished" branch would have lost the refusal of a
  moved-on ticket whose file is gone, so adopt keeps seeing those folders).

### Decisions the design left to this spec

1. **The bounded set per namespace** (2.1). The design lists the work item's
   fixed files "as today" without `capabilities.yaml`; "as today" includes
   it (`docs/lifecycle/abstraction.md:92-94`), so it stays. `description.md`
   is the tree stores' fixed body file.
2. **No organising folder inside an object's folder** (2.3). The design
   allows a folder without a state file "between objects" and lists an object
   folder's contents as fixed files, child objects' folders and `resources/`.
   Reading "between objects" as between the store root and objects keeps that
   list exact, so a stray folder inside an object (`drafts/`) is caught as
   2.6 b rather than accepted as organising. Objects below such a folder are
   still listed, read and accepted by every command (2.5 step 4, row 12), so
   the folder is reported without hiding anything.
3. **What counts as disagreeing** (3.2). Only an object that sits inside
   another object's folder can disagree with its `parent`. Sitting at the top
   says nothing about a parent, since organising folders are not objects; so
   a flat child, a child whose parent is in another project, and a migrated
   3.x child are not warned about. Warning on every flat child would flag all
   of this repository's TCW-99 children and every cross-project part, which
   cannot be nested at all. (Accepted by the user, above.)
4. **`--nest` never fails for want of a place** (3.3). A parent in another
   project cannot hold the child's folder; `--nest` then makes the folder at
   the top with a note, so a prompt or skill can always pass it. Changing a
   parent later never moves a folder (3.4), so the CLI never moves anything
   on its own.
5. **Reserved names per store** (2.4), so taxonomy terms named `review` or
   `plan` stay possible; compared ignoring case for disks that ignore it.
6. **255 characters for every full identifier** (4.2), answering TCW-110's
   handoff. Shortening a new item's title words keeps `tcw work new --nest`
   working under deep parents; the 8-character floor stops a folder name that
   would say nothing. Applying it to taxonomy and capabilities too keeps one
   rule for every identifier. No cap on project IDs is added: only an ID of
   more than 221 characters leaves no room for an item, and the message names
   the ID when it does (4.3).
7. **A state file with a version problem** (1.5): a work item in the files
   backend is unreadable, as any broken item is; a Jira item is still read,
   since nothing is taken from the file; a term or capability is left out of
   `list` with a message and an exit of 1, and never shown or written, so a
   newer file is never overwritten in an older format.
8. **`id:` is never written by TCW** in taxonomy and work (1.3): a copied
   folder with a stale `id:` would mislead; the folder's name is the ID.
9. **`parent` for terms and capabilities** (3.1), as the design says for all
   three namespaces; TCW reads it only for `show`, JSON and `tcw validate` in
   this item. `capabilities add --parent` does not move the folder, since its
   argument already gives the full path; `taxonomy add --parent` keeps
   today's nesting.
10. **The disagreement check for Jira runs under `--remote`** (3.2), since
    the parent is a fact Jira owns and the offline checks never read the
    network (`docs/lifecycle/abstraction.md`, "is item folder").

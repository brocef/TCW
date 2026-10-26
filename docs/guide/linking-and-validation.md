# Linking and validation

How TCW names each object it keeps, how one object's text points at another
with a `tcw://` link, and the single command that checks a whole project,
`tcw validate`.

## Full identifiers

Every object TCW keeps, a taxonomy entry, a capability or a work item, has one
name, its **full identifier**:

```
<project>.<namespace>/<id-path>
```

- `<project>` is the ID of the project that owns the object: lowercase letters
  and digits joined by single hyphens, such as `core` or `billing-api`. The
  IDs `t`, `c`, `w` and `local` are reserved and name no project.
- `<namespace>` is the store the object is in: `taxonomy`, `capabilities` or
  `work`.
- `<id-path>` is the path of the object's folder within that store, its
  folder names joined by `/`. Each folder name, an **id-part**, holds
  letters, digits, `-` and `_`, starts with a letter or a digit, and is at
  most 128 characters long. The id-path is matched exactly, letter case
  included, even on a disk that ignores case.

A full identifier is at most 255 characters long. Examples:
`core.taxonomy/invoice`, `core.capabilities/billing/refund`,
`app.work/2026-10-24-app-epic`, and a nested work item,
`app.work/2026-10-24-app-epic/2026-10-24-a-part`.

Neither a project ID nor an id-part may hold a `.`, so a name with a `.`
before its first `/` is a full identifier, and any other name is an id-path in
the project the command runs in. Every command prints full identifiers in its
output, whichever form it was given; the forms a command accepts as input
(a full identifier, its address, a tracker key, a bare id-path) are in
[the command-line guide](cli.md#naming-an-object).

## `tcw://` addresses

An **address** is a full identifier or a folder written after `tcw://`, so
that it can be the target of an ordinary Markdown link. There are two kinds.

### An object's address

```
tcw://<project>.<namespace>/<id-path>
```

names one object: `tcw://core.taxonomy/invoice` is the address of the
taxonomy entry `core.taxonomy/invoice`. An object's address never ends in
`/`.

### A folder's address

```
tcw://<project>.path/<folder>
tcw://<project>.<namespace>.path/<folder>
```

names a folder on disk instead of an object: a folder in the project's root,
or, with a namespace, a folder in one of its stores. `tcw://core.path/` is the
root of the project `core`, and `tcw://workspace.path/docs/app/work` is a
folder inside the project `workspace`. The `/` after `.path` is always
written. The folder path is made of folder names holding letters, digits,
`-`, `_`, `.` and `~`, with no empty part (`//`) and no part that is `.` or
`..`, which a web browser's address parser would drop. A folder address is
how a store kept in another project's folder is placed (`<namespace>.path` in
`.tcw/tcw-config.yaml`), and one of the ways to name the project a command
runs in, such as `tcw -C tcw://<id>.path/ validate`.

A folder address is about folders on this machine, as manifests and locating
a project are: they say where a project or a store sits here, and another
machine may place it elsewhere. Parent links, full identifiers, which project
owns an object, inheritance, overrides and `--scope` are what every store
keeps, whatever it is made of.

### The rules both kinds share

- Everything before the first `/` (the project ID, the namespace and `.path`)
  is lowercase.
- An address holds only letters, digits, `-`, `_`, `.`, `~` and `/`: no
  query (`?`), no fragment (`#`), no port, no user name and no
  percent-encoding (`%20` and the like).

### Linking one object to another

Any object's Markdown text, such as a taxonomy entry's or a capability's
`description.md` or a work item's documents, can point at another object with
a `tcw://` link:

```markdown
See [Validate a project](tcw://core.capabilities/cli/validate-a-project)
and the [reference](tcw://core.taxonomy/reference) term, or work item
[app.work/2026-10-24-app-epic](tcw://app.work/2026-10-24-app-epic).
```

These are ordinary inline Markdown links, so any Markdown viewer shows them as
links, and [the local web viewer](web-viewer.md) follows them inside the app.
They are additional to the structured references (a capability's `Subject`
and `Feature`, an object's `parent`, a work item's `blocked-by`), not a
replacement for them. TCW never rewrites stored Markdown.

**A link may name an object in any project TCW can locate**, not only the
project itself or one it inherits from: a parent, a child, or any other
project that a manifest lists, that a `TCW_PROJECT_<ID>` variable places, or
that a folder next to this project's root, or enclosing it, declares.
[Related projects](multi-repo.md) describes how TCW locates a project.

### Links written for TCW 3.x

A TCW 3.x link had the form `tcw://[<project-id>/]<axis>/<ref>`, with `T`,
`C` or `W` for the axis, such as `tcw://C/billing/refund` or
`tcw://core/T/invoice`. TCW 4.0 never follows one: `tcw validate` reports
each as an error that names `tcw migrate`, which rewrites a 3.x project's
links, with its other files, into 4.0 addresses. For a link written
`tcw://C/billing/pay`, it prints
`tcw://C/billing/pay is a TCW 3.x reference; TCW 4 writes tcw://<project>.<namespace>/<id-path> (run 'tcw migrate' in this project)`.

The [migration guide](../migration-guide-3.X-to-4.0.0.md) describes the move
from 3.x.

## `tcw validate`: one check of the whole project

`tcw validate` checks the project it is run in: its configuration and its
manifests, its parent and child links, its taxonomy, capabilities and work
stores wherever each lives (moved with `<namespace>.path`, or kept in another
repository with `<namespace>.repository`), and its work items.

```sh
tcw validate            # everything, without contacting anything
tcw validate --remote   # also check a Jira-mode project against Jira
```

**`tcw validate` never needs the network.** In Jira mode it checks the item
folders and their files, and nothing Jira holds, so the work-item checks that
need an item's properties wait for `--remote` (see
[What it checks](#what-it-checks) below). `tcw validate --remote` also reads
Jira, changing nothing there, as
[the Jira guide](jira.md#checking-the-workflow) describes; in a project whose
work is not kept in Jira, `--remote` is a usage error.

### What it prints

It prints one **finding** per line on standard output,
`<severity>: <where>: <message>`, and nothing when the project is clean.
`<where>` is a file or folder, relative to the project when it is inside it.
Each finding has one of three severities:

- **`error`**: something is wrong and must be fixed;
- **`warning`**: something is probably wrong, or will become a problem;
- **`unresolved`**: TCW could not check it, because what it would need to
  read is not on this machine, such as a parent project that was never
  cloned. It is neither a warning nor an error, so a check run in continuous
  integration on one repository passes without the others.

A count of each closes the run, on standard error, such as
`1 error, 2 warnings, 0 unresolved`. What is said about the run rather than
found in it also goes to standard error: a check that was skipped and why,
and, before the findings, each related project that a `TCW_PROJECT_<ID>`
variable places, in the form
`connected project '<id>' is overridden by TCW_PROJECT_<ID> to <folder>`.

`tcw validate` exits with code 1 when there is any error, and 0 otherwise;
with `--remote`, 5 when Jira could not be reached. Run in a folder that holds
no project, it exits 1, saying there is no TCW project here and naming
`tcw project new --id <id>`; run in a TCW 3.x project, it exits 1 with
`<folder> is a TCW 3.x project (tcw-config.yaml at its root, no .tcw/ folder); run 'tcw migrate' in it to move it to TCW 4`.
The other codes are in [the command-line guide](cli.md#exit-codes).

A problem in the project's own parent or child links, such as a loop, means
there is no order in which to read the projects it inherits from, so the run
stops after the configuration findings and that problem.

### What it checks

- **Configuration.** Every problem in `.tcw/tcw-config.yaml` and in personal
  configuration, each named by its key. A personal file that git tracks,
  `.tcw/tcw-config.local.yaml` (your configuration for this project, on this
  machine) or `.tcw/tcw-manifest.local.yaml`, is a **warning**: it is meant to
  stay out of version control.
- **Manifests.** Every entry of `.tcw/tcw-manifest.yaml` and
  `.tcw/tcw-manifest.local.yaml`, whether or not anything names that project:
  an entry whose folder is not on this machine is **unresolved**, and one
  whose folder is not a TCW 4 project, or declares another ID, is an error.
- **Parent and child links.** A loop, a listed child that does not name this
  project among its parents, a related project that is not on this machine
  (**unresolved**), and the warning when no load order keeps every project's
  own order of parents. [Related projects](multi-repo.md) describes the links
  and the load order.
- **Store locations.** A store path that is absolute or starts with `~`, and
  stores that lie inside one another, share a folder, or whose folder
  addresses loop.
- **YAML files** in the stores load cleanly, duplicate keys included.
- **Records of the wrong shape**: see below.
- **The shape of each store**: each object's folder holds only its own files
  (its **state file**, the YAML file that holds its fields and marks the
  folder as an object: `tcw-taxonomy.yaml`, `tcw-capability.yaml` or
  `tcw-work-item.yaml`, and a `description.md` or a work item's
  `capabilities.yaml`), its child objects, a work item's stage and comment
  folders, and its `resources/` folder for anything else; see the table
  below.
- **`tcw://` links** in every Markdown file of the stores resolve, including
  the Markdown in an object's `resources/` folder. Links inside code spans and
  fenced code are ignored, so documents that teach the scheme do not fail
  themselves. An object's address is checked in its owner's own store; a
  folder address is checked for its form and that its project can be
  located, not that the folder exists. A link into a project that is not on
  this machine is **unresolved**.
- **Taxonomy and capabilities**: each of the project's own objects as the
  project sees it, combined with what it inherits; the references between
  records, `parent` included; and overrides, as
  [the taxonomy and capabilities guide](taxonomy-and-capabilities.md)
  describes them. Inherited content that cannot be read is **unresolved**,
  and the checks that need it are left out.
- **Work items.** With the filesystem backend, plain `tcw validate` runs every
  check below. In a Jira-mode project the stage, parent and blocking items are
  kept in Jira, so plain `tcw validate` checks only each item folder's name and
  its `tcw-work-item.yaml`, a ticket key used by two folders, a record folder
  for a stage Jira keeps, the latest `review` round, and each folder's
  `capabilities.yaml` file's form: one that cannot be read or is malformed is
  an error, whatever the item's stage. The `parent` and `blocked-by` and
  stage-ahead checks, and the check of the records a `capabilities.yaml`
  declares, run only under `tcw validate --remote`, which reads each item's
  properties from Jira.
    - a `tcw-work-item.yaml` that cannot be read is an **error**;
    - a `parent` or `blocked-by` naming an item that does not exist is a
      **warning**;
    - an item whose stage is ahead of its documents, such as an item at
      `implement` with nothing from `spec`, is a **warning** until the item is
      finished;
    - a reference into a project that is not on this machine is
      **unresolved**;
    - the latest `review` or `qa` round with no usable `verdict` and `judges` is
      a **warning**, because `tcw work advance` refuses past that stage until it
      has them.
- **Each unfinished item's `capabilities.yaml`**, the records it declares it
  changes, each named by its full identifier. While the item is being worked,
  only what cannot be right at any point is reported: a file that cannot be
  read or is malformed, an unknown key, an entry that is not a full
  identifier, an entry naming a project TCW cannot locate, and an entry that
  could not be checked because its project is not on this machine, which here
  is an error rather than unresolved. A change not
  made yet is not reported; the records gate, the check TCW itself runs before
  an item moves into the stage after `implement`
  ([the work guide](work.md#built-in-gates)), checks those then.

### The findings of a TCW 4 project

Each finding below is quoted as `tcw validate` prints it after
`<severity>: <where>: `, with a name in angle brackets, such as `<id>` or
`<folder>`, in place of what a real run prints there, and `<…>` for a long
path.

| What is found                                                                                         | Severity     | The message                                                                                                                                                                                                                                                                                                                                                                       |
| ----------------------------------------------------------------------------------------------------- | ------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| A file in an object's folder that is not one of its own files                                         | `error`      | `is not one of <full identifier>'s files; move it into resources/`                                                                                                                                                                                                                                                                                                                |
| A folder in an object's folder that is not a child object (it has no state file) and not `resources/` | `error`      | `is not a child object of <full identifier>: it has no <state file>; give it one, or move it into resources/`                                                                                                                                                                                                                                                                     |
| A folder with a reserved name outside its own place, such as `resources` at a store's root            | `error`      | `'resources' is reserved in the taxonomy store`                                                                                                                                                                                                                                                                                                                                   |
| A file directly in a store's root or in a folder that only groups objects                             | `warning`    | `is not part of any object`                                                                                                                                                                                                                                                                                                                                                       |
| A folder that groups objects with no object anywhere below it                                         | `warning`    | `holds no TCW object`                                                                                                                                                                                                                                                                                                                                                             |
| A folder holding a 3.x `meta.yaml` or `item.yaml` and no state file, which `tcw migrate` converts     | `error`      | `holds a TCW 3.x meta.yaml; run 'tcw migrate' in this project`                                                                                                                                                                                                                                                                                                                    |
| A state file in a store's root                                                                        | `error`      | `the store's root is not an object; move this file into an object's folder`                                                                                                                                                                                                                                                                                                       |
| A work item folder, named as the backend names items, with no state file                              | `error`      | `is missing; it holds the item's properties and stage` (in Jira mode, `is missing; it holds the ticket's link`)                                                                                                                                                                                                                                                                   |
| A folder holding a work item's state file whose name breaks the backend's rule                        | `error`      | `is not an item folder: its name must be a date, then title words`                                                                                                                                                                                                                                                                                                                |
| A state file with no `tcw-version`, which 3.x never wrote under a 4.0 name, so `tcw migrate` is not named | `error`      | `has no tcw-version: add 'tcw-version: 4.0.0' as its first line`                                                                                                                                                                                                                                                                                                                  |
| A state file written by a newer TCW; none of its other checks run                                     | `error`      | `was written by TCW 9.0 (tcw-version 9.0.0), newer than this TCW (4.0.0); upgrade TCW`                                                                                                                                                                                                                                                                                            |
| An `id` that differs from the object's folder name                                                    | `error`      | `id '<id>' is not its folder's name, '<folder>'; an object's ID is its folder's name, so remove id or set it to '<folder>'`                                                                                                                                                                                                                                                       |
| A term's or capability's `parent` that names nothing                                                  | `error`      | `dangling parent ref '<full identifier>'`                                                                                                                                                                                                                                                                                                                                         |
| ... that names an object of another namespace                                                         | `error`      | `parent '<project>.taxonomy/<id-path>' names a term; this command takes a capability (capabilities namespace)`                                                                                                                                                                                                                                                                    |
| ... that names the object itself                                                                      | `error`      | `parent names the object itself`                                                                                                                                                                                                                                                                                                                                                  |
| ... that makes a loop, reported at each object in it                                                  | `error`      | `parent forms a loop: <full identifier> -> <full identifier> -> <full identifier>`                                                                                                                                                                                                                                                                                                |
| ... written as a bare 3.x path, which `tcw migrate` rewrites                                          | `error`      | `parent '<id-path>' is a TCW 3.x reference; TCW 4 writes <project>.capabilities/<id-path> (run 'tcw migrate' in this project)`                                                                                                                                                                                                                                                    |
| ... in a project that is not on this machine                                                          | `unresolved` | `parent ref '<full identifier>' could not be checked: project '<id>' is not on this machine: <…>`                                                                                                                                                                                                                                                                                 |
| An object nested in the folder of an object that is not its `parent`                                  | `warning`    | `<full identifier> sits in the folder of <full identifier>, but its parent is <full identifier, or not set>; parent: decides (set it to <full identifier>, or move the folder)`                                                                                                                                                                                                   |
| An object whose full identifier is longer than 255 characters, such as one placed by hand             | `error`      | `<full identifier> is 317 characters; a full identifier is at most 255`                                                                                                                                                                                                                                                                                                           |
| An object of the project's own that overrides nothing and is not complete                             | `error`      | `<full identifier> is incomplete: it overrides nothing, and has no name or description.md; if it overrode an object that moved or was removed, complete it or remove it`                                                                                                                                                                                                          |
| Two projects, neither inheriting from the other, with an object at one path                           | `warning`    | `taxonomy <id-path>: '<first>' and '<second>' each have an object at this path, and neither inherits it from the other; '<project>' uses the one from '<second>', which comes later in its load order, and nothing from '<first>''s; to choose for yourself, give '<project>' a complete object of its own at <id-path> (a name and a description), holding every field you want` |
| An `overrides` key in a state file, the 3.x override pointer that `tcw migrate` converts              | `error`      | `'overrides' was removed in TCW 4.0: an override is an object at the same path as the object it overrides; run 'tcw migrate' in this project, or move this folder to that path and delete the key`                                                                                                                                                                                |
| An axis's 3.x inheritance list left in `.tcw/tcw-config.yaml`, which `tcw migrate` converts           | `error`      | `… was removed in TCW 4.0: a project inherits its taxonomy from its parents; name each project it inherits from under 'parents:' with an 'inherit' that includes taxonomy, and delete this key`                                                                                                                                                                                   |
| A store that lies inside another store                                                                | `error`      | `the capabilities store of project '<id>' (<…>) lies inside the work store of project '<id>' (<…>); stores never nest or share a folder`                                                                                                                                                                                                                                          |
| Two stores in one folder                                                                              | `error`      | `the taxonomy store of project '<id>' (<…>) is the same folder as the work store of project '<id>' (<…>); stores never nest or share a folder`                                                                                                                                                                                                                                    |
| Store locations whose folder addresses loop                                                           | `error`      | `taxonomy.path: store locations loop: <id> taxonomy -> <id> taxonomy -> <id> taxonomy`                                                                                                                                                                                                                                                                                            |
| A store path that is absolute or starts with `~` in `.tcw/tcw-config.yaml`                            | `error`      | `taxonomy.path: must be a path relative to the project, or a tcw:// .path address such as tcw://<project>.path/<folder>; a folder that sits elsewhere on this machine is placed by an entry in .tcw/tcw-manifest.local.yaml`                                                                                                                                                      |
| A manifest entry whose folder is not on this machine (missing, or empty)                              | `unresolved` | `project '<id>' is not on this machine: <manifest> places it at <folder>`, followed, when the entry names a repository, by `, from <repository>; fetch it with 'tcw project provision <id>'`                                                                                                                                                                                      |
| A manifest entry whose folder declares another ID                                                     | `error`      | `entry for '<id>' in <manifest> places it at <folder>, which declares '<other>', not '<id>'`                                                                                                                                                                                                                                                                                      |
| A manifest entry whose folder is not a TCW project                                                    | `error`      | `entry for '<id>' in <manifest> places it at <folder>, which is not a TCW project: it holds files and no .tcw/tcw-config.yaml`                                                                                                                                                                                                                                                    |
| A manifest entry whose folder holds a 3.x project                                                     | `error`      | `entry for '<id>' in <manifest> places it at <folder>, which is a TCW 3.x project (tcw-config.yaml at its root, no .tcw/ folder); run 'tcw migrate' in it to move it to TCW 4`                                                                                                                                                                                                    |
| A parent that is not on this machine                                                                  | `unresolved` | `project '<id>' is not on this machine: <where TCW looked>; could not check what it passes down to '<project>' or the projects above it`, then `; could not check the taxonomy inherited from it`, and the same for capabilities and configuration where it passes them                                                                                                           |
| A listed child that is not on this machine                                                            | `unresolved` | `project '<id>' is not on this machine: <where TCW looked>; could not check that it names '<project>' as a parent`                                                                                                                                                                                                                                                                |
| A parent whose own parent links cannot be read                                                        | `unresolved` | `could not check what '<id>' passes down to '<project>': <the problem>`                                                                                                                                                                                                                                                                                                           |
| A loop in parent links                                                                                | `error`      | `loop in parents: <id> -> <id> -> <id>`                                                                                                                                                                                                                                                                                                                                           |
| A listed child that does not name the project among its parents                                       | `error`      | `'<child>' is listed as a child of '<project>' but does not name '<project>' among its parents`                                                                                                                                                                                                                                                                                   |
| No load order keeps every project's own order of parents                                              | `warning`    | `load order: no order keeps every project's own order of parents (at '<project>': '<id>', '<id>' cannot be placed); using depth-first order <id>, <id>, …, <project>; to choose a value yourself, set it in '<project>'`                                                                                                                                                          |
| A 3.x configuration file left at the root of a TCW 4 project                                          | `warning`    | `a TCW 3.x configuration file at the root of a TCW 4 project; TCW 4 reads .tcw/tcw-config.yaml only, so delete this one`                                                                                                                                                                                                                                                          |
| A `tcw migrate` that stopped, its progress record still in `.tcw/` (the root-file warning is then left out) | `error`      | `an unfinished 'tcw migrate': run 'tcw migrate' again in this project to finish it`                                                                                                                                                                                                                                                                                               |

A finding about a link prints the address and then the reason, such as
`tcw://core.taxonomy/nothing → no taxonomy entry core.taxonomy/nothing`, or
`tcw://gone.taxonomy/x → project 'gone' is not on this machine: <…>` for a
link into a project that is not on this machine. A link whose form is wrong
says so after the address, such as
`tcw://demo.path/../x is not a tcw:// address: a folder path has no '.' or '..' part, which a URL parser would drop`.

### A record of the wrong shape

A YAML file TCW writes as a record, an object's state file
(`tcw-taxonomy.yaml`, `tcw-capability.yaml` or `tcw-work-item.yaml`), has to
be a mapping (a set of `key: value` lines). One that is not is reported by
name:

```
error: docs/capabilities/billing/invoices/tcw-capability.yaml: expected a mapping, found list
```

A work item's `tcw-work-item.yaml` that is not a mapping is reported as
unreadable, and standard error says that the references in it were not
checked.

Any _other_ YAML under the scanned trees may be any shape at all: a work item's
`capabilities.yaml`, or a file in an object's `resources/` folder, is not held
to this rule, and a YAML file in `resources/` is not read at all.

### A leftover inheritance file from before 2.5.0

Before TCW 2.5.0 a project listed the projects it inherits from in a file
inside the tree: `config.yaml` at the root of the taxonomy, `.config.yaml` at
the root of the capabilities ledger. TCW does not read that file: a project
inherits taxonomy and capabilities from its parents, listed under `parents:`
in `.tcw/tcw-config.yaml`. `tcw validate` reports the old file wherever the
tree lives, once per tree, as an error whose message names TCW 2.5.0 and ends
`a project inherits taxonomy and capabilities from its parents (parents: in .tcw/tcw-config.yaml); delete this file`.

The fix is to name under `parents:` any project the file listed that you
still inherit from, and delete the file. The report stays until the file is
gone, even if you already copied the list. TCW never edits or deletes it.

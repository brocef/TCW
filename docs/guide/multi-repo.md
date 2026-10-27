# Related projects

Several TCW projects can work together: a planning workspace and the
applications it plans, a shared library and the products built on it,
packages side by side in one repository. This guide explains how projects are
related to each other, how TCW finds a related project's folder on your
machine, what happens when one is not there, how a command reaches another
project, how a store can live in another repository, and how
`tcw project provision` fetches what is missing.

Two kinds of fact are described here, and they behave differently.
**Manifests, finding a project's folder, `.path` addresses, provisioning and
git worktrees are about folders on this machine**: they say where things sit
on one computer, and can differ from one computer to the next. **Parent links,
full identifiers, ownership, inheritance, overrides and `--scope` are what
every store keeps**, whatever holds it: they are the same on every machine,
and a store that is not a folder of files would keep them too.

Every key named here is listed once, with its exact rules, in the `configure`
skill's [`projects.md`](../../skills/configure/references/projects.md) and
[`stores.md`](../../skills/configure/references/stores.md). See also
[the work guide](work.md),
[Taxonomy and Capabilities](taxonomy-and-capabilities.md),
[the configuration guide](configuration.md) and
[the command line guide](cli.md).

## A project and the active project

A **project** is a folder holding `.tcw/tcw-config.yaml`. That file gives the
project its **ID**, written once by `tcw project new --id <id>`: lower-case
letters and digits joined by `-`, such as `workspace` or `app`. Everything
that refers to a project uses its ID, such as a full identifier
(`app.work/2026-10-15-refund`, the name of an object that says which project
owns it; the [linking guide](linking-and-validation.md) gives every form) or
a parent link. A folder path only says where a project is on one machine.

The **active project** is the one a command runs as: the nearest folder
holding `.tcw/tcw-config.yaml`, starting from the current folder and going up
through the folders enclosing it. `tcw -C <folder>`, written before the
command, makes another folder the starting point (below, under "Changing
another project's objects").

## Parents and children

### Parent links: `parents:`

A project names the projects it builds on as its **parents**, under
`parents:` in its `.tcw/tcw-config.yaml`, in order. Each parent is an ID, or
a mapping with `id` and `inherit`:

```yaml
# app/.tcw/tcw-config.yaml
tcw-version: 4.0.0
id: app
parents:
    - workspace
    - id: core
      inherit: [taxonomy, capabilities]
```

`inherit` says what that parent passes down: `all` (the default when it is
left out), `none`, or a list drawn from `taxonomy`, `capabilities` and
`config`. A parent's own parents pass down too, through every level, without
being listed again; an ancestor is a parent, a parent's parent, and so on.
What each axis passes is described where it is used:
[Taxonomy and Capabilities](taxonomy-and-capabilities.md) for the taxonomy
and capability entries a project inherits and overrides, and
[the configuration guide](configuration.md) for `config`, which passes
`work.tags` and `work.jira` but never `work.backend`. A parent with
`inherit: none` passes nothing, and is still part of the project's family,
for example a planning workspace whose items the project's items name as
their parents.

A parent never has to name its children. A shared library that other
projects read is named as a parent by each of them, and its own files say
nothing about them. No command changes the list: edit the file, then run
`tcw validate`.

### Children: `children:`

A project may also list its **children**, the projects that name it as a
parent, under `children:`, so that commands run in it can reach them (for
`--scope down`, below). They are listed by ID in the shared
`.tcw/tcw-config.yaml`, in the personal `.tcw/tcw-config.local.yaml` (one
person's own list, never committed; `tcw project new` writes a
`.tcw/.gitignore` that leaves it out), or in both, and the two lists are
combined:

```yaml
# workspace/.tcw/tcw-config.yaml
tcw-version: 4.0.0
id: workspace
children:
    - app
    - core
```

```yaml
# workspace/.tcw/tcw-config.local.yaml
tcw-version: 4.0.0
children:
    - stray
```

`tcw project info` marks a child from the personal file `(personal)`. The
user-wide settings file (`~/.config/tcw/config.yaml`) cannot list children,
since it applies to every project.

**A listed child must name the parent back.** A child that does not is an
error, reported by `tcw validate` and by every command that reads the family
(exit code 1):

```text
error: .tcw/tcw-config.yaml: 'stray' is listed as a child of 'workspace' but does not name 'workspace' among its parents
```

The message names `.tcw/tcw-config.yaml` even when the child is listed in the
personal file.

`tcw project list` prints the active project's ID and then each related
project's, one per line; `--json` adds each one's relation, whether it is on
this machine, its folder and how TCW found it.

## The load order

Where several of a project's ancestors have something at the same place, such
as a taxonomy term at one path or a setting under one key, TCW reads them in
one order, the **load order**, and a later project wins over an earlier one.
The project itself comes last, so its own value always wins. The order follows
three rules:

- **The last listed parent wins.** In the `app` example above, `core` is
  listed after `workspace`, so `core` comes later and wins where both have
  something.
- **An ancestor comes before its child**, so a parent always comes after its
  own parents.
- **A project reached twice is loaded once.** When `core` also names
  `workspace` as a parent, `workspace` is still in the order once.

`tcw project info` shows the order:

```text
id: app
path: /home/me/src/app
parents:
  workspace (inherit: all)
  core (inherit: taxonomy, capabilities)
children: none
load order: workspace, core, app
```

Sometimes no order keeps every project's own order of parents, for example
when `a` lists `x` before `y`, `b` lists `y` before `x`, and `top` lists both
`a` and `b`. TCW then uses the order it reaches projects in when it follows
each parent in turn as far up as it goes, and warns. `tcw project info` shows
the warning on a line of its own, and `tcw validate` reports it:

```text
warning: .tcw/tcw-config.yaml: load order: no order keeps every project's own order of parents (at 'top': 'x', 'y' cannot be placed); using depth-first order x, y, a, b, top; the order of each project's parents: list sets the load order, and listing the parents of 'b' as x, y instead gives an order that keeps every other project's own order; to choose a configuration value yourself, set the value in 'top' itself, which loads last and wins
```

A loop in parent links, a project that is its own ancestor, is an error that
every command reading the family reports (exit code 1), such as
`loop in parents: workspace -> app -> workspace`.

## Where a related project is on this machine

This section is about folders on this machine. A parent link names a project
by its ID only; TCW then has to find that project's folder here.

### Manifests

A **manifest** says where other projects are on this machine. Each project can
have two:

- `.tcw/tcw-manifest.yaml`, shared and committed, read on every machine; a
  path in it is relative to the project's folder;
- `.tcw/tcw-manifest.local.yaml`, personal to this machine and never
  committed (the `.tcw/.gitignore` that `tcw project new` writes leaves it
  out); a path in it may also be absolute or start with `~`.

```yaml
# app/.tcw/tcw-manifest.yaml
tcw-version: 4.0.0
projects:
    shared: packages/shared
    core:
        path: ../core
        repository: https://example.com/acme/core.git#release
    server:
        path: ../platform/apps/server
        repository: git@example.com:acme/platform.git
        subfolder: apps/server
```

Each entry maps a project ID to the folder holding that project's `.tcw/`:

- `path`, the folder, written alone or as a key;
- `repository`, optional, the address `tcw project provision` clones the
  project from, written `<address>` or `<address>#<branch>`;
- `subfolder`, optional and only with `repository`, where the project sits
  inside its repository. It must be how `path` ends: in the `server` entry,
  the repository is cloned into `../platform`, and the project is at
  `../platform/apps/server`.

A manifest says where a project is, and nothing else: listing a project in a
manifest does not relate it to this one. The relation is the parent link or
the child entry. A manifest with any problem, such as a missing
`tcw-version` line or an absolute path in the shared file, is not used at
all, and `tcw validate` names the problem:

```text
error: .tcw/tcw-manifest.yaml: projects.inner: path '/abs/inner' must be relative to this project's root: this file is shared by every machine; an absolute path or one starting with '~' goes in .tcw/tcw-manifest.local.yaml
```

### How TCW looks for a project

TCW looks a project up from the project whose file names it, and takes the
first answer of these:

1. **`TCW_PROJECT_<ID>`**, an environment variable naming the project's
   folder on this machine: the ID in capitals, with `-` written `_`, such as
   `TCW_PROJECT_SHARED_CORE` for `shared-core`. A variable naming a folder
   that does not exist is ignored; one naming a folder that holds a different
   project is refused. A relative value is read from the current folder.
2. **A manifest entry**: the naming project's personal manifest, then its
   shared one, then the manifests of its ancestors that TCW has read, in the
   reverse of its load order, then those of the projects below it. **The
   entry decides**, whatever is on disk: when the folder it gives is empty,
   or holds only `.git` (what a clone that stopped leaves behind), the
   project counts as not on this machine, and TCW does not go on looking
   elsewhere.
3. **A search, with no entry:** the folders next to the naming project's
   folder, then each folder enclosing it, up to the top of the disk. The
   search never looks inside a folder it tests, so a project below another
   one, such as a package inside a repository, is found from the package
   (looking up) but not from the repository's top project (looking down):
   the top project needs a manifest entry for each package it lists as a
   child. On macOS, the search does not test the Desktop, Documents and
   Downloads folders of the home folder as folders next to a project.

When the search finds two folders declaring the same ID, the lookup is an
error naming both, and an entry decides between them:

```text
project 'core' is declared by more than one folder near this one: /home/me/src/core and /home/me/src/core-copy; add an entry for 'core' to .tcw/tcw-manifest.local.yaml (this machine) or .tcw/tcw-manifest.yaml (everyone)
```

An entry in an ancestor's manifest must also agree with what the search from
the naming project finds; when the two disagree, the lookup is an error
saying which folder each gives, and an entry in the naming project's own
personal manifest settles it.

`tcw project path <id>` prints the folder TCW found for a project, and
`tcw project list --json` says, for each related project, whether it was
found by a manifest (and which one), by `TCW_PROJECT_<ID>`, or by the search.

## A related project not on this machine

A related project may be named and simply not be here: a fresh clone, or a
machine that has only some of the repositories. A parent kept in another
repository is the common case. What still works depends on what the command
needs:

- **Everything that needs only the active project works.** For a project with
  the filesystem backend (work items kept as files), listing, creating,
  editing and moving its own work items all work without the missing parent.
- **A listing of the active project's own taxonomy or capabilities**, under
  the default scope, shows only the project's own entries, warns, and exits 0:

    ```text
    warning: 'app' inherits its taxonomy from project 'workspace', which is not on this machine: …; showing only 'app''s own declarations
    ```

- **A command that needs what the missing project passes down exits 7**: a
  taxonomy or capabilities command with `--scope up`, which shows what the
  project inherits, and a command that needs a setting the project inherits
  through `config`. The commands that read or register tags
  (`tcw work tags list`, `tcw work tags add`, `tcw work tags rm`, and
  `--tag` on `tcw work new` and `tcw work edit`) exit 7 when a parent that passes `config` is missing,
  since that parent may hold `work.tags`:

    ```text
    tcw work tags list: 'app' inherits its configuration (work.tags) from project 'workspace', which is not on this machine: /home/me/src/app/.tcw/tcw-manifest.yaml places it at /home/me/src/workspace, from https://example.com/acme/workspace.git; fetch it with 'tcw project provision workspace'
    ```

    In a project that keeps its work items in Jira, whose Jira settings could
    come from a missing parent, `tcw work list` exits 7 too;
    [the Jira guide](jira.md) says more.

- **A command that names the missing project itself exits 5**: reading one of
  its objects by full identifier, `tcw project path <id>`, and
  a command run with `tcw -C tcw://<id>.path/`.
- **`tcw validate`** reports what it could not check as **unresolved**, which
  is neither a warning nor an error, keeps checking everything else, and
  exits 0. It says what the missing project's absence leaves unchecked, such
  as `could not check what it passes down to 'app' or the projects above it`,
  and, for an item whose parent or blocker is in that project,
  `parent workspace.work/2026-10-15-plan-billing is in a project that cannot be reached from here`.
- **A family view** (below) leaves out any other covered project that cannot
  be read, such as a listed child that is not here, or a missing ancestor in
  a work listing, prints one warning line for it, and exits 0. Each `show`
  says what that leaves out:

    ```text
    warning: '<id>' is unavailable, so its status is not shown: <reason>
    warning: '<id>' is unavailable, so its items are not counted in children and blocks: <reason>
    warning: '<id>' is unavailable, so its taxonomy entries are not included: <reason>
    ```

    The first is from `tcw capabilities show`, the second from
    `tcw work show`, the third from `tcw taxonomy show`. The listings say
    `so its work items are not listed`, `so its capabilities are not listed`
    and `so its taxonomy entries are not listed`.

Each message says where TCW looked. When the manifest entry that decides where
the project is (step 2 of [How TCW looks for a project](#how-tcw-looks-for-a-project))
gives a `repository`, the message ends by naming the `tcw project provision` command
that fetches the project.

## Views of the whole family: `--scope`

A command normally covers only the active project's own objects. Eight
commands, the `list`, `show` and `search` commands of the three axes (there is
no search command for work items), take `--scope` to cover more: `up` adds
the project's ancestors, `down` its descendants (its children and their
children), `all` both, and `own`, the default, only the project itself. A
scope never covers a sibling. `--project <id>` keeps one covered project's own
objects. So
`tcw work list --scope down`, run in `workspace`, lists the work items of
`workspace` and of every project below it, and `tcw capabilities show
billing/refund --scope down` shows the status each covered project gives that
capability. [The command line guide](cli.md), in "Which projects a command
covers", describes both options in full.

## Changing another project's objects

**A command creates, changes or deletes objects only in the project that owns
them**, the project it runs as. An object's full identifier says which project
owns it. An inherited object is never changed from below, and a child's
object never from above. Asked to change another project's object, a command
refuses with exit code 3 and names the folder to run it in:

```text
tcw work edit: workspace.work/2026-10-15-plan-billing belongs to project 'workspace'; run the command there: tcw -C /home/me/src/workspace …
```

To change it, run the command as the owning project. `tcw project path <id>`
prints that project's folder, and `tcw -C <folder>`, given straight after
`tcw`, runs any command as if `tcw` had been started there, with that
project's own configuration, personal settings, checks and hooks. The folder
can also be given as a folder address, which TCW finds the way it finds any
related project:

```sh
tcw -C tcw://workspace.path/ work edit workspace.work/2026-10-15-plan-billing --priority high
tcw -C ../core work new "Add refunds" --parent workspace.work/2026-10-15-plan-billing
```

Overriding an inherited taxonomy entry or capability is allowed, since the
override is a new object that the active project owns
([Taxonomy and Capabilities](taxonomy-and-capabilities.md) explains it).

**The one stated exception is a blocker in another project.** An item may
name an item in another project as its blocker
(`tcw work edit <item> --blocked-by <full id>`), and likewise as its parent
(`--parent`). The link is written in the naming item's own record, so the
other project's item is not changed; `tcw work show` of that item, under a
scope that covers both, lists the naming item under `blocks` or `children`.
[The Jira guide](jira.md) says how such a link appears in Jira.

## Stores in another repository

Each of the three stores, taxonomy, capabilities and work, is a folder:
`docs/<component>/` unless `.tcw/tcw-config.yaml` says otherwise, under
`taxonomy.path`, `capabilities.path` or `work.path`. A store can live
somewhere else, including in another repository. A common layout keeps every
project's work items in the planning workspace's repository while the code
lives in several:

```text
workspace/                    repository A: the workspace, and the app's work store
├── .tcw/tcw-config.yaml
└── docs/app/work/            the app's work store
app/                          repository B
└── .tcw/tcw-config.yaml      work.path: tcw://workspace.path/docs/app/work
```

A store location is one of two things:

- **a path relative to the project's folder**, such as
  `../workspace/docs/app/work`;
- **a `.path` address**, a folder named through a project's ID:
  `tcw://<id>.path/<folder>` is a folder inside that project's folder, and
  `tcw://<id>.<axis>.path/<folder>` a folder inside that project's own store
  for that axis. TCW finds the named project the way it finds any related
  project, so the address keeps working when the folders are laid out
  differently on another machine.

An absolute path, or one starting with `~`, is refused in the shared
`.tcw/tcw-config.yaml`, since every machine reads that file; a folder that
sits elsewhere on one machine is placed by an entry in
`.tcw/tcw-manifest.local.yaml`:

```text
tcw work path: .tcw/tcw-config.yaml: work.path: must be a path relative to the project, or a tcw:// .path address such as tcw://<project>.path/<folder>; a folder that sits elsewhere on this machine is placed by an entry in .tcw/tcw-manifest.local.yaml
```

**Stores never nest or share a folder,** within one project or across
related projects (a project's taxonomy store inside its own work store is
refused too), and `tcw validate` reports one that does as an error:

```text
error: .tcw/tcw-config.yaml: the work store of project 'app' (/home/me/src/workspace/docs/work/app) lies inside the work store of project 'workspace' (/home/me/src/workspace/docs/work); stores never nest or share a folder
```

Store locations may not loop either, such as `app`'s `work.path` naming a
folder in `core`'s work store while `core`'s names one in `app`'s; every
command that opens the store refuses it (exit code 1), naming the loop:
`work.path: store locations loop: app work -> core work -> app work`.

A store can also say where to get it when it is not here, in a `repository`
block beside its `path`, in `.tcw/tcw-config.yaml`. The block stays on the
store: it is not a manifest entry, and it holds `url` (required), `ref`,
`path` (the store's folder inside that repository) and `checkout` (where to
put the copy; by default a folder in TCW's cache):

```yaml
id: app
work:
    path: ../workspace/docs/app/work
    repository:
        url: https://example.com/acme/workspace
        path: docs/app/work
```

A store that is already where `path` says always wins; the `repository`
block is used only when it is not. Until then, a command that needs the store
stops (exit code 1) and names the command that fetches it,
`tcw project provision --component work`.
`tcw work path`, `tcw taxonomy path` and `tcw capabilities path` print where
each store is.

Keeping a store in another repository up to date is the project's job: TCW
never changes git state, so it never pulls or pushes a store. The
[configuration guide](configuration.md)'s example of keeping git in step with
each stage change shows one way: its prompt text asks the agent to pull the
work store's repository too, before starting each stage, and its `post` hook
commits an item's folder in whichever repository holds it.

## Fetching what is missing: `tcw project provision`

`tcw project provision` fetches what the active project needs and does not
have here: each store with a `repository` block, and each project of its
family that is not on this machine and whose manifest entry, the one that
decides where it is, gives a `repository`. It works in rounds: after each round it reads the family again,
so a project a fetched project names is fetched in the next round. A project
no manifest gives a repository for is reported and skipped; once a fetch
brings the manifest that places it, running the command again fetches it.

- `tcw project provision <id>` fetches only that project and the projects it
  inherits from, and no store;
- `--component <axis>` fetches only that store, and no project;
- `--dry-run` prints the plan and contacts nothing.

It **clones what is missing and never updates what is already here**, so
running it again does nothing more. It prints every repository address before
it contacts it, on standard error. A project is cloned into the folder its
manifest entry gives (with `subfolder` removed), and a store into its
`checkout`, or TCW's cache. A run that fetched some things and failed others
keeps what it fetched and exits 1:

```text
fetched 1, failed 1; what was fetched stays, and running the command again fetches the rest
```

It **does not ask for anything** while it clones: not a password or token,
not an ssh key's passphrase, and not whether to trust a server it has not
met. git's prompts and Git Credential Manager's are turned off, and ssh runs
in batch mode. The one exception is an ssh command you have set yourself
(`GIT_SSH_COMMAND`, `GIT_SSH`, or git's `core.sshCommand` in your global or
system git config or given on the git command line, not the current
repository's own setting): TCW leaves it as it is, so ssh may still ask, as it
would for any clone you run. Where an answer would be needed the clone fails,
and the message gives git's reason. So a private repository needs credentials
that git can find without asking: a credential helper that already holds
them, or an ssh key loaded in an ssh agent, with the server already in your
known hosts.

### Where a clone may be placed

A manifest fetched from someone else's repository could otherwise place a
clone anywhere on your disk, so TCW limits where each manifest may place one.
The limits are checked on every run, and again just before each clone writes
anything:

- **The active project's own two manifests are trusted.** An entry in
  `.tcw/tcw-manifest.yaml` or `.tcw/tcw-manifest.local.yaml` of the project
  `tcw project provision` runs in may place a clone anywhere, and the folders
  above it are made when they are missing.
- **Any other manifest may place a clone only in a folder directly inside
  the folder holding its owner's repository.** The owner is the project
  whose `.tcw/` holds the manifest. If `workspace` is a repository at
  `/home/me/src/workspace`, its manifest may place a clone at
  `/home/me/src/<name>`, such as `../core`, and nowhere else: not deeper
  (`../vendor/core`), not higher (`../../core`), not at an absolute path, and
  not in a folder whose name starts with `.`. A project that is not inside a
  git repository counts as its own repository folder. Each of these is
  refused with the same words, `outside`, followed by the folder holding the
  owner's repository, even when the clone's folder is inside that folder but
  deeper or hidden:

    ```text
    tcw project provision: core: /home/me/src/workspace/.tcw/tcw-manifest.yaml places it at /home/me/src/.core, outside /home/me/src; a manifest that is not this project's own may place a clone only in a folder directly inside /home/me/src; …
    ```

- **Never when that folder is the home folder or a folder above it, or a
  hidden folder below the home folder** (one whose path below the home folder
  has a part starting with `.`). A repository kept directly in your home
  folder, or in `~/.something/`, cannot have another project's manifest place
  clones beside it:

    ```text
    tcw project provision: core: /home/me/workspace/.tcw/tcw-manifest.yaml places it at /home/me/core; '/home/me/workspace' sits in /home/me, which is the home folder, a folder above it, or inside a hidden folder below it, so a manifest that is not this project's own may not place a clone there; …
    ```

- **A manifest whose owner has a `.git` that git cannot read** is refused
  until that is fixed, or until the way out below is taken, since the folder
  holding its repository is not known:
  `but git could not say which repository holds '<folder>' (<git's reason>), so the folder a manifest that is not this project's own may use is not known`.
- **Inside a git submodule**, a repository kept inside another one, the
  submodule is the owner's repository: a manifest in it may place a clone
  beside the submodule, inside the enclosing repository.
- **In a linked git worktree** (below), the active project's repository folder
  is its main checkout, so a clone goes beside the main checkout rather than
  beside the worktree.

**The way out** is either of two, and each refusal names the ones that apply:

- run the command as the owning project, which makes its manifests the active
  project's own and so trusted: `tcw -C <folder> project provision <id>`,
  where `<folder>` is the owner's folder; or
- add an entry for the project to a manifest read before the refusing one:
  the active project's own manifests, or the owner's
  `.tcw/tcw-manifest.local.yaml`, then run the command as that project. **The
  entry needs a `repository` as well as a `path`**: an entry with a path
  alone says where the project is but not where to fetch it from, so the
  command reports
  `not on this machine, and no manifest entry gives the repository to fetch it from`
  and fetches nothing (exit code 5 for `tcw project provision <id>`, 0
  without an ID).

### Folders that stopped clones leave behind

- **A folder holding only `.git` is refused.** It is what a clone or a
  submodule update leaves when it stopped before checking out a file. TCW
  does not guess whether to finish or replace it:
  `holds only .git (a clone or a submodule update that stopped); finish or remove it with git, then run again`.
  Until then, the project counts as not on this machine. A folder holding
  other files is refused too, with
  `is not empty; move it aside, or correct the manifest entry in …`; an empty
  folder is filled.
- **A `.tcw-staging-<hex>` folder** (`<hex>` being eight random characters
  drawn from `0` to `9` and `a` to `f`) is where a clone is made before it is
  checked and moved into place, in the folder that will hold it. TCW removes it when the clone is done or
  fails; a run that was stopped part way, such as by closing the terminal,
  can leave one behind. Nothing reads it, and it is safe to delete.

## Git worktrees

A **linked git worktree** is a second working folder of the same repository,
made with `git worktree add`, often to work on a branch while the main
checkout stays on another. A project opened from a linked worktree is read
this way:

- **Tracked files come from the worktree**: `.tcw/tcw-config.yaml`, the
  shared manifest and the stores inside the repository are the worktree's
  own, on its own branch.
- **Personal files come from the worktree, or else from the main checkout**:
  `.tcw/tcw-config.local.yaml` and `.tcw/tcw-manifest.local.yaml` are read
  from the worktree when it has them, and otherwise from the main checkout's
  copy of the project, since they are never committed and so a new worktree
  does not have them.
- **A path that leads out of the repository is read from the main
  checkout**: a manifest entry such as `../core`, a store location outside the
  repository, and the search's folders next to the project and enclosing it.
  So paths written for the main checkout keep working from a worktree kept
  anywhere, and a clone `tcw project provision` makes goes beside the main
  checkout. A path that stays inside the repository is read inside the
  worktree.
- **Except where the path, read as written, lands in another checkout**: a
  manifest entry or a store location that leads out of the repository is
  read where it is written when it lands on a project or folder inside a
  checkout, main or linked, of another repository, and of the repository the
  entry names when it names one. So worktrees made one inside another, such
  as a child repository's worktree placed inside its workspace's worktree,
  read each other, not the folders they were made from. The search is not
  changed by this.

## Moving from 3.x

In 3.x, related projects were connected under a `projects:` key in the
project's configuration file, with paths, as parent, children or `upstream`
entries; taxonomy and capabilities were inherited through `extends`; and an
item could be filed into another project's inbox from here. In 4.0, parent
links are `parents:` and `children:` by ID, locations are in manifests, a
library its readers name as a parent replaces an upstream entry, inheritance
follows the parent links, and an item for another project is made in that
project, by running the command with `tcw -C <folder>`. `tcw migrate`
converts a 3.x project's files; the [migration guide](../migration-guide-3.X-to-4.0.0.md) maps every
3.x name to its 4.0 replacement.

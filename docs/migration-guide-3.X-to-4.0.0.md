# Migrating from TCW 3.x to 4.0.0

This guide moves a project, or a family of related projects, from TCW 3.x to
TCW 4.0. It is written for a person and for an AI agent acting for one: the
steps are in order, and every command is written out.

TCW 4.0 does most of the work itself. One command, `tcw migrate`, converts a
3.x project's files to the 4.0 format and, when the project's work is kept in
Jira, converts its tickets. This guide says what to do before you run it, how
to run it, how to read what it prints, and what replaces each command, flag,
setting and file that 3.x had and 4.0 does not.

A **migration**, in this guide and in TCW, means converting a project's files
to a newer format. Every file TCW 4.0 writes starts with a `tcw-version` line
saying the version it was made or last migrated with; a file with no such line
is a 3.x file, and TCW 4.0 reads only 4.0 files.

## Before you start

1. **Check that the project is a 3.x project.** TCW 4.0 migrates 3.x projects
   only. A project still in 2.x form first follows the
   [2.8 to 3.0.0 guide](migration-guide-2.8-to-3.0.0.md) with a 3.x `tcw`, and
   then this one. A 3.x project has its configuration file, `tcw-config.yaml`,
   at its root and no `.tcw/` folder.
2. **Commit the project, or back it up.** `tcw migrate` rewrites, moves and
   deletes files. Inside git, a commit made just before the run is your way
   back. A folder that is not in git has no way back unless you copy it first.
3. **Upgrade together with everyone who works on the project.** TCW 4.0 reads
   only 4.0 files and refuses a 3.x project it reaches, and TCW 3.x cannot read
   a migrated project. So everyone working on the project, and every agent,
   upgrades both the `tcw` command and the TCW plugin at the same time, and the
   project is migrated once, by one person, who then shares the result.
4. **Install TCW 4.0.** The command is installed from PyPI, the Python package
   index, as `tcw-cli`:

    ```sh
    pipx upgrade tcw-cli
    ```

    or, where it is not installed yet, `pipx install tcw-cli`. The plugin is
    updated the way it was installed (the [README's Installation](../README.md#installation)
    section has the commands for Claude Code, Codex and Pi); in Claude Code the
    plugin then installs the matching `tcw` at the start of the next session.
    `tcw --version` prints `tcw 4.0.0` once it is in place.

5. **Have the Jira credentials at hand, or plan to convert the tickets later.**
   A project whose work is kept in Jira has its tickets converted too, which
   needs the Jira credentials the project names. Without them, run with
   `--no-jira` (below) and convert the tickets later.
6. **Hold automation back until the project is migrated.** Continuous
   integration (CI) jobs and other scripts that install `tcw-cli` without a
   version limit get 4.0 as soon as it is published, and then fail on a project
   that is still 3.x. Limit them below 4 until the project is migrated, for
   example:

    ```sh
    pipx install 'tcw-cli<4'
    ```

    and raise the limit in the same change that commits the migrated project.

## Migrating one project

**If the project has parents or children, read
[Migrating related projects](#migrating-related-projects) before you run
anything:** the order matters there. A project with no related projects needs
only this section.

### 1. See what would change: `tcw migrate --dry-run`

Run this from the project's folder:

```sh
tcw migrate --dry-run
```

It lists every file and ticket the migration would change and changes nothing:
no file, no folder, no ticket. Everything it prints goes to standard error.
For a small 3.x project it prints, for example:

```text
would write .tcw/tcw-migration.yaml: C10
would write .tcw/.gitignore: C1
would write docs/taxonomy/invoice/tcw-taxonomy.yaml: C9
would delete docs/taxonomy/invoice/meta.yaml: C9
would write docs/capabilities/pay-an-invoice/tcw-capability.yaml: C9, C10
would delete docs/capabilities/pay-an-invoice/meta.yaml: C9
would write docs/work/2026-10-24-add-export/tcw-work-item.yaml: C9
would delete docs/work/2026-10-24-add-export/item.yaml: C9
would write .tcw/tcw-config.yaml: C1
would write .tcw/.gitignore: C1
would delete tcw-config.yaml: C1
needs attention:
  A4 .gitignore:1: /tcw-config.local.yaml now ignores nothing: the personal file is .tcw/tcw-config.local.yaml, which .tcw/.gitignore ignores
  A5 /home/me/.config/tcw/config.yaml:7: work.stages.spec.prompt[0].when.not_tags: TCW 4 refuses not_tags; write not-tags (this file is shared with any TCW 3.x on this machine, which needs not_tags, so tcw migrate leaves it)
reads differently in TCW 4:
  D5 tcw-config.yaml: work.tags: null now removes the value a parent project passes down
would change: 6 files written, 0 moved, 4 deleted; 0 tickets edited
tcw validate's findings on the converted project are known only after a real run
```

### 2. Read what it prints

**The change lines** come first, one per change, each naming the file and the
conversion that makes it (`C1` to `C17`, the code TCW uses for each kind of
conversion):

- `write <path>: <codes>`: a file written, new or rewritten;
- `move <old> -> <new>: <codes>`: a file or folder moved;
- `delete <path>: <codes>`: a file deleted, once its 4.0 copy is written and
  read back;
- `edit <KEY>: C17 TCW Item: <old> -> <new>`: a Jira ticket whose `TCW Item`
  field is converted.

In a dry run each line starts with `would `. Then come up to three lists:

- `needs attention:` lines, `<An> <where>: <text>`. TCW 4.0 reads the project,
  but something should be fixed by hand; `tcw validate` would say the same.
  These do not stop the run.
- `reads differently in TCW 4:` lines, `<Dn> <where>: <text>`. Nothing is
  wrong, but the converted project behaves differently from the 3.x one here
  (for example, a value a parent now passes down). Read each one.
- `refused:` lines, `<Bn> <where>: <why>; <what to do>`. A **blocker**: something
  `tcw migrate` cannot convert without guessing. A run with any blocker
  refuses the whole migration and writes nothing. Each line says what to do; do
  it, in 3.x or by hand, and run `tcw migrate --dry-run` again. For example:

    ```text
    refused:
      B8 docs/capabilities/Pay an invoice: the id-part 'Pay an invoice' breaks the rule: letters, digits, '-' and '_', starting with a letter or digit, at most 128 characters; rename the folder by hand, then run 'tcw migrate' again
    ```

Last comes a count of the changes, and, when the run is in a family, the
related projects still in 3.x form.

Two of the reports need a word more:

- **A5** names `not_tags` in your user-wide file
  (`~/.config/tcw/config.yaml`, or `$XDG_CONFIG_HOME/tcw/config.yaml` where that
  variable is set). TCW 4.0 spells that key `not-tags`, but the user-wide file
  is shared with any TCW 3.x on the same machine, which needs `not_tags`, so
  `tcw migrate` reports it and leaves it as written. Change the line it names
  to `not-tags` once no TCW 3.x is used on that machine; until then
  `tcw validate` reports it as an error in every project.
- **A12**, after a real run, lists the findings `tcw validate` gives on the
  converted project that the project already had in 3.x, such as a capability
  with no `Status`. They are not caused by the migration. A dry run cannot list
  them.
- **B10** is a reference 3.x gave no single owner, including a
  `capabilities.yaml` entry 3.x could not route: one in a project that keeps no
  capabilities ledger, naming no child project. Fix the entry by hand.

### 3. Run it: `tcw migrate`

```sh
tcw migrate
```

It prints the same lines without `would `, and ends with
`changed: <n> files written, <n> moved, <n> deleted; <n> tickets edited`.
Running it again on a finished project prints `nothing to migrate`, changes
nothing and exits 0.

Then run `tcw validate`. It should end `0 errors, 0 warnings, 0 unresolved`;
each finding it gives says what to fix. Read every changed file
(`git status` and `git diff` inside git), then commit the project, CI's
version limit raised in the same change (step 6 of
[Before you start](#before-you-start)).

`tcw migrate` does not check git and commits nothing. It runs whether or not
the working tree has changes, and leaves committing to you.

**What it writes**, besides the converted files:

- **`.tcw/tcw-migration.yaml`**, the migration record. It holds what the
  migration removed that has no 4.0 place of its own: every 3.x capability id
  with the capability's path now, every override it moved, and every removed
  value. Commit it. Only `tcw migrate` reads it: a project that reads this one
  as a parent uses it when it migrates later, to find what this one's 3.x
  names became. Keep it through TCW 4.x. A library that other projects read
  must keep it; a project whose every reader has migrated may delete it.
- **`.tcw/tcw-migration-progress.yaml`**, the progress record, only while a
  run is unfinished (below).

### Jira: `--no-jira`, and converting the tickets last

For a project whose work is kept in Jira, `tcw migrate` also edits each of the
project's tickets whose `TCW Item` field holds a 3.x value, writing the 4.0
value (the item's full identifier, below), and changes no other field: status,
links, comments and labels stay as they were. The Jira settings it uses are
the project's own `work.jira`, in its 3.x or 4.0 files, never a parent's; a
problem elsewhere in the configuration does not stop the ticket conversion.

**`--no-jira` converts the files only.** It never builds a Jira client, so it
needs no credentials and cannot reach Jira, whatever the configuration says.
It is the way to keep a run off a live board, and to convert the files when
Jira cannot be reached:

```sh
tcw migrate --no-jira
```

Its summary says what it left, for example:

```text
tickets not converted (--no-jira): the TCW Item of every ticket of Jira project APP whose TCW Project is 'app' and that holds a 3.x value; run 'tcw migrate' to convert them
work store not checked after the run (--no-jira): run 'tcw validate' to check it
```

A later `tcw migrate`, without the flag, finds the files already converted and
converts only the tickets. **Until it does, the board looks emptier than it
is:** 4.0's `tcw work list` leaves out every ticket that still holds a 3.x
value, with one warning naming their keys and `tcw migrate`.

A dry run, with or without `--no-jira`, cannot edit a ticket: without the flag
it searches Jira to list the tickets it would edit, through a connection that
can only read.

**A run whose Jira step fails while it is planning writes nothing.** It lists
the local changes it would have made, the Jira error, and

```text
nothing was written; 'tcw migrate --no-jira' converts the files without Jira
```

**The way back.** Restoring the commit or backup of step 2 of
[Before you start](#before-you-start) brings the files back at any time. It
does not bring the tickets back: once a run has converted them, no command
puts a ticket's 3.x `TCW Item` back. So a project whose work is kept in Jira
migrates in this order:

1. `tcw migrate --no-jira`;
2. `tcw validate`, and read the changes;
3. `tcw migrate`, which now converts only the tickets.

### Exit codes

| Exit | Meaning                                                                                                                                                                                           |
| ---- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 0    | finished, or nothing to migrate; with `--no-jira`, the files finished and Jira not contacted; for `--dry-run`, a plan with no blocker                                                             |
| 1    | a step failed partway (run it again, below); or Jira refused the credentials, they are not set, or Jira gave another error that is not "cannot be reached"; or there is no project in this folder |
| 2    | an argument was given (`tcw migrate` takes none)                                                                                                                                                  |
| 3    | refused: one or more blockers; nothing was written                                                                                                                                                |
| 5    | Jira could not be reached, or limited requests                                                                                                                                                    |

A Jira failure keeps the code every TCW command gives it: 5 when Jira cannot be
reached or limits requests, 1 when the credentials are missing or refused.

### When a run stops partway

A run can stop partway: a refused permission, a full disk, an interrupted
command. **It is finished by running `tcw migrate` again**, which never
repeats a change it already made. A stopped run says what it did, what it did
not do, and ends:

```text
run 'tcw migrate' again to finish
do not save these files in version control until 'tcw migrate' finishes
```

While a run is unfinished, the project holds a **progress record**,
`.tcw/tcw-migration-progress.yaml`: every step the run planned, so that the
next run finishes the plan instead of working it out again from half-converted
files. It holds personal values, so it is never committed; inside git,
`.tcw/.gitignore` ignores it. The run that finishes deletes it. Do not commit
the project while it is there.

- **Do not delete the progress record** while a run is unfinished. If it is
  deleted, restore the project from the commit or backup of step 2 of
  [Before you start](#before-you-start) first, then run `tcw migrate` again.
- **Do not edit the files between a stopped run and its re-run.** A file the
  run still has to rewrite or delete that was changed meanwhile stops the
  re-run with blocker **B17**, naming the file: restore it as it was, or
  restore the project, delete the progress record, and run again.
- **A store with a mount point inside it.** `tcw migrate` moves folders by
  renaming them, and does not copy across two filesystems. A move between two
  filesystems stops the run with
  `<old> and <new> are on different filesystems; tcw migrate does not copy across them: move it by hand, keeping its contents, then run 'tcw migrate' again`.
  Do that; the next run finds the move done and carries on.
- **A stopped run, run again while Jira cannot be reached**, writes nothing
  more, exits with Jira's code (above), and says
  `nothing more was written; 'tcw migrate --no-jira' finishes the files without Jira`.

### After the project is migrated: the second person, and old branches

**Everyone else**, after pulling the migrated project, runs `tcw migrate`
once too. It converts the files that are theirs alone and never committed,
such as a personal `tcw-config.local.yaml`, and changes a tracked file only
where one is still in 3.x form.

**A branch made before the migration** brings 3.x files back when it is
merged. Run `tcw migrate` again after merging it; it converts what the branch
brought.

## Migrating related projects

Projects are **related** when one names another as its parent; a **family** is
a project with every project related to it. A 3.x family was connected under
the `projects:` key; `tcw migrate` converts that into 4.0's parent links
(`parents:` and `children:`) and manifests, which say where each related
project is on this machine. The [Related projects guide](guide/multi-repo.md)
explains them.

1. **Each project is migrated by running `tcw migrate` in it**, from its own
   folder, or from anywhere with `-C`, which runs a command as if it were
   started in that folder: `tcw -C <folder> migrate`. A run changes only that
   project's files, never another project's.

2. **Migrate parents before children.** TCW 4.0 refuses a related project
   still in 3.x form before it reads anything from it. So in a migrated
   project whose parent is still 3.x, almost every command stops with exit 1
   and a line naming the parent:

    ```text
    tcw work list: /home/me/src/mono: is a TCW 3.x project (tcw-config.yaml at its root, no .tcw/ folder); run 'tcw migrate' in it to move it to TCW 4
    ```

    Migrating a child first is allowed and gives the same files, but its
    commands stop until its parent is migrated. Migrating each parent first
    leaves no 4.0 project below a 3.x one at any moment.

3. **Each run's summary lists the family's projects still in 3.x form**, the
   parents first, each with the command that migrates it:

    ```text
    needs attention:
      A8 /home/me/src/mono: 'mono' is still a TCW 3.x project; migrate it with 'tcw -C /home/me/src/mono migrate'
    ```

    Work down the list until a run lists none.

4. **A planning workspace that holds other projects' stores.** When a
   project's work store (the folder holding its work items) sits in another
   project's repository, such as a planning workspace, the project's own
   migration converts that store, and the files it changed there are listed
   under `left in another repository: <folder>`, for whoever commits in that
   repository. The workspace's own migration converts only its own stores.

5. **A related project that is not on this machine.** Most related projects
   are converted from what this project's own files say about them, without
   reading them. When a conversion must read one that is not here, the run
   stops with blocker B5, naming the project and the command that fetches it,
   such as
   `fetch it with 'git clone <repository> <folder>'`; then run `tcw migrate`
   again. Once the project is migrated, `tcw project provision` fetches every
   related project its manifests name (see
   [Where provisioning may place a clone](#where-provisioning-may-place-a-clone)).

6. **What 3.x inheritance becomes.** Each converted link is printed for review
   under `reads differently in TCW 4:`:

    - a 3.x parent becomes a parent link that passes everything down, and D1
      lists what the child now inherits that 3.x did not pass it;
    - an `extends` that named a sibling or another project becomes one more
      parent link, inheriting only the axes the `extends` named;
    - an `extends` that named one of the project's own listed children is
      turned around: that child becomes the parent, and D6 lists the link
      dropped;
    - an upstream project becomes a parent link inheriting the axes an
      `extends` named, or nothing.

## What each 3.x name becomes

The tables below name every 3.x command, flag, setting, file and name that 4.0
removes or renames, and what replaces it. The first column is 3.x; none of its
commands works in 4.0.

### Commands

| 3.x command                         | In 4.0                                                                                                                           |
| ----------------------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| `tcw init`                          | `tcw project new --id <id>`, which writes `.tcw/tcw-config.yaml`                                                                 |
| `tcw projects list`                 | `tcw project list`                                                                                                               |
| `tcw config show`                   | `tcw project config`; `--origin` says where each value comes from                                                                |
| `tcw provision`                     | `tcw project provision`                                                                                                          |
| `tcw taxonomy extends add <id>`     | a parent link to `<id>` whose `inherit` includes `taxonomy`, in `.tcw/tcw-config.yaml` ([Related projects](guide/multi-repo.md)) |
| `tcw taxonomy extends rm <id>`      | `taxonomy` left out of that parent link's `inherit`, or the link removed                                                         |
| `tcw capabilities extends add <id>` | a parent link to `<id>` whose `inherit` includes `capabilities`                                                                  |
| `tcw capabilities extends rm <id>`  | `capabilities` left out of that parent link's `inherit`, or the link removed                                                     |

### Flags

| 3.x flag                                                                 | In 4.0                                                                                                                                                   |
| ------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `tcw work new --project <id>`, as in `tcw work new "<t>" --project <id>` | the item is made in its own project: `tcw -C <folder> work new "<t>"`, where `tcw project path <id>` prints the folder                                   |
| `tcw work edit --blocks <b>`, as in `tcw work edit <a> --blocks <b>`     | the blocked item records it, in its own project: `tcw -C <b-folder> work edit <b> --blocked-by <a>`, where `<b-folder>` is the folder of `<b>`'s project |
| `--local` on `tcw taxonomy list` or `tcw capabilities list`              | not needed: a plain listing shows only the project's own entries; `--scope up` adds inherited ones                                                       |

### Configuration

| 3.x setting                                                                                | In 4.0                                                                                                                                                   |
| ------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `tcw-config.yaml` at the project's root                                                    | `.tcw/tcw-config.yaml`, starting with `tcw-version: 4.0.0`                                                                                               |
| `tcw-config.local.yaml` at the project's root                                              | `.tcw/tcw-config.local.yaml`, never committed                                                                                                            |
| `not_tags` (in a binding's `when:` or a documentation entry)                               | `not-tags`                                                                                                                                               |
| `projects.parent`                                                                          | `parents:`, a list of project IDs, each passing everything down unless it gives `inherit`                                                                |
| `projects.children`                                                                        | `children:`, a list of project IDs, in the shared or the personal file                                                                                   |
| `projects.upstream` (`upstream:` under `projects:`), an upstream project                   | a parent link with `inherit` naming the axes it passed, or `none`; the library does not list its readers                                                 |
| `extends:` under `taxonomy` or `capabilities` (`taxonomy.extends`, `capabilities.extends`) | `inherit` on a parent link                                                                                                                               |
| a path under `projects.<id>`                                                               | an entry in `.tcw/tcw-manifest.yaml` (shared) or `.tcw/tcw-manifest.local.yaml` (personal), which says where a project is                                |
| `projects.<id>.repository`                                                                 | the manifest entry's `repository`, written `<url>` or `<url>#<branch>`, with `subfolder` for a folder inside it                                          |
| `projects.<id>.jira`                                                                       | removed: an item for another project is made in that project; the value is kept in `.tcw/tcw-migration.yaml`                                             |
| `work.path: /abs/path` or another absolute store location                                  | a path relative to the project, or a `.path` address such as `tcw://workspace.path/docs/app/work`; an absolute path is allowed only in the personal file |
| `work.path: ~/docs/work`                                                                   | the same: relative, or a `.path` address                                                                                                                 |
| `<component>.repository`, a store's own repository                                         | unchanged: it stays on the store                                                                                                                         |

### Files

| 3.x file                                                  | In 4.0                                                                                                               |
| --------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| `meta.yaml` in a taxonomy entry's folder                  | `tcw-taxonomy.yaml`, starting with `tcw-version`                                                                     |
| `meta.yaml` in a capability's folder                      | `tcw-capability.yaml`, starting with `tcw-version`                                                                   |
| `item.yaml` in a work item's folder                       | `tcw-work-item.yaml`, starting with `tcw-version`; other loose files of the folder move into its `resources/` folder |
| `overrides: core/cap-1a2b3c` in a capability's state file | no pointer: an override is an object at the same path as the one it overrides, holding only what it changes          |
| `cap-1a2b3c`, a capability's id                           | none: a capability is named by its path; the old ids are kept in `.tcw/tcw-migration.yaml`                           |

### Names and addresses

| 3.x name                                                  | In 4.0                                                                                                           |
| --------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| `<project>/<folder>`, an item's slug                      | `<project>.work/<folder>`, its full identifier                                                                   |
| `tcw://C/<id-path>`, `tcw://W/<folder>`, `tcw://T/<term>` | `tcw://<project>.capabilities/<id-path>`, `tcw://<project>.work/<id-path>`, `tcw://<project>.taxonomy/<id-path>` |
| `tcw://core/T/<term>`, a link into another project        | `tcw://core.taxonomy/<term>`, which may name any project TCW can locate                                          |
| a ticket's `TCW Item` value `tcw/TCW-12-add-export`       | `tcw.work/TCW-12-add-export`, converted by `tcw migrate`                                                         |

A **full identifier** names one object in any project:
`<project>.<namespace>/<id-path>`, such as `app.work/2026-10-24-add-export` or
`core.taxonomy/invoice`. "Slug" is a nickname for it. Every command prints full
identifiers, and accepts one, its `tcw://` address, a ticket key, or an
id-path in the active project. The
[Linking and validation guide](guide/linking-and-validation.md) has the
grammar.

### Output a script reads

| 3.x output                                 | In 4.0                                                                                                                          |
| ------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------- |
| `"schema": 1` in `--json` output           | `"schema": 2`; each record carries `full-id` and `owner`                                                                        |
| the `--origin` comment `# <layer>: <file>` | `# <project>, <layer> <file>`, such as `# app, project .tcw/tcw-config.yaml` or `# my-proj, environment TCW_USER_NAME__MY_PROJ` |

### What reads differently with no name change

- **Plain listings show only the project's own entries.**
  `tcw taxonomy list` and `tcw capabilities list` list what this project
  declares; `--scope up` adds what it inherits. `tcw capabilities show <id-path>`
  of an inherited capability needs `--scope up` too.
- **A plain listing carries no override mark and no status summary.** Both are
  in `--json` and in `show`.
- **A related project that is not on this machine gives exit 7.** A command
  that needs a related project that is not here, or a setting only that
  project could give, exits 7 and says how to fetch it, where 3.x gave 5 or 1.
- **Only the project that owns an object changes it.** A change to another
  project's item, term or capability is refused with exit 3, naming the
  folder to run it in; run it there with `tcw -C <folder>`. A blocker in
  another project is the one exception: an item may name one with
  `--blocked-by`.

### New in 4.0

| Command or option                                  | What it does                                         | Where it is explained                                           |
| -------------------------------------------------- | ---------------------------------------------------- | --------------------------------------------------------------- |
| `tcw project path <id>`                            | prints a related project's folder on this machine    | [Related projects](guide/multi-repo.md)                         |
| `tcw project info`                                 | shows the project's parents, children and load order | [Related projects](guide/multi-repo.md)                         |
| `tcw -C <folder>`                                  | runs any command as if started in that folder        | [The command line](guide/cli.md)                                |
| `--scope own\|up\|down\|all`                       | how much of the family a listing or `show` covers    | [The command line](guide/cli.md)                                |
| `--project <id>`                                   | keeps one project's results                          | [The command line](guide/cli.md)                                |
| `tcw work move`                                    | moves an item to another place in its store          | [The Work component](guide/work.md)                             |
| `tcw taxonomy rename`, `tcw taxonomy move`         | renames or moves a taxonomy entry                    | [Taxonomy and Capabilities](guide/taxonomy-and-capabilities.md) |
| `tcw capabilities rename`, `tcw capabilities move` | renames or moves a capability                        | [Taxonomy and Capabilities](guide/taxonomy-and-capabilities.md) |
| `tcw work new --nest`                              | puts a new item's folder inside its parent's folder  | [The Work component](guide/work.md)                             |

## The epic-parts flow, step by step

In 3.x, an epic, a large item split into parts, could have a part filed into
another project's inbox from the epic's project. In 4.0, **an agent taught the
3.0.1 or 3.0.2 flow changes one thing: it runs each part's command in the
part's own project, with `tcw -C`.** The part names its epic with `--parent`
and the epic's full identifier, and because the command runs as the part's
project, every option, that project's own stages and settings apply.

| #   | 3.x step                                                                                                               | 4.0                                                                                                      |
| --- | ---------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| a   | `tcw work new "<t>" --project <id>`                                                                                    | `tcw -C tcw://<id>.path/ work new "<t>" --parent <epic>`                                                 |
| b   | a ticket key printed instead of a slug, because no item exists there yet                                               | does not happen: the command runs in the part's project, which makes its item as any `tcw work new` does |
| c   | record the other project's changes before filing there again, or the next filing is refused or stays in the Jira inbox | not required by TCW; record changes the way that project does                                            |
| d   | from inside that project, `tcw work edit <part> --parent <epic>`                                                       | part of step a                                                                                           |
| e   | from inside that project, `tcw work edit <part> --blocked-by <ref>`                                                    | `tcw -C tcw://<id>.path/ work edit <part> --blocked-by <ref>`, or `--blocked-by` on step a               |
| f   | `tcw work edit <a> --blocks <b>`                                                                                       | `tcw -C <b-folder> work edit <b> --blocked-by <a>`, run in the folder of `<b>`'s project                 |

`tcw://<id>.path/` is the address of project `<id>`'s folder on this machine;
`tcw project path <id>` prints the same folder. `--nest`, which puts a new
item's folder inside its parent's, applies only when the parent is in the same
project; across projects TCW makes the part at the top of its own project's
work folder and says so.

## Personal settings and environment variables

- **The personal files** are `.tcw/tcw-config.local.yaml` (settings) and
  `.tcw/tcw-manifest.local.yaml` (where related projects are on this machine).
  Both are yours alone and never committed: `.tcw/.gitignore` ignores them.
- **An environment variable can override a setting for one project**, named
  `TCW_<KEY>__<PROJECT>`: the key's path in capitals with each `.` and `-`
  written `_`, two underscores, then the project's ID the same way. For
  example:

    ```sh
    # user.name, for the project whose ID is my-proj
    export TCW_USER_NAME__MY_PROJ="Sam Example"
    # work.jira.credentials.token-env, for the project whose ID is app
    export TCW_WORK_JIRA_CREDENTIALS_TOKEN_ENV__APP=MY_OWN_TOKEN
    ```

    `tcw project config --origin` shows where each value came from, such as
    `name: Sam Example  # my-proj, environment TCW_USER_NAME__MY_PROJ`.

- **How variables combine.** A variable whose value is a mapping merges into
  the setting key by key; a list or a single value replaces it. Where two
  variables set the same value, the more specific one wins.
- **Only the personal keys.** A personal file or a variable may set only the
  keys a person may choose for themselves; a shared key, such as
  `work.jira.site` or a store's location, is refused with
  `work.jira.site is a shared key; an environment variable cannot set it`. The
  [personal settings reference](../skills/configure/references/personal.md)
  lists the allowed keys.
- **`TCW_NO_PERSONAL_CONFIG=1`** turns off the variables as well as the
  personal files.
- **Unchanged:** `TCW_PROJECT_<ID>`, `TCW_CONFIG_DIR`, and the credential
  variables a project names (such as `TCW_JIRA_EMAIL`), which hold no `__`,
  work as in 3.x.
- **A credential variable whose name starts with `TCW_` and holds `__`** is
  read by 4.0 as an override of a setting, so it must be renamed; `tcw migrate`
  reports each one (A9).

## Where provisioning may place a clone

`tcw project provision` fetches related projects and stores that are not on
this machine, by cloning their repositories into the folders the manifests
give. A manifest fetched from someone else's repository could otherwise place
a clone anywhere, so 4.0 limits where each manifest may place one. The
[Related projects guide](guide/multi-repo.md#where-a-clone-may-be-placed)
states the rules in full; in short:

1. The active project's own two manifests, `.tcw/tcw-manifest.yaml` and
   `.tcw/tcw-manifest.local.yaml`, are trusted: an entry there may place a
   clone anywhere.
2. Any other manifest may place a clone only in a folder directly inside the
   folder holding its owner's repository, whose name does not start with `.`,
   and never when that folder is the home folder or a folder above it.
3. A hidden folder below the home folder (one with a part of its path starting
   with `.`) is refused like the home folder.
4. A manifest whose owner has a `.git` that git cannot read is refused until
   that is fixed, or the way out below is taken.
5. In a git submodule, a manifest may place a clone beside the submodule,
   inside the enclosing repository.
6. In a linked git worktree, the limit is beside the main checkout, not beside
   the worktree.
7. **The way out**: run the command as the owning project,
   `tcw -C <folder> project provision <id>`, or add an entry for the project,
   with its `repository` as well as its `path`, to the active project's own
   manifests or the owning project's `.tcw/tcw-manifest.local.yaml`, then run
   the command as that project.
8. A folder holding only `.git`, which a clone that stopped early leaves, is
   refused; finish it or remove it with git, then run again.
9. A `.tcw-staging-<hex>` folder is where a clone is made before it is moved
   into place; a run that was stopped can leave one behind. Nothing reads it,
   and it is safe to delete.

## Scripts, hooks and agent instructions

1. **Look for removed commands and flags** in the project's own instructions
   and automation: `CLAUDE.md`, `AGENTS.md`, agent memories, CI jobs, and the
   commands bound to stages, hooks and procedures in `.tcw/tcw-config.yaml`.
   `tcw migrate` names each binding that uses one (A13) and leaves it as
   written. The tables above give each replacement.
2. **A script that reads `--json` output** reads `"schema": 2` and full
   identifiers (`full-id`, `owner`). One that reads `tcw project config --origin`
   comments reads their new shape.
3. **A script that checks exit 5 for a missing related project** checks 7.
4. **A 3.x command typed into 4.0 is refused** with exit 2 and a line naming
   its replacement, printed after the usual usage error. Each line, split at
   the command, is in the table after this list. Typing the first word alone,
   or with other words after it, gives the same line. A command word on its
   own that belongs to a group gets a suggestion instead: typing new straight
   after tcw prints "did you mean `tcw work new` or `tcw project new`?".
5. **Automation that installs `tcw-cli`** keeps the version limit of step 6
   of [Before you start](#before-you-start) until the project is migrated.

| 3.x command typed   | the rest of the line           |
| ------------------- | ------------------------------ |
| `tcw init`          | is now `tcw project new`       |
| `tcw projects list` | is now `tcw project list`      |
| `tcw config show`   | is now `tcw project config`    |
| `tcw provision`     | is now `tcw project provision` |

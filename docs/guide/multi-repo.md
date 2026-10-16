# Working across repositories

A **project** is a folder holding a `tcw-config.yaml`. Several projects can work
together: a planning project and the applications it plans, a shared library
and the products built on it, packages side by side in one repository. This
guide explains how projects are connected, how one finds another on your
machine, how an item is created in another project, and how a store can live
in a different repository from the code.

Every key named here is described once, with its exact rules, in the
`configure` skill's
[`projects.md`](../../skills/configure/references/projects.md) and
[`stores.md`](../../skills/configure/references/stores.md). See also
[the work guide](work.md) and [Taxonomy and Capabilities](taxonomy-and-capabilities.md).

## A project's ID is its identity

Each project has an **ID**, written once by `tcw init --id <id>`: lower-case
letters and digits joined by `-`, such as `planning` or `app`. Everything that
refers to a project uses its ID: a work item's slug (`app/2026-10-15-refund`),
a `tcw://` link, the list of projects a ledger inherits from. A **path** only
says where a project is on one machine, and can differ from one machine to the
next without changing which project it is.

## Connecting projects: `projects`

Projects are connected in `tcw-config.yaml`, under `projects`, with up to three
kinds of entry: `parent`, `children` and `upstream`. A parent and its child
each declare the other:

```yaml
# planning/tcw-config.yaml
id: planning
projects:
    children:
        app: ../app
```

```yaml
# app/tcw-config.yaml
id: app
projects:
    parent:
        planning: ../planning
```

An entry is a path relative to the project, or a mapping that can also say
where to get the project when it is not at that path:

```yaml
id: app
projects:
    parent:
        planning:
            path: ../planning
            repository:
                url: https://example.com/acme/planning
                ref: main
```

`tcw validate` reports a parent or child connection declared on one side only,
and a command that needs the connected projects refuses until both sides
agree. The projects one command can see this way, the one it runs in and every
project connected to it, are its **family**.

`tcw projects list` prints the project's ID and every connected project's ID,
one per line, this project first; `--json` adds each one's relation, whether
it is on this machine, and its path.

## Reading a project that does not name you: `upstream`

Sometimes a two-sided connection is wrong. A public library read by a private
application must not carry the application's name in its own files. An
**upstream** entry is a connection declared by the reader alone:

```yaml
id: private-app
projects:
    upstream:
        shared-core:
            path: ../shared-core
            repository:
                url: https://example.com/acme/shared-core
```

- The upstream's own configuration never mentions its readers.
- Every project in the reader's family reaches the upstream, through the
  project that declares it.
- It is **read-only from here**: its items can be read by full slug
  (`tcw work show shared-core/<folder>`), and its taxonomy and capabilities can
  be inherited, but creating or changing anything in it is refused with exit
  code 3. Change it from its own folder.
- Its own connections are not followed, and a problem in them does not stop
  the reader.

## Where a project is on this machine: `TCW_PROJECT_<ID>`

The paths in `tcw-config.yaml` are read on every machine. When yours is laid
out differently, the environment variable `TCW_PROJECT_<ID>` (the ID in
capitals, with `-` written `_`) says where one project is on **this** machine,
and wins over the entry's `path` and `repository`:

```sh
export TCW_PROJECT_SHARED_CORE=~/src/shared-core
```

It is the only way to say this. It is never written into `tcw-config.yaml`,
and it is not personal configuration. A variable naming a folder that does not
exist is ignored in favour of the entry's `repository`; one naming a folder
that holds a different project is refused. `tcw validate` lists the variables
in effect.

Inside a **linked git worktree** (a second checkout of the same repository,
made with `git worktree add`), a relative path that leads out of the worktree
is read from the primary checkout's copy of the project, so paths written for
the primary checkout still work. A path that stays inside the worktree is left
alone.

## A project that is declared but not on this machine

A connected project may be declared and simply not be here: a fresh clone, or
a machine that has only some of the repositories. A command that has to read
it stops with exit code 5, says so, and names `tcw provision`, which obtains
it. A project that nothing here declares is a different case: reading it is
exit code 4, since there is nothing to obtain.

`tcw validate` reports a declared project that is not here as **unresolved**,
neither a warning nor an error, and keeps checking everything else.

## Slugs across projects

A work item's full slug names its project, so it can be used from anywhere in
the family: `tcw work show app/2026-10-15-refund-a-payment` reads the item from
the `planning` project. An item's `parent` and `blocked-by` can name items in
other projects the same way. Commands that change an item work only in the
item's own project, and are refused (exit code 3) elsewhere, with a message
saying where to run them.

## Creating an item in another project

`tcw work new "<title>" --project <id>` creates an item in another project's
inbox, the way a request is handed to the team that owns the code. Text piped
on standard input becomes its request, and `--priority` is the only property
that can be set; the target project sets the rest itself. Creating an item
runs no hooks, in either project.

What happens depends on where the target is:

1. **Nothing here declares it:** refused, exit code 3.
2. **It is an upstream project:** refused, exit code 3, since upstream
   projects are read-only from here.
3. **It is on this machine:**
   - with the **filesystem** backend, the item is created at the target's
     `inbox` stage. TCW first checks three things: the target's path resolves
     here, it has a work store, and that work store has no uncommitted
     changes. It checks the last by reading git's status of the store, and
     changes nothing. If any of the three fails, or the work store is not
     inside a git repository, creating the item is refused with exit code 3.
     The files it writes in the other repository are left uncommitted, and
     named on standard error, and standard output is the new item's slug;
   - with the **Jira** backend, TCW creates the ticket in the target's Jira
     inbox, using the target's own `work.jira` settings, never this project's.
     When the target's work store is present, inside a git repository and has
     no uncommitted changes, and Jira offers a move to the status set for
     the `request` stage, TCW then moves the ticket to the `request` stage
     and writes its item folder, left uncommitted; standard output is the new
     item's slug. Otherwise the ticket stays in the Jira inbox, TCW says why on
     standard error, prints the ticket's key, and exits 0.
4. **It is declared but not on this machine, and this project's entry for it
   has a `jira` block:** TCW creates the ticket in that project's Jira inbox,
   prints the ticket's key, and exits 0. The block names the target's site,
   Jira project, inbox status, credential variables and `TCW Project` field
   ([`projects.md`](../../skills/configure/references/projects.md#creating-an-item-in-another-project)).
5. **It is declared but not on this machine, with no `jira` block:** refused,
   exit code 3.

`tcw work edit <folder> --blocks <project>/<folder>` changes an item in
another project, adding this item to its `blocked-by`, and never creates one.
It follows cases 1 to 3, and is refused, exit code 3, for a project known here
only through a `jira` block.

## Stores in another repository

Each of the three stores, taxonomy, capabilities and work, is a folder:
`docs/<component>/` unless `tcw-config.yaml` says otherwise. A store can live
somewhere else, including in another repository. A common layout keeps every
project's planning in one repository while the code lives in several:

```
planning/                     repository A: planning, and every work store
├── tcw-config.yaml
├── docs/app/work/            the app's work store
└── app/                      repository B, its own clone, ignored by A
    └── tcw-config.yaml       work.path: ../docs/app/work
```

`work.path` says where the store is on this machine; a `repository` block
beside it says where to get it when it is not there:

```yaml
id: app
work:
    path: ../docs/app/work
    repository:
        url: https://example.com/acme/planning
        path: docs/app/work
```

`tcw work path`, `tcw taxonomy path` and `tcw capabilities path` print where
each store is. A store that is already where `path` says always wins; the
`repository` block is used only when it is not.

### `tcw provision`

`tcw provision` obtains what this project declares but does not have here:
each store with a `repository`, and each connected project with one, following
the projects it obtains to what they declare in turn. It is the one command
that contacts a repository address written in a file, so it prints every
address before it contacts it, and `--dry-run` prints the plan without
contacting anything.

It **clones a store or project that is missing, and never updates one that is
already here**. Running it twice does nothing the second time.

It **does not ask for anything** while it clones: not a password or token,
not an ssh key's passphrase, and not whether to trust a server it has not
met. git's prompts and Git Credential Manager's are turned off, and ssh runs
in batch mode. The one exception is an ssh command you have set yourself
(`GIT_SSH_COMMAND`, `GIT_SSH`, or git's `core.sshCommand` in your global or
system git config or given on the git command line, not the current
repository's own setting): TCW leaves it as it is, so ssh may still ask, as it would
for any clone you run. Where an answer would be needed the clone fails, and
the message gives git's reason.
So a private repository needs credentials that git can find without asking:
a credential helper that already holds them, or an ssh key loaded in an ssh
agent, with the server already in your known hosts.

### Keeping a store up to date

Keeping a store in another repository up to date is the project's job: TCW
never changes git state, so it never pulls or pushes a store. The
[git example](configuration.md#example-keeping-git-in-step-with-each-stage-change-something-your-project-adds)
in the configuration guide shows one way: its prompt text asks the agent to
pull the work store's repository too, before starting each stage, and its
`post` hook commits an item's folder in whichever repository holds it.

## Inheriting taxonomy and capabilities: `extends`

A connection alone shares nothing but work items. A project inherits another's
taxonomy or capabilities only when it says so, per axis:

```yaml
taxonomy:
    extends: [shared-core]
capabilities:
    extends: [shared-core]
```

`tcw taxonomy extends add <id>` and `tcw capabilities extends add <id>` (and
`rm`) change the list, checking first that the ID is a project connected to
this one. Inherited terms and capabilities resolve as if they were local, and
can be linked to as `tcw://<id>/T/<term>` or `tcw://<id>/C/<path>`. [Taxonomy and Capabilities](taxonomy-and-capabilities.md)
describes what inheriting means for each, and how an inherited capability is
reviewed.

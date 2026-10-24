# Connect projects, and inherit from them

A **project** is a folder holding a `tcw-config.yaml`. Three things join one
project to others: `projects` in `tcw-config.yaml` says which projects it is
connected to, the environment variable `TCW_PROJECT_<ID>` says where one of
them is on this machine, and `parents:` says whose taxonomy and capabilities
it inherits. What an inherited term or capability looks like once it resolves is
in the `taxonomy` and `capabilities` skills.

Every key here is shared: personal configuration cannot set any of them.

## The project's ID

### `id`

Shared: personal configuration cannot set it.

The project's ID: lower-case letters and digits joined by `-`, such as
`my-app`. `tcw project new --id <id>` writes it once. Other projects and every item's
full slug (`project/folder`) refer to the project by it, so it is not changed
afterwards. Paths only say where a project is; the ID says which project it
is.

## Connected projects: `projects`

```yaml
id: planning
projects:
    children:
        app: ../app
        api:
            path: ../api
            repository:
                url: https://example.com/acme/api
                ref: main
```

```yaml
id: app
projects:
    parent:
        planning: ../planning
```

- `projects` is a mapping with up to three keys: `parent`, `children` and
  `upstream`. Any other key is reported by `tcw validate`.
- Each maps a project ID to an entry. `parent` holds at most one entry;
  `children` and `upstream` may hold any number.
- An entry is either a path to the project's folder, relative to this
  project, or a mapping with `path`, `repository` and `jira`, each optional,
  described below.
- A parent and its child each declare the other: the parent lists the child,
  and the child names the parent. `tcw validate` reports a connection declared
  on one side only, and a command that needs the connected projects refuses
  until both sides agree.
- `upstream` is the exception: a connection declared by one side only. See
  below.

`tcw project list` prints this project and every project connected to it,
one ID per line; `--json` adds each one's relation, whether it is on this
machine, and its path.

### `projects.parent.*.path`

Shared: personal configuration cannot set it.

Where the parent project is, relative to this project. A bare string entry
is the same as an entry with only `path`.

### `projects.parent.*.repository`

Shared: personal configuration cannot set it.

Where to get the parent project when it is not at its `path`: the same block
a store takes (`url`, and optionally `ref`, `path` and `checkout`; see
`stores.md`). A project at its `path` always wins; `tcw project provision` makes the
copy when it is not there.

### `projects.children.*.path`

Shared: personal configuration cannot set it.

Where a child project is, relative to this project, as for the parent.

### `projects.children.*.repository`

Shared: personal configuration cannot set it.

Where to get a child project that is not at its `path`, as for the parent.

### `projects.upstream.*.path`

Shared: personal configuration cannot set it.

Where an upstream project is, relative to this project, as for the parent.

### `projects.upstream.*.repository`

Shared: personal configuration cannot set it.

Where to get an upstream project that is not at its `path`, as for the
parent.

## Upstream projects

```yaml
id: private-app
projects:
    upstream:
        shared-core:
            path: ../shared-core
            repository:
                url: https://example.com/acme/shared-core
```

An **upstream** project is one this project reads without the upstream naming
it back: its work items by full slug, such as
`tcw work show shared-core/<folder>`. Use it for a shared library, or for a
public project read by a private one that must not be named in the public
project's files.

- **Declared by the reader only.** The upstream's own configuration never
  mentions its readers.
- **Reachable from the whole family.** A project below the one that declares
  it reaches the upstream through its parents.
- **Read-only from here.** Creating an item in an upstream project, or
  changing one there, is refused with exit code 3. Change it from the
  upstream's own folder.
- **Not part of the family.** Nothing beyond the upstream's own
  `tcw-config.yaml` is read: its own parent, children and upstreams are not
  followed, and a problem in them does not stop the reader.
- **One relation per project.** A project may not declare as upstream a
  project it also reaches as a parent, child, sibling or ancestor; `tcw
  validate` reports it.

To turn a child into an upstream, move its entry from the parent's `children`
to `upstream` in one edit, then remove `parent` from the former child. In
between, `tcw validate` prints a warning, not an error, so neither project is
blocked while the second edit is made.

## Where a project is on this machine: `TCW_PROJECT_<ID>`

The paths above are written in a file every machine reads. The environment
variable `TCW_PROJECT_<ID>` (the ID in capitals, with `-` written `_`) says
where one project is on **this** machine, and wins over both the entry's
`path` and its `repository`. It is the only way to say this; it is never
written into `tcw-config.yaml`, and it is not personal configuration.

```sh
export TCW_PROJECT_SHARED_CORE=~/src/shared-core
```

Reach for it when a workspace is laid out differently from what the
configuration describes, before editing a shared file to match one machine.
A variable naming a folder that does not exist falls through to the entry's
`repository`; one naming a folder that exists but holds a different project
is refused, by `tcw project provision` too. `tcw validate` lists the variables in
effect.

## A project that is declared but not on this machine

A command that has to read a declared project that is not on this machine
exits with code 5, and says that `tcw project provision` obtains it. `tcw project provision`
clones each declared project and store that is missing, from its
`repository`, and never updates one that is already here. A project that
nothing here declares is exit code 4.

## Creating an item in another project

An item for another project is created in that project, with
`tcw -C <folder> work new "<title>"`, where `<folder>` is its folder or
`tcw://<id>.path/`. The `--project` option of `tcw work new`, which created it
from here, is removed in 4.0; in 3.x, what it did depended on where that
project was:

1. **Nothing here declares it:** refused, exit code 3.
2. **It is an upstream project:** refused, exit code 3, since upstream
   projects are read-only from here.
3. **It is on this machine:** with the filesystem backend, the item is created
   in its inbox when its work store is present and has no uncommitted changes
   (TCW reads the repository's status to check, and changes nothing). Creating
   it is refused, exit code 3, when the work store is missing, has uncommitted
   changes, or is not inside a repository whose status TCW can read. The files
   it writes are left uncommitted, and named on standard error, and standard
   output is the new item's slug. With the Jira backend, TCW creates the
   ticket in that project's Jira inbox, using that project's own `work.jira`
   block, never this one's. When that project's work store is present, inside
   a repository whose status TCW can read, has no uncommitted changes, and Jira
   offers a move to the status set for the `request` stage, TCW then moves
   the ticket to the `request` stage and writes its item folder there, left
   uncommitted, and standard output is the new item's slug.
   Otherwise the ticket stays in the Jira inbox, TCW says why on standard
   error, prints the ticket's key, and exits 0. Until the files a filing
   wrote are recorded in that project's version control, the next filing
   there is refused, or, with Jira, stays in the inbox.
4. **It is declared but not on this machine, and its entry here has a `jira`
   block:** TCW creates a ticket in the inbox status the block names, prints
   the ticket's key, and exits 0.
5. **It is declared but not on this machine, with no `jira` block:** refused,
   exit code 3.

The `--blocks` option of `tcw work edit`, removed in 4.0, changed an existing
item in another project and never created one. It followed cases 1 to 3, and
was refused, exit code 3, for a project known here only through a `jira` block.
A blocker is recorded on the blocked item, in its own project, with
`tcw -C <folder> work edit <item> --blocked-by <full id>`.

## A connected project's `jira` block

An entry may carry a `jira` block: what TCW needs to create a ticket in that
project when the project itself is not on this machine (case 4 above). When
the project is on this machine, its own `tcw-config.yaml` is read instead.
The block is written in this project's file, so the site and the credential
names always come from the same file.

```yaml
projects:
    children:
        billing:
            path: ../billing
            jira:
                site: https://example.atlassian.net
                project: BILL
                inbox-status: Inbox
                credentials:
                    email-env: TCW_JIRA_EMAIL
                    token-env: TCW_JIRA_TOKEN
                fields:
                    project: TCW Project
```

Every key of the block is required, and each follows the rule of the
matching `work.jira` key in `jira.md`. Delegating into an upstream project is
refused, so a `jira` block on an upstream entry is accepted but never used.

### `projects.parent.*.jira.site`

Shared: personal configuration cannot set it.

The parent project's Jira site, `https://<host>`.

### `projects.parent.*.jira.project`

Shared: personal configuration cannot set it.

The key of the parent project's Jira project.

### `projects.parent.*.jira.inbox-status`

Shared: personal configuration cannot set it.

The status of the parent project's Jira inbox, where the new ticket is put.

### `projects.parent.*.jira.credentials.email-env`

Shared: personal configuration cannot set it.

The name of the environment variable holding the email address to create the
ticket with. Unlike `work.jira`'s credential names, it cannot be changed in a
personal file.

### `projects.parent.*.jira.credentials.token-env`

Shared: personal configuration cannot set it.

The name of the environment variable holding the API token, as for
`email-env`.

### `projects.parent.*.jira.fields.project`

Shared: personal configuration cannot set it.

The name of the parent project's TCW Project field, which TCW fills with that
project's ID.

### `projects.children.*.jira.site`

Shared: personal configuration cannot set it.

A child project's Jira site, as for the parent.

### `projects.children.*.jira.project`

Shared: personal configuration cannot set it.

A child project's Jira project key, as for the parent.

### `projects.children.*.jira.inbox-status`

Shared: personal configuration cannot set it.

A child project's Jira inbox status, as for the parent.

### `projects.children.*.jira.credentials.email-env`

Shared: personal configuration cannot set it.

The email variable for a child project, as for the parent.

### `projects.children.*.jira.credentials.token-env`

Shared: personal configuration cannot set it.

The token variable for a child project, as for the parent.

### `projects.children.*.jira.fields.project`

Shared: personal configuration cannot set it.

A child project's TCW Project field, as for the parent.

### `projects.upstream.*.jira.site`

Shared: personal configuration cannot set it.

Accepted on an upstream entry, as for the parent, and never used.

### `projects.upstream.*.jira.project`

Shared: personal configuration cannot set it.

Accepted on an upstream entry, as for the parent, and never used.

### `projects.upstream.*.jira.inbox-status`

Shared: personal configuration cannot set it.

Accepted on an upstream entry, as for the parent, and never used.

### `projects.upstream.*.jira.credentials.email-env`

Shared: personal configuration cannot set it.

Accepted on an upstream entry, as for the parent, and never used.

### `projects.upstream.*.jira.credentials.token-env`

Shared: personal configuration cannot set it.

Accepted on an upstream entry, as for the parent, and never used.

### `projects.upstream.*.jira.fields.project`

Shared: personal configuration cannot set it.

Accepted on an upstream entry, as for the parent, and never used.

## Inheriting taxonomy and capabilities: `parents:`

```yaml
id: app
parents:
    - shared-core
    - id: planning
      inherit: [capabilities]
```

A project inherits taxonomy and capabilities from the parents listed under
`parents:` in its `.tcw/tcw-config.yaml`, and from nothing else. Each entry is
a project ID, or a mapping with `id` and `inherit`. `inherit` says what that
parent passes down: `all` (the default), `none`, or a list drawn from
`taxonomy`, `capabilities` and `config`. Inheritance goes through every level:
a parent's own parents pass down to this project too, as far as each link's
`inherit` allows, without being listed here. The order of the list decides the
project's load order (the order in which TCW reads its parents), which
matters only where two parents that do not inherit from each other both have
an entry at one path: the one later in the load order is used, and
`tcw validate` warns.

To change one inherited entry, the project puts its own entry at the same
path, holding only what it changes; the `taxonomy` and `capabilities` skills
say how.

Before TCW 4.0, each of the taxonomy and capabilities sections kept its own
list of the projects it inherited from, edited by commands of its own. Both
the lists and the commands are gone. A project's own `.tcw/tcw-config.yaml`
that still holds such a list is an error that names `parents:`: name each
project it listed under `parents:`, with an `inherit` that includes the axis,
and delete the list.

Inheritance belongs to the project, not to the store: two projects whose
store `path` is the same folder can inherit differently. `tcw validate` also
reports a `docs/taxonomy/config.yaml` or `docs/capabilities/.config.yaml` left
from before TCW 2.5.0, which is not read; delete it, and name under `parents:`
any project it listed.

After editing any of this, run `tcw validate`, then `tcw project provision` if a
`repository` was added.

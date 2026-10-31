# Relate projects, and say where they are

A **project** is a folder holding `.tcw/tcw-config.yaml`. Two kinds of
setting join a project to others, and they behave differently:

- **Relations**, in `.tcw/tcw-config.yaml`: `parents:` names the projects
  this one builds on and takes things from, and `children:` names the
  projects that build on it. Both name projects by ID only. They are what
  every store keeps, whatever holds it, and they are the same on every
  machine.
- **Locations**, in the project's **manifests** (two files in `.tcw/` that
  say where other projects are), or in the environment variable
  `TCW_PROJECT_<ID>`. They are about folders on this machine only, and can
  differ from one machine to the next. Listing a project in a manifest does
  not relate it to this one.

How TCW uses these, and the order in which it looks for a project's folder,
are in the guide [Related projects](../../../docs/guide/multi-repo.md) in the
TCW repository. This document gives each setting's exact shape. What an
inherited taxonomy term or capability looks like once it resolves is in the
`taxonomy` and `capabilities` skills.

## The project's ID

### `id`

Shared: personal configuration cannot set it.

The project's ID: lower-case letters and digits joined by `-`, such as
`my-app`. `tcw project new --id <id>` writes it once. Other projects, parent
links, manifests and every object's **full identifier** (the name that says
which project owns an object, such as `my-app.work/2026-10-01-add-login`)
refer to the project by it, so it is not changed afterwards. A path only says
where a project is; the ID says which project it is.

## Parent links

### `parents`

Shared: personal configuration cannot set it.

The projects this one builds on, in order. Each entry is a project ID, or a
mapping with `id` and `inherit`:

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
`config`. `config` passes `work.tags` and `work.jira`, and never
`work.backend`; the guide [Configuration](../../../docs/guide/configuration.md)
says how those keys merge. A parent's own parents pass down too, through every
level, without being listed here, as far as each link's `inherit` allows. A
parent with `inherit: none` passes nothing and is still part of the project's
family.

- An entry may hold only `id` and `inherit`. A project listed twice, an
  `inherit` value outside the ones above, and an unknown key are errors that
  `tcw validate` names, such as
  `parents[1].inherit: 'tags' is not one of taxonomy, capabilities, config`.
- The order of the list sets the project's **load order**, the order in
  which TCW reads its ancestors where two of them have something at the same
  place; a parent listed later wins over one listed earlier, and the project
  itself wins over all of them. `tcw project info` prints the load order. The
  guide [Related projects](../../../docs/guide/multi-repo.md) gives its rules,
  the warning when no order fits every project, and the error for a loop.
- A parent never has to name its children. No command changes the list:
  edit the file, then run `tcw validate`.

To change one inherited taxonomy entry or capability, the project puts its own
entry at the same path, holding only what it changes; the `taxonomy` and
`capabilities` skills say how.

### `children`

Shared: set it in `.tcw/tcw-config.yaml`. The one exception is that the
project's own personal file, `.tcw/tcw-config.local.yaml`, may also list
children.

The projects that name this one as a parent, by ID, so that commands run here
can reach them, for example with `--scope down`. The two lists are combined,
and a child listed in both files is accepted:

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
    - extra
```

- Each entry is a project ID. A project listed twice in one file, or the
  project listing itself (`children[0]: 'workspace' lists itself as a child`),
  is an error.
- **A listed child must name this project among its parents.** One that does
  not is an error that `tcw validate` and every command reading the family
  report, with exit code 1:
  `'extra' is listed as a child of 'workspace' but does not name 'workspace' among its parents`.
  The message names `.tcw/tcw-config.yaml` even for a child listed in the
  personal file.
- `tcw project info` marks a child from the personal file `(personal)`.
- The user-wide file cannot list children, since it applies to every
  project; the command stops with exit code 1 and says
  `children may be listed only in this project's own files, .tcw/tcw-config.yaml or .tcw/tcw-config.local.yaml`.
  An override variable cannot set `children` either.

## Where a related project is: the manifests

Each project can have two manifests in its `.tcw/` folder:

- `.tcw/tcw-manifest.yaml`, shared with everyone who works on the project; a
  path in it is relative to the project's folder;
- `.tcw/tcw-manifest.local.yaml`, personal to this machine and never shared
  (the `.tcw/.gitignore` that `tcw project new` writes leaves it out); a path
  in it may also be absolute or start with `~`.

```yaml
# app/.tcw/tcw-manifest.yaml
tcw-version: 4.0.0
projects:
    shared: packages/shared
    core:
        path: ../core
        repository: https://example.com/acme/core#release
    server:
        path: ../platform/apps/server
        repository: https://example.com/acme/platform
        subfolder: apps/server
```

A manifest holds `tcw-version` and `projects`, and nothing else.
`projects` maps a project ID to an **entry**, written as a path alone or as a
mapping of these keys:

- `path`, required: the folder holding that project's `.tcw/`.
- `repository`, optional: the address `tcw project provision` clones the
  project from when it is not on this machine, written `<url>` or
  `<url>#<branch>`. The text after the first `#` names the version to
  check out, such as `release` above; without it, the version the remote
  repository names as its default is used. `tcw project provision --dry-run`
  shows each one as `<url> at <name>`.
- `subfolder`, optional and only with `repository`: where the project sits
  inside its repository. It must be how `path` ends, since the repository is
  cloned into `path` with `subfolder` removed: in the `server` entry, into
  `../platform`, with the project at `../platform/apps/server`.

**A manifest with any problem is not used at all**, and `tcw validate` names
the problem, such as:

```text
error: .tcw/tcw-manifest.yaml: has no tcw-version; a manifest starts with 'tcw-version: 4.0.0'
error: .tcw/tcw-manifest.yaml: projects.core: subfolder is where the project sits inside its repository, so it needs a repository
```

An absolute path, or one starting with `~`, in the shared manifest is refused
with `must be relative to this project's root: this file is shared by every machine; an absolute path or one starting with '~' goes in .tcw/tcw-manifest.local.yaml`.

`tcw project path <id>` prints the folder TCW found for a project, and
`tcw project list --json` says, for each related project, whether a manifest
(and which one), `TCW_PROJECT_<ID>` or the search found it.

### `TCW_PROJECT_<ID>`

The environment variable `TCW_PROJECT_<ID>` (the ID in capitals, with `-`
written `_`, such as `TCW_PROJECT_SHARED_CORE` for `shared-core`) names one
project's folder on this machine, and is read before any manifest:

```sh
export TCW_PROJECT_SHARED_CORE=~/src/shared-core
```

It is not a configuration key and not personal configuration: it is never
written in a file. Reach for it, or for an entry in
`.tcw/tcw-manifest.local.yaml`, when this machine's folders are laid out
differently from what the shared manifest says, before editing a shared file
to suit one machine. With neither a variable nor an entry, TCW searches the
folders next to the project and the folders enclosing it; the guide gives
the search's limits.

## Fetching a related project

A command that needs a related project that is not on this machine says so
and names `tcw project provision <id>` when the deciding manifest entry gives
a `repository`. `tcw project provision` clones each missing project and store
it can, and never updates one that is already here. A manifest other than the
active project's own two may place a clone only in a folder directly inside
the folder holding its owner's repository, never in a hidden folder and never
in or above the home folder; `tcw -C <folder> project provision <id>`, run in
the owner's folder, or an entry with a `repository` in that project's own
`.tcw/tcw-manifest.local.yaml`, is the way out. The guide
[Related projects](../../../docs/guide/multi-repo.md) has the cases this
sentence leaves out and the exit codes.

## A project moved over from 3.x

In 3.x, related projects were written under a `projects:` key with folder
paths, as parent, children or `upstream` entries, and each of the taxonomy
and capabilities sections listed the projects it inherited from under
`extends`. 4.0 refuses both as errors that name `parents:`: name each parent
by ID under `parents:` (a library read by other projects becomes their
parent), list the children under `children:`, and say where each project is
in a manifest. `tcw migrate` makes these changes to a 3.x project's files;
the migration guide, `docs/migration-guide-3.X-to-4.0.0.md` in the TCW
repository, maps every 3.x name to its replacement.

## After editing any of this

Run `tcw validate`. It reports a malformed entry or manifest, a child that
does not name its parent, and a related project it could not reach, which it
lists as unresolved and does not count as an error. Then run
`tcw project provision` if a `repository` was added, and `tcw project info`
to see the parents, children and load order that resulted.

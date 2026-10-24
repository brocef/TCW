# Choose where a component's store lives

Each of TCW's three components (taxonomy, capabilities and work) keeps its
entries in a **store**: a folder of files. By default the taxonomy store is
`docs/taxonomy`, the capabilities store `docs/capabilities`, and the work
store `docs/work`, all inside the project. A project that configures nothing
keeps those defaults.

Two keys per component say where its store is: `<component>.path`, where it
is on this machine, and `<component>.repository`, how any machine gets it. The
taxonomy and capabilities keys are described here; the work store's two keys,
[`work.path`](work.md#workpath) and [`work.repository`](work.md#workrepository),
are in `work.md` and follow the same rules. All six are shared: personal
configuration cannot set them.

## A different folder

```yaml
id: my-project
taxonomy:
    path: ../shared-docs/taxonomy
capabilities:
    path: ../shared-docs/capabilities
work:
    path: ../planning/docs/work/my-project
```

The rules for every `<component>.path`:

- The folder may be in another repository.
- It is one of two things: **a path relative to the project's folder**, such
  as `../shared-docs/taxonomy`, or **a `.path` address**, a folder named
  through a project's ID: `tcw://<id>.path/<folder>` is a folder inside that
  project's folder, and `tcw://<id>.<component>.path/<folder>` a folder
  inside that project's own store for that component. TCW finds the named
  project the way it finds any related project (`projects.md`), so the
  address keeps working where the folders are laid out differently.
- **An absolute path, or one starting with `~`, is refused**, since every
  machine reads `.tcw/tcw-config.yaml`. A folder that sits elsewhere on one
  machine is placed by an entry in `.tcw/tcw-manifest.local.yaml` for the
  project that holds it, and named here by a `.path` address:

    ```text
    tcw work path: .tcw/tcw-config.yaml: work.path: must be a path relative to the project, or a tcw:// .path address such as tcw://<project>.path/<folder>; a folder that sits elsewhere on this machine is placed by an entry in .tcw/tcw-manifest.local.yaml
    ```

- A symbolic link is followed. When the project is
  opened from a linked worktree (a second working folder of the same
  repository), a relative path that leads out of the repository is read from
  the main checkout's copy of the project instead, and one that stays inside
  the repository is read in the folder the project was opened from.
- **Stores never nest or share a folder**, within one project or across
  related projects, and their locations may not loop, such as `app`'s
  `work.path` naming a folder in `core`'s work store while `core`'s names one
  in `app`'s. `tcw validate` reports a nested or shared store as an error,
  and every command that opens a store refuses a loop, naming it. The guide
  [Related projects](../../../docs/guide/multi-repo.md) in the TCW repository
  shows both messages.
- A store path is about files only. The project's ID and its configuration
  stay with the project.
- **Changing a path moves nothing.** Entries in the old folder stay there and
  TCW does not read them. Move them yourself, then change the path.

`tcw project new` takes `--work-path <path>`, `--taxonomy-path <path>` and
`--capabilities-path <path>`, each a relative path; each writes the key and
creates the store there. A `.path` address is written into
`.tcw/tcw-config.yaml` by hand once the project exists. Run without them in a
project that already exists, `tcw project new` uses the paths already in
`.tcw/tcw-config.yaml`.

### `taxonomy.path`

Shared: personal configuration cannot set it.

The folder holding the taxonomy store, `docs/taxonomy` by default.

### `capabilities.path`

Shared: personal configuration cannot set it.

The folder holding the capabilities store, `docs/capabilities` by default.

## Where a store comes from

A store can also say where it comes from, so a machine that does not have it
can get it. A store that is **already here** always wins: the declaration is
used only when the local folder is absent, so one configuration serves both a
machine that has the folder and a fresh copy that does not.

```yaml
work:
    path: ../planning/docs/work/my-project
    repository:
        url: https://example.com/acme/planning
        ref: main
        path: docs/work/my-project
        checkout: ~/src/planning
taxonomy:
    repository:
        url: https://example.com/acme/planning
        path: docs/taxonomy
```

The block, the same for all three stores:

- `url`: the repository to copy. Required.
- `ref`: which version of it to check out; by default, the one the remote
  repository names as its default.
- `path`: the store's folder inside the repository; by default its root.
- `checkout`: where to put the copy on this machine; by default a cache
  folder.

The block stays on the store: it is not a manifest entry, which says where a
whole project is (`projects.md`). `tcw project provision --component <component>`
makes the copy of that store when it is missing, and `tcw project provision`
alone makes every missing store and project; neither updates one that is
already here, and `--dry-run` prints what each would contact first. Until the
copy is made, a command that needs the store stops with exit code 1 and names
that command. Keeping a copy up to date is the
project's own job: TCW never changes the copy once it exists. The
configuration guide's
[example](../../../docs/guide/configuration.md#example-keeping-git-in-step-with-each-stage-change-something-your-project-adds)
shows one way, with an instruction in each stage's prompt.

### `taxonomy.repository`

Shared: personal configuration cannot set it.

Where the taxonomy store comes from, in the block above.

### `capabilities.repository`

Shared: personal configuration cannot set it.

Where the capabilities store comes from, in the block above.

## What a project inherits is not a store key

Which projects a project inherits taxonomy and capabilities from is not set
beside `path` and `repository`: it comes from the project's parent links
(`parents:` in `.tcw/tcw-config.yaml`), each parent passing the axes its
`inherit` names, as `projects.md` describes. Because inheritance belongs to the
project rather than to the store, two projects whose `path` is the same folder
may inherit differently.

## After changing a store's location

1. Run `tcw validate`. It names a malformed `repository` block by its key.
2. Where a `repository` block was added, run `tcw project provision` to get the store.
   Never run `tcw project new` to get past a declared store that is missing here:
   that would create a second, empty store beside the real one.
3. Confirm with `tcw work path`, `tcw taxonomy path` or
   `tcw capabilities path`, which print the folder each store resolved to.

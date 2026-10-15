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
- A relative path is read from the project's own folder. When the project is
  opened from a linked worktree (a second working folder of the same
  repository), a relative path that points outside that folder is read from
  the main checkout's copy of the project instead. Absolute paths and
  symbolic links are accepted.
- A store path is about files only. The project's ID and its configuration
  stay with the project.
- **Changing a path moves nothing.** Entries in the old folder stay there and
  TCW does not read them. Move them yourself, then change the path.

`tcw init` takes `--work-path <path>`, `--taxonomy-path <path>` and
`--capabilities-path <path>`; each writes the key and creates the store
there. Run without them, `tcw init` uses the paths already in
`tcw-config.yaml`.

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

`tcw provision` makes the copy of every declared store and project that is
missing, and never updates one that is already here. `tcw provision --dry-run`
prints what it would contact first. Keeping a copy up to date is the
project's own job: TCW never changes the copy once it exists.

### `taxonomy.repository`

Shared: personal configuration cannot set it.

Where the taxonomy store comes from, in the block above.

### `capabilities.repository`

Shared: personal configuration cannot set it.

Where the capabilities store comes from, in the block above.

## The other per-component key: `extends`

`taxonomy.extends` and `capabilities.extends` sit beside `path` and
`repository`, and name the projects whose entries this project inherits. They
are described in `projects.md`, with the connections they depend on, and are
changed with `tcw taxonomy extends add <id>` and
`tcw capabilities extends add <id>`, not by hand. Because `extends` belongs to
the project rather than to the store, two projects whose `path` is the same
folder may inherit differently.

## After changing a store's location

1. Run `tcw validate`. It names a malformed `repository` block by its key.
2. Where a `repository` block was added, run `tcw provision` to get the store.
   Never run `tcw init` to get past a declared store that is missing here:
   that would create a second, empty store beside the real one.
3. Confirm with `tcw work path`, `tcw taxonomy path` or
   `tcw capabilities path`, which print the folder each store resolved to.

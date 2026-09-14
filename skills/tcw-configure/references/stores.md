# Choose where a component's store lives

Each component keeps its entries in a store: a folder of files. By default the
taxonomy store is `docs/taxonomy`, the capabilities store `docs/capabilities`,
and the work store `docs/work`, all inside the project. A project that
configures nothing keeps those defaults.

## A different folder: `<component>.path`

```yaml
id: my-project
taxonomy:
    path: ../shared-docs/taxonomy
capabilities:
    path: ../shared-docs/capabilities
work:
    path: ../orchestrator/docs/work/my-project
```

- `taxonomy.path`, `capabilities.path` and `work.path` each name the folder that
  component's store lives in. The folder may be in another Git repository.
- A relative path is anchored to the project's own directory. Inside a linked
  Git worktree, a relative path that points outside the worktree is anchored to
  the primary checkout's copy of the project instead. Absolute paths and symbolic
  links are supported.
- A store path is about files only. The project's identity, its lifecycle
  bindings and its code worktrees stay with the project.

**Setting a path when the store is created.** `tcw init` takes
`--work-path <path>`, `--taxonomy-path <path>` and `--capabilities-path <path>`,
and `tcw work init` takes `--path <path>`. Each writes the key and creates the
store there. For the work store, if a default `docs/work` already exists and
holds no items, init replaces it; if it holds anything, init refuses.

**Changing a path later does not move existing items.** Editing `work.path` (or
either of the other two) only changes where TCW looks. Entries already in the
old folder stay there, and TCW ignores them. A store that isn't empty is never
moved automatically: move the existing entries yourself, update the path, then
run the component's `init` if the new folder has no store yet.

## Where a store comes from: `<component>.repository`

**The work store can also declare where it comes from.** `work.repository` in
`tcw-config.yaml` names the repository holding the store (`url`, and optionally
`ref`, `path` within it, and a local `checkout`), which is the portable half:
`work.path` says where it is on one machine, `repository` says how any machine
gets it. Resolution prefers a store that is **already here** — the declaration
answers only when the local one is absent, so one config serves a laptop that has
the folder and a fresh clone that does not.

```yaml
work:
    path: ../orchestrator/docs/work/my-project # optional; where it is here
    repository:
        url: https://github.com/me/orchestrator.git
        ref: main # optional (default: the remote's default branch)
        path: docs/work/my-project # optional (default: the repository root)
        checkout: ~/src/orchestrator # optional (default: a cache folder)
taxonomy:
    repository: # the same block, per component
        url: https://github.com/me/orchestrator.git
        path: docs/taxonomy
```

`taxonomy.repository` and `capabilities.repository` take the same block. A work
store fetched this way pushes each transition back to its repository; to keep
transitions local, see `work.publish-transitions` in `work.md`.

## After changing a store's location

1. Run `tcw validate`. It names a malformed `repository` block by its config
   line.
2. Where a `repository` block was added, run `tcw provision` to fetch the store.
   `tcw provision --dry-run` prints what it would contact first. Never run
   `tcw init` to get past a declared store that is missing here; that creates a
   second, empty store beside the real one.
3. Confirm with `tcw work path`, `tcw taxonomy path` or `tcw capabilities path`,
   which print the folder each store resolved to.

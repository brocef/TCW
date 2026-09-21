# Connect and inherit from other projects

Three settings join a project to others: `connected-projects` in
`tcw-config.yaml` says which projects it is connected to, `TCW_PROJECT_<ID>` says
where one of them is on this machine, and `extends` says whose taxonomy or
capabilities it inherits. What an inherited term or capability looks like once
it resolves is in the `taxonomy` and `capabilities` skills.

## `connected-projects`

```yaml
id: orchestrator
connected-projects:
    children:
        project-a: ../project-a
        project-b:
            path: ../project-b # optional; where it is here
            repository:
                url: https://github.com/me/project-b.git
                ref: main
```

```yaml
id: project-a
connected-projects:
    parent:
        orchestrator: ../orchestrator
```

- `connected-projects` is a mapping with two keys, `parent` and `children`. Any
  other key is reported by `tcw validate`.
- Each of the two is a mapping from a project id to an entry. `parent` holds at
  most one entry; `children` may hold any number.
- An entry is either a locator (a path to the project's folder, relative to this
  project) or a `{path, repository}` block, where `repository` takes the same
  keys as a store's repository block in `stores.md`.
- Connections are declared from both sides: the parent lists the child, and the
  child names the parent. `tcw validate` reports a connection declared on only
  one side, and commands that need a valid project graph, such as
  `tcw taxonomy extends add`, refuse until both sides agree.

A `repository` block answers only when the project is not found at its `path`.

**A connected project declares a repository the way a store does.** An entry under
`connected-projects` may be `{path, repository}` instead of a bare locator, with
the ladder a store uses — the project at `path` wins when it is here — so a checkout that
cloned one repository can still resolve `extends`, cross-node refs and the
topology. Declarations follow the graph: each config names only its own edges.

After editing, run `tcw validate`, then `tcw provision` if a `repository` block
was added; it fetches the connected projects this machine does not have, and
follows their connections in turn.

## `TCW_PROJECT_<ID>`: where a project is on this machine

A locator and a declared repository are both written in a file every machine
reads.

**One rung sits above both: `TCW_PROJECT_<ID>`** (the id uppercased, `-` as `_`),
naming where that project is on *this* machine. It wins over the declared path
and the declaration, because the case it exists for is a path that resolves to
the *wrong* node — a workspace laid out flat where the config describes it
nested, which is what makes `tcw provision` fetch a second copy of a project the
machine already has. Reach for it before editing a shared config to match one
machine. It reaches component stores too: a store whose
declared repository is a project this variable located is read there. A variable naming a path that is not here is not an error and falls
through to `repository`, so one set can serve a whole environment; one naming a
directory that is present and wrong is refused — by `tcw provision` too, which
stops before contacting anything rather than falling back to a fetch.
`tcw validate` lists the ones in effect — if a graph resolves for a reason no
config explains, that list is where to look.

Set it in the shell or environment that runs `tcw`, for example
`export TCW_PROJECT_PROJECT_A=~/src/project-a`. It is never written into
`tcw-config.yaml`.

## `extends`: inheriting taxonomy or capabilities

Import another registered project's taxonomy explicitly:
`tcw taxonomy extends add <project-id>` (`rm <project-id>` drops it). The ID must
be reachable through the validated project graph; a connection alone does not
imply inheritance.

A project can explicitly inherit another registered project's capabilities with
`tcw capabilities extends <project-id>` (`--rm` to drop). The source must be
reachable in the registered graph, but a connection alone does not imply
inheritance.

- `extends` is a list of project ids, one list per component, and both live in
  `tcw-config.yaml` beside that component's `path` and `repository`:

  ```yaml
  taxonomy:
      extends:
          - acme-shared
  capabilities:
      extends:
          - acme-shared
  ```

- **Inheritance belongs to the project, not to the store.** Two projects whose
  `taxonomy.path` points at the same folder can inherit differently, and a
  shared folder imposes nothing on what reads it.
- Change it only through the two commands above, which check the project id
  before writing. Legacy alias or path maps fail closed. Writing the key changes
  only its own lines of `tcw-config.yaml`; a file the command cannot edit in
  place (a section in braces, for instance) is refused with the hand edit to
  make, never rewritten.
- Projects written for TCW 2.x kept these lists inside the store, in
  `docs/taxonomy/config.yaml` and `docs/capabilities/.config.yaml`. Those files
  are no longer read; `tcw taxonomy check`, `tcw capabilities check` and
  `tcw validate` report one until it is deleted — see
  [the 2.5.0 migration guide](../../../docs/migration-guide-2.4.X-to-2.5.0.md).
- Run `tcw taxonomy check` or `tcw capabilities check` afterwards; both report
  an inheritance cycle.

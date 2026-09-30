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

- `connected-projects` is a mapping with up to three keys, `parent`,
  `children` and `upstream`. Any other key is reported by `tcw validate`.
- Each is a mapping from a project id to an entry. `parent` holds at most one
  entry; `children` and `upstream` may hold any number.
- An entry is either a locator (a path to the project's folder, relative to this
  project) or a `{path, repository}` block, where `repository` takes the same
  keys as a store's repository block in `stores.md`.
- Connections are declared from both sides: the parent lists the child, and the
  child names the parent. `tcw validate` reports a connection declared on only
  one side, and commands that need a valid project graph, such as
  `tcw taxonomy extends add`, refuse until both sides agree.
- `upstream` is the one exception: a one-way, read-only connection, declared
  only by the reader. See below.

A `repository` block answers only when the project is not found at its `path`.

**A connected project declares a repository the way a store does.** An entry under
`connected-projects` may be `{path, repository}` instead of a bare locator, with
the ladder a store uses — the project at `path` wins when it is here — so a checkout that
cloned one repository can still resolve `extends`, cross-node refs and the
topology. Declarations follow the graph: each config names only its own edges.

## `upstream`: a project you read but do not write

```yaml
id: proposit-app-repo
connected-projects:
    upstream:
        proposit-core:
            path: ../proposit-core
            repository:
                url: https://github.com/example/proposit-core.git
                ref: main
```

An upstream project is one this project reads — its taxonomy and capabilities
through `extends`, its work items by qualified reference such as
`tcw work show proposit-core/<slug>` — without the upstream naming it back. Use it
for a shared library, or a public project read by a private one that must not
be named in the public project's files.

- **Declared by the reader only.** The upstream's own config is unchanged and
  never mentions its readers. Its entry takes the same forms as `children`.
- **Reachable from the reader's whole family.** A package below the declarer
  reaches the upstream through its parents, as it would a child of theirs.
- **Read-only from here.** Anything that changes an item or runs its project's
  scripts is refused for an upstream item — `start`, `edit`, `drop`, the stage
  and procedure verbs, `delegate`, and every changing route of
  `tcw serve --include-descendants` (403). Change it from the upstream's own
  checkout. The rule: a project is writable from here only when it is reached
  through `parent` and `children` links alone.
- **Not part of the family.** Nothing beyond the upstream's own config is read:
  its parent, children and upstreams are not followed, and a problem in its
  graph does not block the reader. It is not listed by `list
  --include-descendants`, not validated with the family, not rolled up by
  `reconcile`, and not on the web board. `tcw work nodes` shows it under
  `upstream (read-only):`, with the project that declared it.
- **One or the other.** A project may not declare as upstream something it
  also reaches as a parent, child, sibling or ancestor; `tcw validate` reports
  it. Several projects may declare the same upstream: entries that resolve to
  the same folder are one project, and ones that resolve to different folders
  are a `duplicate project id` problem naming each declarer.

**Moving an existing child to upstream.** Move its entry from the parent's
`children` to `upstream` in one edit, then remove `parent` from the former
child. In between, `tcw validate` prints a warning — the former child still
names a parent that now reads it as an upstream — instead of a problem, so
neither repository is blocked while they catch up. Doing it the other way
round (the child drops `parent` first) fails as a `nonreciprocal connection`.
Before the former child drops its parent, check what it inherited: an
incomplete `work.tracker` block has nothing left to inherit from, and
`tcw validate` says so.

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

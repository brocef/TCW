# Lifecycle bindings

A node may bind its own agent skills or shell commands to any stage or transition
id, in `tcw-config.yaml`:

```yaml
work:
    lifecycle:
        stages:
            spec: [{ skill: superpowers:brainstorming }]
        transitions:
            complete:
                pre: [{ command: "pytest -q" }]
```

A binding declares one **kind** explicitly — a bare string is rejected, never
guessed at. Declaration order is significant. `tcw validate` rejects unknown ids,
malformed shapes, blank or duplicated references, a kind used in a position that
does not allow it, and a malformed `when:`.

Which kinds each position allows, how several bindings combine, and what `when:`
can test are in the table under "Roles, kinds, and conditions" in the `tcw-work`
skill's `hooks.md`. That document also says how bindings run. Run
`tcw work lifecycle` to see what a node has bound once you have changed it.

A bare list under a stage id still means `prompt:`. It is the one place
`command:` is accepted in a prompt position — the explicit `prompt:` key rejects
it and points at `generate:` — because the legacy shape predates the distinction
and cannot be renamed.

`tcw-config.yaml` is a file in the user's own repository and is trusted exactly
as much as any other file there. This is not a sandbox.

## Hook limits: `timeout` and `output-cap`

Two more keys sit beside `stages` and `transitions` under `work.lifecycle`:

```yaml
work:
    lifecycle:
        timeout: 300       # seconds
        output-cap: 65536  # bytes
```

- **`work.lifecycle.timeout`** is how many seconds a `command:` check or a
  `generate:` script may run before it is stopped. It must be a positive whole
  number; the default is 300.
- **`work.lifecycle.output-cap`** is the most a `generate:` script may print, in
  bytes. Past it the script is stopped and nothing it printed is used. It must
  be a positive whole number; the default is 65536 (64 KiB). It is a separate
  limit from the 64 KiB cap on the item body the script receives on its standard
  input.

`tcw validate` reports either key when its value is not a positive whole number
(`true` and `false` do not count), and the default is used in the meantime. Any
other key under `work.lifecycle` is reported as unknown.

## The Definition of Done: `dod.yaml`

`tcw work complete --resolution done` prints a checklist and refuses until it is
re-run with `--confirm`. The built-in checklist has five lines: `tests pass`,
`docs synced`, `capabilities reconciled`, `reviewed`, `version offered`.

To set a project's own checklist, write `dod.yaml` at the root of the work store
(`docs/work/dod.yaml` unless `work.path` puts the store elsewhere):

```yaml
- tests pass
- docs synced
- originating GitHub issue answered and closed, if the item came from one
```

- A plain list of strings, or a mapping with a `checklist:` key holding that
  list.
- The file **replaces** the built-in list; it does not add to it. A line left out
  is dropped from every completion, with no warning.
- The checklist is printed, never enforced, and is not stored on the completed
  item. A discard (`wontfix`, `duplicate`, `superseded`) prints no checklist.
- A file that is missing, or holds some other shape, means the built-in five
  apply. `tcw validate` reports a `dod.yaml` that is not valid YAML.

## How transitions commit and where they land

All four keys below live under `work` in `tcw-config.yaml`. What each one does
while items move is described in the `tcw-work` skill's `transitions.md` and
`commands.md`; this is how to set them.

```yaml
work:
    auto-commit-transitions: true
    trunk-branch: main
    publish-transitions: true
    retain:
        completed: true
        discarded: false
```

- **`work.auto-commit-transitions`** — `true` or `false`, default `true`. When
  `true`, every transition commits its own status move. Set it to `false` to
  commit the moves yourself. A value that is not `true` or `false` is read as the
  default, and `tcw validate` does not report it.
- **`work.trunk-branch`** — a branch name, unset by default. When set, a
  transition made on some other branch prints a warning and still commits where
  it is. It never checks anything out. A value that is not text, or is blank, is
  read as unset.
- **`work.publish-transitions`** — `true` or `false`, default `true`. It matters
  only for a work store that `tcw provision` fetched from a declared repository:
  there a transition refreshes before moving and pushes after committing. Set it
  to `false` to keep transitions local. A value that is not `true` or `false` is
  read as the default.
- **`work.retain`** — a mapping from `completed` and `discarded` to `true` or
  `false`, both `true` by default. A status set to `false` removes an item from
  the tree after it lands there, leaving a graveyard entry that names the commit
  holding it. Setting `false` is refused at transition time while that status's
  folder is gitignored, and the refusal names the ignore rules to drop. Before
  turning it on for a board that already has resolved items, backfill the
  graveyard with `tcw work tombstone add`, or a deleted slug can be reissued.
  `tcw validate` reports an unknown status or a value that is not `true` or
  `false`, and the default (keep the item) is used in the meantime. It also
  reports a status set explicitly to `true` whose folder is gitignored, because
  items landing there would not be tracked.

Run `tcw validate` after changing any of these.

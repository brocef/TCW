## Parents, and what each passes down

A project now names the projects it builds on under `parents:` in
`.tcw/tcw-config.yaml`, by ID and in order. A project may have several parents,
and each says what it passes down: everything (`inherit: all`, the default),
nothing (`inherit: none`), or a list drawn from `taxonomy`, `capabilities` and
`config`:

    parents:
      - core
      - id: workspace
        inherit: [config]

The parent does not have to name the child. A parent may list its children
under `children:`, in its committed file, in its personal
`.tcw/tcw-config.local.yaml`, or both; the personal list only adds, and the
user-wide file cannot list children. Every listed child must name its parent.

## The order ancestors are read in

A project's ancestors are read in one order, the load order, which ends with
the project itself. TCW works it out the way Python orders a class's bases, so
that a later parent wins over an earlier one and every project's own order of
parents is kept. When no order can keep them all, TCW uses a depth-first order
and `tcw validate` warns, naming the project where the orders disagree. A loop
of parents is an error. `tcw projects list --json` shows the load order, what
each parent passes down, which children only your personal file lists, and
which projects are read-only from here.

## A project that is not here

A parent or ancestor that is not on this machine, or whose own parents cannot
be read, stops only a command that needs what it passes down. That command
exits with the new code 7 and says which project it needs and how to fetch
it. `tcw validate` reports each such project once, as could not be checked,
and still exits 0.

When a manifest places a project in one folder but the folder search finds it
in another, TCW no longer picks one: every command stops with exit 1 and an
error naming both folders. To settle it, add an entry for that project to your
own `.tcw/tcw-manifest.local.yaml`, which is read first, giving the folder you
mean (for example `lib: ../lib`).

When a manifest entry's folder is missing, the "not on this machine" message
now names the full folder that was checked, not the entry's relative path. In
a linked git worktree, that is the folder beside the main checkout.

## What is gone

- The `projects:` key, with its `parent`, `children` and `upstream` entries.
  A configuration that still has it is refused, with a message saying to name
  parents under `parents:` and children under `children:`. A project that only
  read from another is now a child naming that project as a parent, which does
  not list it back.
- Writing into a sibling, another child of one of your parents: work can be
  created only in a project reached through links both sides declare.
- Filing work into a project not on this machine through a `jira` block.

## `extends`

Until it is replaced in TCW 4.0, `taxonomy.extends` and `capabilities.extends`
may name only an ancestor whose parent links pass that axis down. Naming any
other project is refused, and `extends add` leaves the file unchanged.

## The web app

The create form marks a project that is read-only from here, as the command
line decides it.

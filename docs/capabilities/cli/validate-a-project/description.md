As a user, I run `tcw validate` to check the current project: its
`.tcw/tcw-config.yaml`, its connections to other projects, the YAML and `tcw://` links
in its stores, its taxonomy and capabilities ledgers, and its work items. It checks this
project only; a reference into another project is checked by resolving it. It
takes no path, and nothing it does reaches the network.

**Findings are the product, so they go to standard output**, one per line, as
`<severity>: <where>: <message>`, where `<where>` is a file (with `:<line>` when
known) or an item slug. A clean run prints nothing on standard output. Standard
error carries a closing count, such as `2 errors, 1 warning, 0 unresolved`, and
notes such as a `TCW_PROJECT_<ID>` override in effect.

There are three severities, and only one fails the run:

- `error` — malformed YAML, a broken `tcw://` link, an `item.yaml` that cannot be
  read, a taxonomy or capabilities problem (including a capability record that
  still carries the retired `Planning doc` or `Tracker` field), or a
  configuration problem in any layer — `.tcw/tcw-config.yaml`, the user-wide
  file or `.tcw/tcw-config.local.yaml` — named by its file and key. That
  includes a `.tcw/` file whose `tcw-version` is missing, is not a version
  written as text, is older than TCW 4 or is newer than the running TCW, and
  a key or project ID that is not lowercase letters and digits joined by
  single hyphens. Any error makes `tcw validate` exit 1.
- `warning` — for example a `.tcw/tcw-config.local.yaml` or
  `.tcw/tcw-manifest.local.yaml` that version control is tracking, which should
  stay personal; a committed manifest entry overridden on this machine by the
  personal manifest or a `TCW_PROJECT_<ID>`, whose problem would otherwise be
  an error; a TCW 3.x `tcw-config.yaml` left at
  the root of a TCW 4 project, which is not read; a load order that no order
  can keep (see [Read a project's ancestors in one load
  order](tcw://C/cli/read-ancestors-in-one-load-order)); a parent or blocker that names no item, an item whose
  latest verdict round is invalid, or a stage ahead of its artifacts. The run
  still exits 0.
- `unresolved` — something declared that cannot be checked from here: a project
  that is not on this machine, or a reference into one. The run still exits 0.

**Connections between projects.** Missing or invalid IDs, a malformed
`parents:` or `children:` entry, a project named both as a parent and as a
child, a manifest entry placing a folder that holds another project or none,
one ID found in two folders, a listed child that does not name this project
among its parents, and a loop of parents are errors, with guidance on how to
fix them. The TCW 3 `projects:` key is an error saying to name parents under
`parents:` and children under `children:`. Every entry of this project's two
manifests is checked, whether or not a link names it: an entry whose folder is
not here, or is empty, is `unresolved`, and one whose folder is wrong is an
error. A project not on this machine is reported with where its manifest entry
places it and, when the entry gives a repository, the command that fetches it.

A parent, a project further up, or a listed child that is not on this machine
is one `unresolved` finding saying what could not be checked: what it passes
down to this project, or that it names its parent back. So is a parent whose
own `parents:` cannot be read, or still holds the 3.x `projects:` key: its
problem is its own, and this project's run goes on. When a taxonomy or
capabilities check stops at such a project, the same finding adds that the
taxonomy or capabilities inherited from it could not be checked.
The key 2.x used before `projects` was named is an error naming
`docs/migration-guide-2.8-to-3.0.0.md`. A connected project still in the TCW
3.x layout, or whose `.tcw/tcw-config.yaml` records a version this TCW cannot
read, is an error on that connection naming what to do (converting it to TCW 4, or an
upgrade), and that project is not read. In a 3.x project itself, `tcw validate`
refuses like every other command.

**Stores.** Validation tells a store's three failure modes apart: a
`<component>.path` that is simply wrong, a store declared in another repository
but not yet provisioned here (naming the declared remote and `tcw provision`),
and a malformed `repository` block (naming the configuration key). The last is
reported even when no local store can be opened to report it through. A store
that cannot be opened is one finding beside the others rather than the end of
the run, so one unprovisioned store does not hide the rest. A `<component>.path`
that names a folder holding no store, in a project that also declares a home
repository it has not obtained, is two findings, not one; a configured path that
simply does not exist stays silent when a home repository is declared, because
that is the ordinary state of a checkout holding only the code. A taxonomy or
capabilities `config.yaml` or `.config.yaml` left over from before 2.5.0 is
reported once for each store that has one.

**Work items.** Every item is checked: an `item.yaml` that cannot be read is an
error naming the file and the key, and the other checks still run over the items
that can be read. An item whose stage is not in the stage table, or is disabled
in this project, is reported. While an item is still being worked, its
`capabilities.yaml` is checked for paths that cannot be right. A work store
shared with another project in this repository, which would mix their items, is
an error.

**Jira mode.** When the project keeps its work items in Jira, plain
`tcw validate` checks only what is on this machine: each item folder's name and
`item.yaml`, the latest `review` round, and each folder's `capabilities.yaml`,
which is an error when it cannot be read or is malformed, whatever the item's
stage, since the stage is kept in Jira. A folder for a stage Jira keeps, such as
`qa/`, is a warning that the folder is ignored, and its rounds are not read.
`tcw validate --remote` also checks the project against Jira itself — its
workflow, its fields, the stages and links of its items, and the records each
unfinished item's `capabilities.yaml` declares — and only reads; a
`capabilities.yaml` already reported as malformed is not reported again. A Jira
that cannot be reached is exit 5. In a project that keeps its items in files,
`--remote` is a usage error (exit 2).

`tcw validate` also checks the form of every reference stored in a record
and every `tcw://` address, and reports one still in a TCW 3.x form as needing
tcw migrate. It fails two stores that are the same folder or one inside the
other, among this project's three stores and those of every project it can
locate, and a store location that loops back to a store already followed.
